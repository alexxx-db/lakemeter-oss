/**
 * AI Chat Panel Component
 * 
 * Provides a conversational interface for the AI assistant to help users
 * create and manage estimates.
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import clsx from 'clsx'
import {
  ChatBubbleLeftRightIcon,
  PaperAirplaneIcon,
  XMarkIcon,
  SparklesIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ArrowPathIcon,
  DocumentPlusIcon,
  TrashIcon
} from '@heroicons/react/24/outline'
// AI Chat Panel uses fetch directly - no store needed

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  toolResults?: ToolResult[]
  isStreaming?: boolean
}

interface ToolResult {
  tool: string
  result: any
}

interface DraftEstimate {
  draft_id: string
  name: string
  cloud: string
  region: string
  description?: string
  status: 'draft'
}

interface DraftWorkload {
  draft_id: string
  workload_type: string
  workload_name: string
  estimated_cost: number
  [key: string]: any
}

interface ChatPanelProps {
  isOpen: boolean
  onClose: () => void
  onEstimateCreated?: (estimateId: string) => void
  currentEstimate?: any
  currentWorkloads?: any[]
}

export function ChatPanel({
  isOpen,
  onClose,
  onEstimateCreated,
  currentEstimate,
  currentWorkloads
}: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [draftEstimate, setDraftEstimate] = useState<DraftEstimate | null>(null)
  const [draftWorkloads, setDraftWorkloads] = useState<DraftWorkload[]>([])
  const [error, setError] = useState<string | null>(null)
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus()
    }
  }, [isOpen])

  // Add welcome message on first open
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      const welcomeMessage: Message = {
        id: 'welcome',
        role: 'assistant',
        content: currentEstimate 
          ? `I see you're working on the estimate "${currentEstimate.name}". How can I help you? I can analyze your current workloads, suggest optimizations, or help you add new ones.`
          : `Hi! I'm your Databricks pricing assistant. I can help you create cost estimates for your workloads.\n\nTell me about what you're planning to build, and I'll help you configure the right resources. For example:\n- "I need to run daily ETL jobs processing 500GB of data"\n- "We're setting up a SQL analytics warehouse for our BI team"\n- "I want to estimate costs for a real-time ML inference endpoint"`,
        timestamp: new Date()
      }
      setMessages([welcomeMessage])
    }
  }, [isOpen, currentEstimate])

  const sendMessage = useCallback(async () => {
    if (!inputValue.trim() || isLoading) return

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)
    setError(null)

    // Create placeholder for assistant response
    const assistantMessageId = `assistant-${Date.now()}`
    setMessages(prev => [...prev, {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true
    }])

    try {
      abortControllerRef.current = new AbortController()
      
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: userMessage.content,
          conversation_id: conversationId,
          estimate_context: currentEstimate || draftEstimate,
          workloads_context: currentWorkloads || draftWorkloads,
          stream: true
        }),
        signal: abortControllerRef.current.signal
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let buffer = ''
      let fullContent = ''
      let toolResults: ToolResult[] = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') continue

            try {
              const chunk = JSON.parse(data)
              
              if (chunk.type === 'start') {
                setConversationId(chunk.conversation_id)
              } else if (chunk.type === 'content') {
                fullContent += chunk.content
                setMessages(prev => prev.map(m => 
                  m.id === assistantMessageId 
                    ? { ...m, content: fullContent }
                    : m
                ))
              } else if (chunk.type === 'tool_result') {
                toolResults.push({
                  tool: chunk.tool,
                  result: chunk.result
                })
              } else if (chunk.type === 'done') {
                // Update draft state from final response
                if (chunk.estimate) {
                  setDraftEstimate(chunk.estimate)
                }
                if (chunk.workloads) {
                  setDraftWorkloads(chunk.workloads)
                }
              } else if (chunk.type === 'error') {
                throw new Error(chunk.content)
              }
            } catch (e) {
              // Ignore parse errors for incomplete chunks
            }
          }
        }
      }

      // Finalize the assistant message
      setMessages(prev => prev.map(m => 
        m.id === assistantMessageId 
          ? { ...m, content: fullContent, isStreaming: false, toolResults }
          : m
      ))

    } catch (err: any) {
      if (err.name === 'AbortError') return
      
      console.error('Chat error:', err)
      setError(err.message || 'Failed to get response')
      
      // Remove the streaming message on error
      setMessages(prev => prev.filter(m => m.id !== assistantMessageId))
    } finally {
      setIsLoading(false)
      abortControllerRef.current = null
    }
  }, [inputValue, isLoading, conversationId, currentEstimate, currentWorkloads, draftEstimate, draftWorkloads])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const clearConversation = async () => {
    if (conversationId) {
      try {
        await fetch(`/api/v1/chat/${conversationId}`, { method: 'DELETE' })
      } catch (e) {
        // Ignore errors
      }
    }
    setMessages([])
    setConversationId(null)
    setDraftEstimate(null)
    setDraftWorkloads([])
    setError(null)
  }

  const applyEstimate = async () => {
    if (!conversationId || !draftEstimate) return

    setIsLoading(true)
    try {
      const response = await fetch(`/api/v1/chat/${conversationId}/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })

      if (!response.ok) {
        throw new Error('Failed to apply estimate')
      }

      const result = await response.json()
      
      // Add success message
      setMessages(prev => [...prev, {
        id: `system-${Date.now()}`,
        role: 'system',
        content: `✅ ${result.message}`,
        timestamp: new Date()
      }])

      // Clear draft state
      setDraftEstimate(null)
      setDraftWorkloads([])

      // Notify parent
      if (onEstimateCreated) {
        onEstimateCreated(result.estimate_id)
      }
    } catch (err: any) {
      setError(err.message || 'Failed to apply estimate')
    } finally {
      setIsLoading(false)
    }
  }

  const totalDraftCost = draftWorkloads.reduce((sum, w) => sum + (w.estimated_cost || 0), 0)

  if (!isOpen) return null

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-[420px] bg-[var(--bg-primary)] border-l border-[var(--border-primary)] shadow-2xl z-50 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-primary)] bg-[var(--bg-secondary)]">
        <div className="flex items-center gap-2">
          <SparklesIcon className="w-5 h-5 text-orange-500" />
          <h2 className="font-semibold text-[var(--text-primary)]">AI Assistant</h2>
          {conversationId && (
            <span className="text-xs text-[var(--text-muted)] bg-[var(--bg-tertiary)] px-2 py-0.5 rounded">
              Active
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={clearConversation}
            className="p-1.5 rounded-lg hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)]"
            title="Clear conversation"
          >
            <TrashIcon className="w-4 h-4" />
          </button>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)]"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Draft Estimate Preview */}
      {draftEstimate && (
        <div className="px-4 py-3 bg-teal-50 dark:bg-teal-900/20 border-b border-teal-200 dark:border-teal-800">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <DocumentPlusIcon className="w-4 h-4 text-teal-600" />
              <span className="text-sm font-medium text-teal-700 dark:text-teal-300">
                Draft Estimate
              </span>
            </div>
            <button
              onClick={applyEstimate}
              disabled={isLoading || draftWorkloads.length === 0}
              className="text-xs px-3 py-1 bg-teal-600 text-white rounded-full hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
            >
              <CheckCircleIcon className="w-3 h-3" />
              Save Estimate
            </button>
          </div>
          <div className="text-sm text-teal-800 dark:text-teal-200">
            <span className="font-medium">{draftEstimate.name}</span>
            <span className="text-teal-600 dark:text-teal-400"> • {draftEstimate.cloud.toUpperCase()} {draftEstimate.region}</span>
          </div>
          {draftWorkloads.length > 0 && (
            <div className="mt-2 flex items-center justify-between text-xs">
              <span className="text-teal-600 dark:text-teal-400">
                {draftWorkloads.length} workload{draftWorkloads.length !== 1 ? 's' : ''}
              </span>
              <span className="font-medium text-teal-700 dark:text-teal-300">
                ~${totalDraftCost.toLocaleString()}/month
              </span>
            </div>
          )}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={clsx(
              'flex gap-3',
              message.role === 'user' ? 'flex-row-reverse' : 'flex-row'
            )}
          >
            {/* Avatar */}
            <div className={clsx(
              'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
              message.role === 'user' 
                ? 'bg-blue-100 dark:bg-blue-900' 
                : message.role === 'system'
                ? 'bg-green-100 dark:bg-green-900'
                : 'bg-orange-100 dark:bg-orange-900'
            )}>
              {message.role === 'user' ? (
                <span className="text-xs font-medium text-blue-600 dark:text-blue-400">You</span>
              ) : message.role === 'system' ? (
                <CheckCircleIcon className="w-4 h-4 text-green-600 dark:text-green-400" />
              ) : (
                <SparklesIcon className="w-4 h-4 text-orange-600 dark:text-orange-400" />
              )}
            </div>

            {/* Message Content */}
            <div className={clsx(
              'flex-1 max-w-[85%]',
              message.role === 'user' ? 'text-right' : 'text-left'
            )}>
              <div className={clsx(
                'inline-block px-4 py-2 rounded-2xl text-sm',
                message.role === 'user'
                  ? 'bg-blue-600 text-white rounded-tr-sm'
                  : message.role === 'system'
                  ? 'bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-200 rounded-tl-sm'
                  : 'bg-[var(--bg-secondary)] text-[var(--text-primary)] rounded-tl-sm border border-[var(--border-primary)]'
              )}>
                {message.isStreaming && !message.content ? (
                  <div className="flex items-center gap-2">
                    <ArrowPathIcon className="w-4 h-4 animate-spin" />
                    <span>Thinking...</span>
                  </div>
                ) : (
                  <div className="whitespace-pre-wrap">{message.content}</div>
                )}
              </div>

              {/* Tool Results */}
              {message.toolResults && message.toolResults.length > 0 && (
                <div className="mt-2 space-y-1">
                  {message.toolResults.map((tr, idx) => (
                    <div
                      key={idx}
                      className="text-xs px-3 py-1.5 bg-[var(--bg-tertiary)] rounded-lg border border-[var(--border-primary)]"
                    >
                      <span className="font-medium text-orange-600 dark:text-orange-400">
                        {tr.tool.replace(/_/g, ' ')}
                      </span>
                      {tr.result?.success && (
                        <span className="ml-2 text-green-600 dark:text-green-400">✓</span>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Timestamp */}
              <div className={clsx(
                'text-xs text-[var(--text-muted)] mt-1',
                message.role === 'user' ? 'text-right' : 'text-left'
              )}>
                {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          </div>
        ))}

        {/* Error Message */}
        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-300">
            <ExclamationCircleIcon className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-[var(--border-primary)] bg-[var(--bg-secondary)]">
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask me about Databricks pricing..."
            disabled={isLoading}
            rows={1}
            className="flex-1 resize-none rounded-xl border border-[var(--border-primary)] bg-[var(--bg-primary)] px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 disabled:opacity-50"
            style={{ minHeight: '44px', maxHeight: '120px' }}
          />
          <button
            onClick={sendMessage}
            disabled={!inputValue.trim() || isLoading}
            className="px-4 py-2 bg-orange-600 text-white rounded-xl hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          >
            {isLoading ? (
              <ArrowPathIcon className="w-5 h-5 animate-spin" />
            ) : (
              <PaperAirplaneIcon className="w-5 h-5" />
            )}
          </button>
        </div>
        <p className="text-xs text-[var(--text-muted)] mt-2 text-center">
          Powered by Claude Sonnet 4.5 • Estimates are approximate
        </p>
      </div>
    </div>
  )
}

/**
 * AI Assistant Toggle Button
 * 
 * Floating button to open the chat panel.
 */
export function ChatToggleButton({ onClick, hasActiveConversation }: { onClick: () => void, hasActiveConversation?: boolean }) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "fixed bottom-6 right-6 w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-all hover:scale-105 z-40",
        hasActiveConversation
          ? "bg-teal-600 hover:bg-teal-700"
          : "bg-orange-600 hover:bg-orange-700"
      )}
      title="AI Assistant"
    >
      <ChatBubbleLeftRightIcon className="w-6 h-6 text-white" />
      {hasActiveConversation && (
        <span className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full border-2 border-white" />
      )}
    </button>
  )
}

