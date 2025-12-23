"""
Databricks Claude AI Client

Integrates with Databricks-hosted Claude Sonnet 4.5 model for the AI assistant.
Endpoint: https://fe-vm-lakemeter.cloud.databricks.com/serving-endpoints/databricks-claude-sonnet-4-5/invocations

Rate Limits (Pay-per-token):
- Input tokens per minute (ITPM): Controls input throughput
- Output tokens per minute (OTPM): Controls output throughput  
- Queries per hour: Maximum requests in 60-minute window
"""
import os
import json
import asyncio
import httpx
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import deque

from app.config import log_info, log_warning, log_error


# Claude endpoint configuration
CLAUDE_ENDPOINT = "https://fe-vm-lakemeter.cloud.databricks.com/serving-endpoints/databricks-claude-sonnet-4-5/invocations"
MODEL_NAME = "databricks-claude-sonnet-4-5"

# Rate limiting configuration (conservative defaults)
MAX_QUERIES_PER_HOUR = 100  # Adjust based on your actual limits
MAX_INPUT_TOKENS_PER_MINUTE = 40000
MAX_OUTPUT_TOKENS_PER_MINUTE = 8000


@dataclass
class RateLimitState:
    """Tracks rate limit usage."""
    query_timestamps: deque  # Timestamps of queries in last hour
    input_tokens_window: deque  # (timestamp, token_count) tuples
    output_tokens_window: deque  # (timestamp, token_count) tuples
    
    def __init__(self):
        self.query_timestamps = deque()
        self.input_tokens_window = deque()
        self.output_tokens_window = deque()


class ClaudeAIClient:
    """
    Client for Databricks-hosted Claude Sonnet 4.5.
    
    Handles authentication, rate limiting, and streaming responses.
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the Claude client.
        
        Args:
            token: Databricks OAuth token. If not provided, will attempt to get from environment.
        """
        self._token = token
        self._rate_limit_state = RateLimitState()
        self._http_client: Optional[httpx.AsyncClient] = None
    
    def set_token(self, token: str):
        """Set the authentication token."""
        self._token = token
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=120.0)
        return self._http_client
    
    async def close(self):
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    def _clean_rate_limit_windows(self):
        """Remove expired entries from rate limit tracking."""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        minute_ago = now - timedelta(minutes=1)
        
        # Clean query timestamps (1 hour window)
        while self._rate_limit_state.query_timestamps and \
              self._rate_limit_state.query_timestamps[0] < hour_ago:
            self._rate_limit_state.query_timestamps.popleft()
        
        # Clean token windows (1 minute window)
        while self._rate_limit_state.input_tokens_window and \
              self._rate_limit_state.input_tokens_window[0][0] < minute_ago:
            self._rate_limit_state.input_tokens_window.popleft()
        
        while self._rate_limit_state.output_tokens_window and \
              self._rate_limit_state.output_tokens_window[0][0] < minute_ago:
            self._rate_limit_state.output_tokens_window.popleft()
    
    def _check_rate_limits(self, estimated_input_tokens: int = 1000) -> bool:
        """
        Check if we're within rate limits.
        
        Returns True if request can proceed, False if rate limited.
        """
        self._clean_rate_limit_windows()
        
        # Check queries per hour
        if len(self._rate_limit_state.query_timestamps) >= MAX_QUERIES_PER_HOUR:
            log_warning(f"Rate limited: {len(self._rate_limit_state.query_timestamps)} queries in last hour")
            return False
        
        # Check input tokens per minute
        current_input_tokens = sum(t[1] for t in self._rate_limit_state.input_tokens_window)
        if current_input_tokens + estimated_input_tokens > MAX_INPUT_TOKENS_PER_MINUTE:
            log_warning(f"Rate limited: {current_input_tokens} input tokens in last minute")
            return False
        
        return True
    
    def _record_usage(self, input_tokens: int, output_tokens: int):
        """Record token usage for rate limiting."""
        now = datetime.now()
        self._rate_limit_state.query_timestamps.append(now)
        self._rate_limit_state.input_tokens_window.append((now, input_tokens))
        self._rate_limit_state.output_tokens_window.append((now, output_tokens))
    
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a chat request to Claude (non-streaming).
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)
            system: Optional system prompt
            
        Returns:
            Response dict with 'content', 'tool_calls', and 'usage'
        """
        if not self._token:
            raise ValueError("No authentication token provided")
        
        # Estimate input tokens (rough: 4 chars per token)
        estimated_input = sum(len(str(m.get('content', ''))) // 4 for m in messages)
        if system:
            estimated_input += len(system) // 4
        
        if not self._check_rate_limits(estimated_input):
            raise Exception("Rate limit exceeded. Please wait before making more requests.")
        
        # Build request payload (Anthropic messages format)
        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "anthropic_version": "2023-06-01"
        }
        
        if system:
            payload["system"] = system
        
        if tools:
            payload["tools"] = tools
        
        client = await self._get_http_client()
        
        try:
            response = await client.post(
                CLAUDE_ENDPOINT,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
            result = response.json()
            
            # Record usage
            usage = result.get("usage", {})
            self._record_usage(
                usage.get("input_tokens", estimated_input),
                usage.get("output_tokens", 0)
            )
            
            return self._parse_response(result)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                log_error("Claude API rate limited (429)")
                raise Exception("AI service is temporarily rate limited. Please try again in a moment.")
            log_error(f"Claude API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            log_error(f"Claude API request failed: {e}")
            raise
    
    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Send a streaming chat request to Claude.
        
        Yields chunks with 'type' and 'content' or 'tool_call' data.
        """
        if not self._token:
            raise ValueError("No authentication token provided")
        
        # Estimate input tokens
        estimated_input = sum(len(str(m.get('content', ''))) // 4 for m in messages)
        if system:
            estimated_input += len(system) // 4
        
        if not self._check_rate_limits(estimated_input):
            yield {"type": "error", "content": "Rate limit exceeded. Please wait before making more requests."}
            return
        
        # Build request payload with streaming
        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            "anthropic_version": "2023-06-01"
        }
        
        if system:
            payload["system"] = system
        
        if tools:
            payload["tools"] = tools
        
        client = await self._get_http_client()
        
        try:
            async with client.stream(
                "POST",
                CLAUDE_ENDPOINT,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json"
                }
            ) as response:
                response.raise_for_status()
                
                output_tokens = 0
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            parsed = self._parse_stream_chunk(chunk)
                            if parsed:
                                if parsed.get("type") == "content_delta":
                                    output_tokens += 1  # Rough estimate
                                yield parsed
                        except json.JSONDecodeError:
                            continue
                
                # Record usage
                self._record_usage(estimated_input, output_tokens)
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                yield {"type": "error", "content": "AI service is temporarily rate limited. Please try again."}
            else:
                yield {"type": "error", "content": f"AI service error: {e.response.status_code}"}
        except Exception as e:
            log_error(f"Claude streaming error: {e}")
            yield {"type": "error", "content": str(e)}
    
    def _parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Claude API response into standardized format."""
        result = {
            "content": "",
            "tool_calls": [],
            "usage": response.get("usage", {}),
            "stop_reason": response.get("stop_reason")
        }
        
        for block in response.get("content", []):
            if block.get("type") == "text":
                result["content"] += block.get("text", "")
            elif block.get("type") == "tool_use":
                result["tool_calls"].append({
                    "id": block.get("id"),
                    "name": block.get("name"),
                    "arguments": block.get("input", {})
                })
        
        return result
    
    def _parse_stream_chunk(self, chunk: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a streaming chunk into standardized format."""
        chunk_type = chunk.get("type")
        
        if chunk_type == "content_block_start":
            block = chunk.get("content_block", {})
            if block.get("type") == "tool_use":
                return {
                    "type": "tool_use_start",
                    "id": block.get("id"),
                    "name": block.get("name")
                }
        
        elif chunk_type == "content_block_delta":
            delta = chunk.get("delta", {})
            if delta.get("type") == "text_delta":
                return {
                    "type": "content_delta",
                    "content": delta.get("text", "")
                }
            elif delta.get("type") == "input_json_delta":
                return {
                    "type": "tool_input_delta",
                    "partial_json": delta.get("partial_json", "")
                }
        
        elif chunk_type == "message_delta":
            return {
                "type": "message_delta",
                "stop_reason": chunk.get("delta", {}).get("stop_reason")
            }
        
        elif chunk_type == "message_stop":
            return {"type": "done"}
        
        return None


# Global client instance (initialized per-request with user token)
def get_claude_client(token: str) -> ClaudeAIClient:
    """Get a Claude client instance with the given token."""
    client = ClaudeAIClient(token=token)
    return client

