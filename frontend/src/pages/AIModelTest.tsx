import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import { 
  BeakerIcon, 
  PlayIcon, 
  SparklesIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  ChatBubbleLeftRightIcon,
  WrenchScrewdriverIcon,
  DocumentTextIcon
} from '@heroicons/react/24/outline'
import clsx from 'clsx'

interface ModelConfig {
  name: string
  model_id: string
  itpm_limit: number
  otpm_limit: number
  description: string
}

interface TestPrompt {
  name: string
  description: string
  prompt: string
  expected_max_tokens: number
}

interface TestMetrics {
  total_latency_ms: number
  total_latency_seconds?: number
  input_tokens?: number
  output_tokens?: number
  total_tokens?: number
  tokens_per_second?: number
}

interface TestResult {
  success: boolean
  model: string
  model_id?: string
  content?: string
  response?: string
  content_length?: number
  response_length?: number
  error?: string
  traceback?: string
  metrics?: TestMetrics
  tool_calls_made?: string[]
  proposed_workloads?: number
  limits?: {
    itpm_limit?: number
    otpm_limit?: number
    max_tokens_used?: number
    model_itpm_limit?: number
    model_otpm_limit?: number
  }
  context?: {
    estimate_loaded: boolean
    workloads_count: number
    conversation_length: number
  }
}

interface ComparisonResult {
  test_type: string
  test_name: string
  prompt_preview?: string
  prompt?: string
  error?: string
  traceback?: string
  results: Record<string, TestResult>
  comparison: {
    faster_model?: string
    latency_difference_ms?: number
    latency_ratio?: number
    sonnet_tokens_per_sec?: number
    opus_tokens_per_sec?: number
    sonnet_response_length?: number
    opus_response_length?: number
    sonnet_tools_used?: number
    opus_tools_used?: number
    output_length_difference?: number
  }
}

interface AIAssistantPrompt {
  name: string
  description: string
  prompt: string
}

const MODEL_INFO = {
  'databricks-claude-sonnet-4-5': {
    name: 'Claude Sonnet 4.5',
    color: 'blue',
    itpm: 50000,
    otpm: 5000
  },
  'databricks-claude-opus-4-5': {
    name: 'Claude Opus 4.5',
    color: 'purple',
    itpm: 200000,
    otpm: 20000
  }
}

export default function AIModelTest() {
  const [_models, setModels] = useState<Record<string, ModelConfig>>({})
  const [testPrompts, setTestPrompts] = useState<Record<string, TestPrompt>>({})
  const [assistantPrompts, setAssistantPrompts] = useState<Record<string, AIAssistantPrompt>>({})
  const [selectedTest, setSelectedTest] = useState<string>('medium_analysis')
  const [selectedAssistantTest, setSelectedAssistantTest] = useState<string>('analyze_costs')
  const [selectedModel, setSelectedModel] = useState<string>('databricks-claude-sonnet-4-5')
  const [customPrompt, setCustomPrompt] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isComparing, setIsComparing] = useState(false)
  const [singleResult, setSingleResult] = useState<TestResult | null>(null)
  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null)
  const [stressTestTokens, setStressTestTokens] = useState(4000)
  const [stressResult, setStressResult] = useState<any>(null)
  const [isStressTesting, setIsStressTesting] = useState(false)
  const [assistantResult, setAssistantResult] = useState<TestResult | null>(null)
  const [assistantComparisonResult, setAssistantComparisonResult] = useState<ComparisonResult | null>(null)
  const [isAssistantTesting, setIsAssistantTesting] = useState(false)
  const [isAssistantComparing, setIsAssistantComparing] = useState(false)
  const [systemPromptInfo, setSystemPromptInfo] = useState<any>(null)
  const [showSystemPrompt, setShowSystemPrompt] = useState(false)
  const [activeTab, setActiveTab] = useState<'interactive' | 'assistant' | 'assistant-compare' | 'single' | 'compare' | 'stress'>('interactive')
  
  // Interactive chat state
  const [chatSessionId, setChatSessionId] = useState<string | null>(null)
  const [chatModel, setChatModel] = useState<string>('databricks-claude-sonnet-4-5')
  const [chatMessages, setChatMessages] = useState<Array<{role: string, content: string, tool_calls?: any[], latency_ms?: number}>>([])
  const [chatInput, setChatInput] = useState('')
  const [isChatLoading, setIsChatLoading] = useState(false)
  const [chatSessionInfo, setChatSessionInfo] = useState<any>(null)
  const [enableTools, setEnableTools] = useState(true)

  useEffect(() => {
    loadModelsAndPrompts()
    loadAssistantPrompts()
  }, [])

  const loadModelsAndPrompts = async () => {
    try {
      const response = await fetch('/api/v1/ai-test/models')
      if (response.ok) {
        const data = await response.json()
        setModels(data.models)
        setTestPrompts(data.test_prompts)
      }
    } catch (error) {
      console.error('Failed to load models:', error)
    }
  }

  const loadAssistantPrompts = async () => {
    try {
      const response = await fetch('/api/v1/ai-test/assistant/prompts')
      if (response.ok) {
        const data = await response.json()
        setAssistantPrompts(data.prompts)
      }
    } catch (error) {
      console.error('Failed to load assistant prompts:', error)
    }
  }

  const loadSystemPrompt = async () => {
    try {
      const response = await fetch('/api/v1/ai-test/assistant/system-prompt')
      if (response.ok) {
        const data = await response.json()
        setSystemPromptInfo(data)
        setShowSystemPrompt(true)
      }
    } catch (error) {
      console.error('Failed to load system prompt:', error)
    }
  }

  const runSingleTest = async () => {
    setIsLoading(true)
    setSingleResult(null)
    
    try {
      const response = await fetch('/api/v1/ai-test/test-single', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_id: selectedModel,
          test_type: selectedTest,
          temperature: 0.7
        })
      })
      
      const data = await response.json()
      setSingleResult(data)
    } catch (error) {
      setSingleResult({
        success: false,
        model: selectedModel,
        error: String(error)
      })
    } finally {
      setIsLoading(false)
    }
  }

  const runComparison = async () => {
    setIsComparing(true)
    setComparisonResult(null)
    
    try {
      const response = await fetch('/api/v1/ai-test/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          test_type: selectedTest,
          temperature: 0.7
        })
      })
      
      const data = await response.json()
      setComparisonResult(data)
    } catch (error) {
      console.error('Comparison failed:', error)
    } finally {
      setIsComparing(false)
    }
  }

  const runStressTest = async (modelId: string) => {
    setIsStressTesting(true)
    setStressResult(null)
    
    try {
      const response = await fetch(`/api/v1/ai-test/stress-test?model_id=${modelId}&target_output_tokens=${stressTestTokens}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      
      const data = await response.json()
      setStressResult({ ...data, tested_model: modelId })
    } catch (error) {
      setStressResult({
        success: false,
        error: String(error),
        tested_model: modelId
      })
    } finally {
      setIsStressTesting(false)
    }
  }

  const runAssistantTest = async () => {
    setIsAssistantTesting(true)
    setAssistantResult(null)
    
    try {
      const response = await fetch('/api/v1/ai-test/assistant/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_id: selectedModel,
          test_type: selectedAssistantTest,
          custom_prompt: customPrompt || undefined,
          include_sample_context: true
        })
      })
      
      const data = await response.json()
      setAssistantResult(data)
    } catch (error) {
      setAssistantResult({
        success: false,
        model: selectedModel,
        error: String(error)
      })
    } finally {
      setIsAssistantTesting(false)
    }
  }

  const runAssistantComparison = async () => {
    setIsAssistantComparing(true)
    setAssistantComparisonResult(null)
    
    try {
      const response = await fetch('/api/v1/ai-test/assistant/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          test_type: selectedAssistantTest,
          custom_prompt: customPrompt || undefined
        })
      })
      
      // Check if response is OK
      if (!response.ok) {
        const text = await response.text()
        setAssistantComparisonResult({
          error: `HTTP ${response.status}: ${text || response.statusText}`,
          results: {},
          comparison: {} as any,
          test_type: selectedAssistantTest,
          test_name: 'Error',
          prompt: ''
        })
        return
      }
      
      const data = await response.json()
      setAssistantComparisonResult(data)
    } catch (error) {
      console.error('Assistant comparison failed:', error)
      setAssistantComparisonResult({
        error: String(error),
        results: {},
        comparison: {} as any,
        test_type: selectedAssistantTest,
        test_name: 'Error',
        prompt: ''
      })
    } finally {
      setIsAssistantComparing(false)
    }
  }

  // Interactive Chat Functions
  const startNewChatSession = async () => {
    setIsChatLoading(true)
    setChatMessages([])
    setChatSessionInfo(null)
    
    try {
      const response = await fetch(`/api/v1/ai-test/interactive/new-session?model_id=${chatModel}`, {
        method: 'POST'
      })
      
      if (response.ok) {
        const data = await response.json()
        setChatSessionId(data.session_id)
        setChatSessionInfo(data)
        setChatMessages([{
          role: 'assistant',
          content: `**Session Started!** 🚀\n\nYou're now chatting with **${data.model}**.\n\n${data.message}\n\n**Available Tools:** ${data.tools_available?.join(', ') || 'None'}\n\n**Context:**\n${data.context_summary}`
        }])
      } else {
        const error = await response.text()
        setChatMessages([{ role: 'assistant', content: `❌ Failed to start session: ${error}` }])
      }
    } catch (error) {
      setChatMessages([{ role: 'assistant', content: `❌ Error: ${String(error)}` }])
    } finally {
      setIsChatLoading(false)
    }
  }

  const sendChatMessage = async () => {
    if (!chatInput.trim() || !chatSessionId) return
    
    const userMessage = chatInput.trim()
    setChatInput('')
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsChatLoading(true)
    
    try {
      const response = await fetch('/api/v1/ai-test/interactive/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: chatSessionId,
          message: userMessage,
          model_id: chatModel,
          enable_tools: enableTools
        })
      })
      
      const data = await response.json()
      
      if (data.error) {
        setChatMessages(prev => [...prev, { 
          role: 'assistant', 
          content: `❌ Error: ${data.error}`,
          latency_ms: data.latency_ms
        }])
      } else {
        let content = data.response || 'No response'
        
        // Add tool call info if any
        if (data.tool_calls && data.tool_calls.length > 0) {
          content += '\n\n---\n**🔧 Tool Calls Detected:**\n'
          data.tool_calls.forEach((tc: any) => {
            content += `- **${tc.tool}**: ${JSON.stringify(tc.arguments)}\n`
            content += `  *Status: ${tc.status}*\n`
          })
        }
        
        setChatMessages(prev => [...prev, { 
          role: 'assistant', 
          content,
          tool_calls: data.tool_calls,
          latency_ms: data.latency_ms
        }])
        
        // Update session info
        setChatSessionInfo((prev: any) => ({
          ...prev,
          message_count: data.message_count,
          estimated_tokens: data.estimated_tokens
        }))
      }
    } catch (error) {
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `❌ Error: ${String(error)}` 
      }])
    } finally {
      setIsChatLoading(false)
    }
  }

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat().format(num)
  }

  const formatLatency = (ms: number) => {
    if (ms >= 1000) {
      return `${(ms / 1000).toFixed(2)}s`
    }
    return `${ms.toFixed(0)}ms`
  }

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <BeakerIcon className="w-8 h-8 text-lava-600" />
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">
              AI Model Testing Lab
            </h1>
          </div>
          <p className="text-[var(--text-secondary)]">
            Compare Claude Sonnet 4.5 vs Opus 4.5 as Lakemeter AI Assistant backend
          </p>
        </div>

        {/* Model Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {Object.entries(MODEL_INFO).map(([modelId, info]) => (
            <div 
              key={modelId}
              className={clsx(
                'card p-4 border-l-4',
                info.color === 'blue' ? 'border-l-blue-500' : 'border-l-purple-500'
              )}
            >
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-[var(--text-primary)]">{info.name}</h3>
                <span className={clsx(
                  'text-xs px-2 py-1 rounded-full',
                  info.color === 'blue' 
                    ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                    : 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                )}>
                  {info.color === 'blue' ? 'Balanced' : 'Highest Capability'}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-[var(--text-muted)]">Input Tokens/min</span>
                  <p className="font-mono font-semibold text-[var(--text-primary)]">
                    {formatNumber(info.itpm)}
                  </p>
                </div>
                <div>
                  <span className="text-[var(--text-muted)]">Output Tokens/min</span>
                  <p className="font-mono font-semibold text-[var(--text-primary)]">
                    {formatNumber(info.otpm)}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Tab Navigation */}
        <div className="flex flex-wrap gap-2 mb-6">
          {[
            { id: 'interactive', label: '💬 Interactive Chat', icon: ChatBubbleLeftRightIcon },
            { id: 'assistant-compare', label: 'AI Assistant Compare', icon: ChartBarIcon },
            { id: 'assistant', label: 'AI Assistant Single', icon: WrenchScrewdriverIcon },
            { id: 'compare', label: 'Raw API Compare', icon: ChartBarIcon },
            { id: 'single', label: 'Raw API Single', icon: PlayIcon },
            { id: 'stress', label: 'Token Stress Test', icon: SparklesIcon }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={clsx(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                activeTab === tab.id
                  ? 'bg-lava-600 text-white'
                  : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'
              )}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Interactive Chat Tab */}
        {activeTab === 'interactive' && (
          <div className="space-y-4">
            {/* Session Controls */}
            <div className="card p-4">
              <div className="flex flex-wrap items-center gap-4 mb-4">
                <div className="flex-1 min-w-[200px]">
                  <label className="block text-sm text-[var(--text-muted)] mb-1">Model</label>
                  <select
                    value={chatModel}
                    onChange={(e) => setChatModel(e.target.value)}
                    className="w-full p-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-primary)] text-[var(--text-primary)]"
                    disabled={!!chatSessionId}
                  >
                    <option value="databricks-claude-sonnet-4-5">Claude Sonnet 4.5 (50K/5K tokens)</option>
                    <option value="databricks-claude-opus-4-5">Claude Opus 4.5 (200K/20K tokens)</option>
                  </select>
                </div>
                
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="enableTools"
                    checked={enableTools}
                    onChange={(e) => setEnableTools(e.target.checked)}
                    className="rounded"
                  />
                  <label htmlFor="enableTools" className="text-sm text-[var(--text-secondary)]">
                    Enable Tools (propose_workload, ask_clarifying_questions, etc.)
                  </label>
                </div>
                
                <button
                  onClick={startNewChatSession}
                  disabled={isChatLoading}
                  className="btn-primary px-4 py-2 flex items-center gap-2"
                >
                  {isChatLoading ? (
                    <ArrowPathIcon className="w-4 h-4 animate-spin" />
                  ) : (
                    <PlayIcon className="w-4 h-4" />
                  )}
                  {chatSessionId ? 'New Session' : 'Start Session'}
                </button>
              </div>
              
              {/* Session Info */}
              {chatSessionInfo && (
                <div className="flex flex-wrap gap-4 text-sm text-[var(--text-muted)] border-t border-[var(--border-primary)] pt-3">
                  <span>Session: <code className="text-lava-600">{chatSessionId}</code></span>
                  <span>Messages: <strong>{chatSessionInfo.message_count || chatMessages.length}</strong></span>
                  <span>Est. Tokens: <strong>{formatNumber(chatSessionInfo.estimated_tokens || 0)}</strong></span>
                  <span className={clsx(
                    'px-2 py-0.5 rounded',
                    chatModel.includes('sonnet') ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'
                  )}>
                    {chatModel.includes('sonnet') ? 'Sonnet 4.5' : 'Opus 4.5'}
                  </span>
                </div>
              )}
            </div>
            
            {/* Chat Messages */}
            <div className="card p-4 min-h-[400px] max-h-[600px] overflow-y-auto flex flex-col gap-4">
              {chatMessages.length === 0 ? (
                <div className="flex-1 flex items-center justify-center text-[var(--text-muted)]">
                  <div className="text-center">
                    <ChatBubbleLeftRightIcon className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>Start a session to begin testing</p>
                    <p className="text-sm mt-2">This interactive mode lets you have a full conversation with the AI Assistant, including tool calls.</p>
                  </div>
                </div>
              ) : (
                chatMessages.map((msg, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={clsx(
                      'p-3 rounded-lg max-w-[85%]',
                      msg.role === 'user' 
                        ? 'bg-[#d7edfe] text-gray-800 self-end ml-auto' 
                        : 'bg-[var(--bg-secondary)] self-start'
                    )}
                  >
                    <div className="flex items-center gap-2 mb-1 text-xs text-[var(--text-muted)]">
                      <span className="font-medium">{msg.role === 'user' ? 'You' : 'AI Assistant'}</span>
                      {msg.latency_ms && <span>• {formatLatency(msg.latency_ms)}</span>}
                      {msg.tool_calls && msg.tool_calls.length > 0 && (
                        <span className="px-1.5 py-0.5 bg-yellow-100 text-yellow-700 rounded text-xs">
                          🔧 {msg.tool_calls.length} tool call(s)
                        </span>
                      )}
                    </div>
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </motion.div>
                ))
              )}
              
              {isChatLoading && (
                <div className="flex items-center gap-2 text-[var(--text-muted)] p-3">
                  <ArrowPathIcon className="w-4 h-4 animate-spin" />
                  <span>Thinking...</span>
                </div>
              )}
            </div>
            
            {/* Chat Input */}
            {chatSessionId && (
              <div className="card p-4">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendChatMessage()}
                    placeholder="Type your message... (e.g., 'Analyze my workloads', 'Add a new Jobs workload', 'How can I reduce costs?')"
                    className="flex-1 p-3 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-primary)] text-[var(--text-primary)]"
                    disabled={isChatLoading}
                  />
                  <button
                    onClick={sendChatMessage}
                    disabled={isChatLoading || !chatInput.trim()}
                    className="btn-primary px-6"
                  >
                    {isChatLoading ? (
                      <ArrowPathIcon className="w-5 h-5 animate-spin" />
                    ) : (
                      'Send'
                    )}
                  </button>
                </div>
                
                {/* Quick Actions */}
                <div className="flex flex-wrap gap-2 mt-3">
                  {[
                    'Analyze my workloads and suggest optimizations',
                    'Add a new ETL Jobs workload',
                    'What\'s my total monthly cost?',
                    'How can I reduce my Databricks spend?',
                    'Compare serverless vs classic SQL',
                  ].map((suggestion) => (
                    <button
                      key={suggestion}
                      onClick={() => setChatInput(suggestion)}
                      className="text-xs px-3 py-1.5 rounded-full bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] transition-colors"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* AI Assistant Compare Tab */}
        {activeTab === 'assistant-compare' && (
          <div className="space-y-6">
            {/* Test Selection for AI Assistant */}
            <div className="card p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-[var(--text-primary)]">AI Assistant Test Scenario</h3>
                <button 
                  onClick={loadSystemPrompt}
                  className="text-xs text-lava-600 hover:underline flex items-center gap-1"
                >
                  <DocumentTextIcon className="w-4 h-4" />
                  View System Prompt & Tools
                </button>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
                {Object.entries(assistantPrompts).map(([key, prompt]) => (
                  <button
                    key={key}
                    onClick={() => {
                      setSelectedAssistantTest(key)
                      setCustomPrompt('')
                    }}
                    className={clsx(
                      'p-3 rounded-lg border text-left transition-all',
                      selectedAssistantTest === key && !customPrompt
                        ? 'border-lava-500 bg-lava-50 dark:bg-lava-900/20'
                        : 'border-[var(--border-primary)] hover:border-lava-300'
                    )}
                  >
                    <span className="block font-medium text-[var(--text-primary)] text-sm">
                      {prompt.name}
                    </span>
                    <span className="block text-xs text-[var(--text-muted)] mt-1 line-clamp-2">
                      {prompt.description}
                    </span>
                  </button>
                ))}
              </div>
              
              <div className="mt-4">
                <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                  Or enter custom prompt:
                </label>
                <textarea
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  placeholder="Enter your own prompt to test..."
                  className="w-full p-3 border border-[var(--border-primary)] rounded-lg bg-[var(--bg-secondary)] text-[var(--text-primary)] text-sm"
                  rows={3}
                />
              </div>
              
              <div className="mt-4 p-3 bg-[var(--bg-secondary)] rounded-lg text-sm">
                <span className="font-medium text-[var(--text-primary)]">Test Context:</span>
                <span className="text-[var(--text-muted)] ml-2">
                  3 sample workloads (ETL Pipeline, Analytics Warehouse, Dev Cluster) • AWS us-east-1 • PREMIUM tier
                </span>
              </div>
            </div>

            <div className="flex justify-center">
              <button
                onClick={runAssistantComparison}
                disabled={isAssistantComparing}
                className="btn-primary px-8 py-3 flex items-center gap-2"
              >
                {isAssistantComparing ? (
                  <>
                    <ArrowPathIcon className="w-5 h-5 animate-spin" />
                    Testing Both Models with AI Assistant...
                  </>
                ) : (
                  <>
                    <ChatBubbleLeftRightIcon className="w-5 h-5" />
                    Compare AI Assistant Backends
                  </>
                )}
              </button>
            </div>

            {assistantComparisonResult && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-6"
              >
                {/* Error Display */}
                {(assistantComparisonResult as any).error && (
                  <div className="card p-4 bg-red-50 dark:bg-red-900/20 border border-red-300 dark:border-red-700">
                    <h4 className="font-medium text-red-700 dark:text-red-300 mb-2 flex items-center gap-2">
                      <ExclamationTriangleIcon className="w-5 h-5" />
                      Error
                    </h4>
                    <p className="text-sm text-red-600 dark:text-red-400 whitespace-pre-wrap">
                      {(assistantComparisonResult as any).error}
                    </p>
                    {(assistantComparisonResult as any).traceback && (
                      <pre className="mt-2 text-xs bg-red-100 dark:bg-red-900/40 p-2 rounded overflow-x-auto">
                        {(assistantComparisonResult as any).traceback}
                      </pre>
                    )}
                  </div>
                )}

                {/* Prompt Used */}
                {assistantComparisonResult.prompt && (
                  <div className="card p-4 bg-[var(--bg-secondary)]">
                    <h4 className="font-medium text-[var(--text-primary)] mb-2">Prompt Tested:</h4>
                    <p className="text-sm text-[var(--text-secondary)] whitespace-pre-wrap">
                      {assistantComparisonResult.prompt}
                    </p>
                  </div>
                )}

                {/* Comparison Summary */}
                {assistantComparisonResult.comparison && Object.keys(assistantComparisonResult.comparison).length > 0 && (
                  <div className="card p-6 bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20">
                    <h3 className="font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
                      <ChartBarIcon className="w-5 h-5 text-green-600" />
                      AI Assistant Comparison Summary
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <span className="text-sm text-[var(--text-muted)]">Faster Model</span>
                        <p className="font-semibold text-green-600">{assistantComparisonResult.comparison.faster_model}</p>
                      </div>
                      <div>
                        <span className="text-sm text-[var(--text-muted)]">Latency Difference</span>
                        <p className="font-mono">{formatLatency(assistantComparisonResult.comparison.latency_difference_ms || 0)}</p>
                      </div>
                      <div>
                        <span className="text-sm text-[var(--text-muted)]">Sonnet Response</span>
                        <p className="font-mono text-blue-600">{formatNumber(assistantComparisonResult.comparison.sonnet_response_length || 0)} chars</p>
                      </div>
                      <div>
                        <span className="text-sm text-[var(--text-muted)]">Opus Response</span>
                        <p className="font-mono text-purple-600">{formatNumber(assistantComparisonResult.comparison.opus_response_length || 0)} chars</p>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 mt-4">
                      <div>
                        <span className="text-sm text-[var(--text-muted)]">Sonnet Tools Used</span>
                        <p className="font-mono text-blue-600">{assistantComparisonResult.comparison.sonnet_tools_used || 0}</p>
                      </div>
                      <div>
                        <span className="text-sm text-[var(--text-muted)]">Opus Tools Used</span>
                        <p className="font-mono text-purple-600">{assistantComparisonResult.comparison.opus_tools_used || 0}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Individual Results */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {Object.entries(assistantComparisonResult.results).map(([modelId, result]) => {
                    const modelInfo = MODEL_INFO[modelId as keyof typeof MODEL_INFO]
                    return (
                      <div 
                        key={modelId}
                        className={clsx(
                          'card p-4 border-t-4',
                          modelInfo?.color === 'blue' ? 'border-t-blue-500' : 'border-t-purple-500'
                        )}
                      >
                        <div className="flex items-center justify-between mb-4">
                          <h4 className="font-semibold">{result.model}</h4>
                          {result.success ? (
                            <CheckCircleIcon className="w-5 h-5 text-green-500" />
                          ) : (
                            <XCircleIcon className="w-5 h-5 text-red-500" />
                          )}
                        </div>

                        {result.success ? (
                          <>
                            <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
                              <div className="bg-[var(--bg-secondary)] p-2 rounded">
                                <span className="text-[var(--text-muted)]">Latency</span>
                                <p className="font-mono font-semibold">
                                  {result.metrics?.total_latency_seconds?.toFixed(2)}s
                                </p>
                              </div>
                              <div className="bg-[var(--bg-secondary)] p-2 rounded">
                                <span className="text-[var(--text-muted)]">Response Length</span>
                                <p className="font-mono font-semibold">
                                  {formatNumber(result.response_length || 0)} chars
                                </p>
                              </div>
                            </div>

                            {result.tool_calls_made && result.tool_calls_made.length > 0 && (
                              <div className="mb-4">
                                <span className="text-sm text-[var(--text-muted)]">Tools Used:</span>
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {result.tool_calls_made.map((tool, idx) => (
                                    <span key={idx} className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs rounded">
                                      {tool}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {result.proposed_workloads !== undefined && result.proposed_workloads > 0 && (
                              <div className="mb-4 text-sm">
                                <span className="text-[var(--text-muted)]">Proposed Workloads: </span>
                                <span className="font-semibold text-green-600">{result.proposed_workloads}</span>
                              </div>
                            )}

                            <div className="mt-4">
                              <span className="text-sm text-[var(--text-muted)]">Response:</span>
                              <div className="mt-1 p-3 bg-[var(--bg-secondary)] rounded-lg text-sm max-h-80 overflow-y-auto prose prose-sm dark:prose-invert max-w-none">
                                <ReactMarkdown>
                                  {result.response || ''}
                                </ReactMarkdown>
                              </div>
                            </div>
                          </>
                        ) : (
                          <div className="text-red-500 text-sm bg-red-50 dark:bg-red-900/20 p-3 rounded">
                            <p className="font-medium">{result.error}</p>
                            {result.traceback && (
                              <pre className="mt-2 text-xs overflow-x-auto">{result.traceback}</pre>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </motion.div>
            )}
          </div>
        )}

        {/* AI Assistant Single Test Tab */}
        {activeTab === 'assistant' && (
          <div className="space-y-6">
            <div className="card p-4">
              <h3 className="font-semibold text-[var(--text-primary)] mb-3">Select Model for AI Assistant</h3>
              <div className="flex gap-3 mb-4">
                {Object.entries(MODEL_INFO).map(([modelId, info]) => (
                  <button
                    key={modelId}
                    onClick={() => setSelectedModel(modelId)}
                    className={clsx(
                      'flex-1 p-3 rounded-lg border transition-all',
                      selectedModel === modelId
                        ? info.color === 'blue' 
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-purple-500 bg-purple-50 dark:bg-purple-900/20'
                        : 'border-[var(--border-primary)] hover:border-gray-400'
                    )}
                  >
                    <span className="font-medium">{info.name}</span>
                  </button>
                ))}
              </div>

              <h3 className="font-semibold text-[var(--text-primary)] mb-3 mt-6">Select Test Scenario</h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {Object.entries(assistantPrompts).map(([key, prompt]) => (
                  <button
                    key={key}
                    onClick={() => {
                      setSelectedAssistantTest(key)
                      setCustomPrompt('')
                    }}
                    className={clsx(
                      'p-3 rounded-lg border text-left transition-all',
                      selectedAssistantTest === key && !customPrompt
                        ? 'border-lava-500 bg-lava-50 dark:bg-lava-900/20'
                        : 'border-[var(--border-primary)] hover:border-lava-300'
                    )}
                  >
                    <span className="block font-medium text-[var(--text-primary)] text-sm">
                      {prompt.name}
                    </span>
                  </button>
                ))}
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                  Or enter custom prompt:
                </label>
                <textarea
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  placeholder="Enter your own prompt..."
                  className="w-full p-3 border border-[var(--border-primary)] rounded-lg bg-[var(--bg-secondary)] text-[var(--text-primary)] text-sm"
                  rows={3}
                />
              </div>
            </div>

            <div className="flex justify-center">
              <button
                onClick={runAssistantTest}
                disabled={isAssistantTesting}
                className="btn-primary px-8 py-3 flex items-center gap-2"
              >
                {isAssistantTesting ? (
                  <>
                    <ArrowPathIcon className="w-5 h-5 animate-spin" />
                    Running AI Assistant Test...
                  </>
                ) : (
                  <>
                    <WrenchScrewdriverIcon className="w-5 h-5" />
                    Run AI Assistant Test
                  </>
                )}
              </button>
            </div>

            {assistantResult && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="card p-6"
              >
                <div className="flex items-center justify-between mb-4">
                  <h4 className="font-semibold text-lg">{assistantResult.model} AI Assistant Results</h4>
                  {assistantResult.success ? (
                    <CheckCircleIcon className="w-6 h-6 text-green-500" />
                  ) : (
                    <XCircleIcon className="w-6 h-6 text-red-500" />
                  )}
                </div>

                {assistantResult.success ? (
                  <>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                      <div className="bg-[var(--bg-secondary)] p-3 rounded-lg">
                        <span className="text-sm text-[var(--text-muted)]">Total Latency</span>
                        <p className="text-xl font-mono font-bold">
                          {assistantResult.metrics?.total_latency_seconds?.toFixed(2)}s
                        </p>
                      </div>
                      <div className="bg-[var(--bg-secondary)] p-3 rounded-lg">
                        <span className="text-sm text-[var(--text-muted)]">Response Length</span>
                        <p className="text-xl font-mono font-bold">
                          {formatNumber(assistantResult.response_length || 0)}
                        </p>
                      </div>
                      <div className="bg-[var(--bg-secondary)] p-3 rounded-lg">
                        <span className="text-sm text-[var(--text-muted)]">Tools Called</span>
                        <p className="text-xl font-mono font-bold">
                          {assistantResult.tool_calls_made?.length || 0}
                        </p>
                      </div>
                      <div className="bg-[var(--bg-secondary)] p-3 rounded-lg">
                        <span className="text-sm text-[var(--text-muted)]">Workloads Proposed</span>
                        <p className="text-xl font-mono font-bold">
                          {assistantResult.proposed_workloads || 0}
                        </p>
                      </div>
                    </div>

                    {assistantResult.context && (
                      <div className="mb-4 p-3 bg-[var(--bg-secondary)] rounded-lg text-sm">
                        <span className="font-medium">Context:</span>
                        <span className="ml-2 text-[var(--text-muted)]">
                          {assistantResult.context.workloads_count} workloads loaded • 
                          {assistantResult.context.conversation_length} messages in history
                        </span>
                      </div>
                    )}

                    {assistantResult.tool_calls_made && assistantResult.tool_calls_made.length > 0 && (
                      <div className="mb-4">
                        <h5 className="font-medium mb-2">Tools Used:</h5>
                        <div className="flex flex-wrap gap-2">
                          {assistantResult.tool_calls_made.map((tool, idx) => (
                            <span key={idx} className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-sm rounded-full">
                              {tool}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    <div>
                      <h5 className="font-medium mb-2">Full Response:</h5>
                      <div className="p-4 bg-[var(--bg-secondary)] rounded-lg max-h-96 overflow-y-auto prose prose-sm dark:prose-invert max-w-none">
                        <ReactMarkdown>
                          {assistantResult.response || ''}
                        </ReactMarkdown>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="text-red-500 bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
                    <ExclamationTriangleIcon className="w-5 h-5 inline mr-2" />
                    {assistantResult.error}
                    {assistantResult.traceback && (
                      <pre className="mt-4 text-xs overflow-x-auto bg-red-100 dark:bg-red-900/40 p-3 rounded">
                        {assistantResult.traceback}
                      </pre>
                    )}
                  </div>
                )}
              </motion.div>
            )}
          </div>
        )}

        {/* Raw API Test Selection */}
        {(activeTab === 'compare' || activeTab === 'single') && (
          <div className="card p-4 mb-6">
            <h3 className="font-semibold text-[var(--text-primary)] mb-3">Select Raw API Test Scenario</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(testPrompts).map(([key, prompt]) => (
                <button
                  key={key}
                  onClick={() => setSelectedTest(key)}
                  className={clsx(
                    'p-3 rounded-lg border text-left transition-all',
                    selectedTest === key
                      ? 'border-lava-500 bg-lava-50 dark:bg-lava-900/20'
                      : 'border-[var(--border-primary)] hover:border-lava-300'
                  )}
                >
                  <span className="block font-medium text-[var(--text-primary)] text-sm">
                    {prompt.name}
                  </span>
                  <span className="block text-xs text-[var(--text-muted)] mt-1">
                    {prompt.description}
                  </span>
                  <span className="block text-xs text-[var(--text-muted)] mt-1 font-mono">
                    ~{prompt.expected_max_tokens} tokens
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'compare' && (
          <div className="space-y-6">
            <div className="flex justify-center">
              <button
                onClick={runComparison}
                disabled={isComparing}
                className="btn-primary px-8 py-3 flex items-center gap-2"
              >
                {isComparing ? (
                  <>
                    <ArrowPathIcon className="w-5 h-5 animate-spin" />
                    Running Raw API Comparison...
                  </>
                ) : (
                  <>
                    <ChartBarIcon className="w-5 h-5" />
                    Compare Raw API
                  </>
                )}
              </button>
            </div>

            {comparisonResult && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-6"
              >
                {/* Comparison Summary */}
                {comparisonResult.comparison && Object.keys(comparisonResult.comparison).length > 0 && (
                  <div className="card p-6 bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20">
                    <h3 className="font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
                      <ChartBarIcon className="w-5 h-5 text-green-600" />
                      Raw API Comparison Summary
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <span className="text-sm text-[var(--text-muted)]">Faster Model</span>
                        <p className="font-semibold text-green-600">{comparisonResult.comparison.faster_model}</p>
                      </div>
                      <div>
                        <span className="text-sm text-[var(--text-muted)]">Latency Difference</span>
                        <p className="font-mono">{formatLatency(comparisonResult.comparison.latency_difference_ms || 0)}</p>
                      </div>
                      <div>
                        <span className="text-sm text-[var(--text-muted)]">Sonnet Speed</span>
                        <p className="font-mono text-blue-600">{comparisonResult.comparison.sonnet_tokens_per_sec} tok/s</p>
                      </div>
                      <div>
                        <span className="text-sm text-[var(--text-muted)]">Opus Speed</span>
                        <p className="font-mono text-purple-600">{comparisonResult.comparison.opus_tokens_per_sec} tok/s</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Individual Results */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {Object.entries(comparisonResult.results).map(([modelId, result]) => {
                    const modelInfo = MODEL_INFO[modelId as keyof typeof MODEL_INFO]
                    return (
                      <div 
                        key={modelId}
                        className={clsx(
                          'card p-4 border-t-4',
                          modelInfo?.color === 'blue' ? 'border-t-blue-500' : 'border-t-purple-500'
                        )}
                      >
                        <div className="flex items-center justify-between mb-4">
                          <h4 className="font-semibold">{result.model}</h4>
                          {result.success ? (
                            <CheckCircleIcon className="w-5 h-5 text-green-500" />
                          ) : (
                            <XCircleIcon className="w-5 h-5 text-red-500" />
                          )}
                        </div>

                        {result.success ? (
                          <>
                            <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
                              <div className="bg-[var(--bg-secondary)] p-2 rounded">
                                <span className="text-[var(--text-muted)]">Latency</span>
                                <p className="font-mono font-semibold">
                                  {formatLatency(result.metrics?.total_latency_ms || 0)}
                                </p>
                              </div>
                              <div className="bg-[var(--bg-secondary)] p-2 rounded">
                                <span className="text-[var(--text-muted)]">Tokens/sec</span>
                                <p className="font-mono font-semibold">
                                  {result.metrics?.tokens_per_second}
                                </p>
                              </div>
                              <div className="bg-[var(--bg-secondary)] p-2 rounded">
                                <span className="text-[var(--text-muted)]">Input Tokens</span>
                                <p className="font-mono">
                                  {formatNumber(result.metrics?.input_tokens || 0)}
                                </p>
                              </div>
                              <div className="bg-[var(--bg-secondary)] p-2 rounded">
                                <span className="text-[var(--text-muted)]">Output Tokens</span>
                                <p className="font-mono">
                                  {formatNumber(result.metrics?.output_tokens || 0)}
                                </p>
                              </div>
                            </div>

                            <div className="mt-4">
                              <span className="text-sm text-[var(--text-muted)]">Response Preview:</span>
                              <div className="mt-1 p-3 bg-[var(--bg-secondary)] rounded-lg text-sm max-h-40 overflow-y-auto">
                                {result.content?.substring(0, 500)}
                                {(result.content?.length || 0) > 500 && '...'}
                              </div>
                            </div>
                          </>
                        ) : (
                          <div className="text-red-500 text-sm bg-red-50 dark:bg-red-900/20 p-3 rounded">
                            {result.error}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </motion.div>
            )}
          </div>
        )}

        {activeTab === 'single' && (
          <div className="space-y-6">
            <div className="card p-4">
              <h3 className="font-semibold text-[var(--text-primary)] mb-3">Select Model</h3>
              <div className="flex gap-3">
                {Object.entries(MODEL_INFO).map(([modelId, info]) => (
                  <button
                    key={modelId}
                    onClick={() => setSelectedModel(modelId)}
                    className={clsx(
                      'flex-1 p-3 rounded-lg border transition-all',
                      selectedModel === modelId
                        ? info.color === 'blue' 
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-purple-500 bg-purple-50 dark:bg-purple-900/20'
                        : 'border-[var(--border-primary)] hover:border-gray-400'
                    )}
                  >
                    <span className="font-medium">{info.name}</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="flex justify-center">
              <button
                onClick={runSingleTest}
                disabled={isLoading}
                className="btn-primary px-8 py-3 flex items-center gap-2"
              >
                {isLoading ? (
                  <>
                    <ArrowPathIcon className="w-5 h-5 animate-spin" />
                    Running Test...
                  </>
                ) : (
                  <>
                    <PlayIcon className="w-5 h-5" />
                    Run Single Test
                  </>
                )}
              </button>
            </div>

            {singleResult && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="card p-6"
              >
                <div className="flex items-center justify-between mb-4">
                  <h4 className="font-semibold text-lg">{singleResult.model} Results</h4>
                  {singleResult.success ? (
                    <CheckCircleIcon className="w-6 h-6 text-green-500" />
                  ) : (
                    <XCircleIcon className="w-6 h-6 text-red-500" />
                  )}
                </div>

                {singleResult.success ? (
                  <>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                      <div className="bg-[var(--bg-secondary)] p-3 rounded-lg">
                        <span className="text-sm text-[var(--text-muted)]">Total Latency</span>
                        <p className="text-xl font-mono font-bold">
                          {formatLatency(singleResult.metrics?.total_latency_ms || 0)}
                        </p>
                      </div>
                      <div className="bg-[var(--bg-secondary)] p-3 rounded-lg">
                        <span className="text-sm text-[var(--text-muted)]">Tokens/Second</span>
                        <p className="text-xl font-mono font-bold">
                          {singleResult.metrics?.tokens_per_second}
                        </p>
                      </div>
                      <div className="bg-[var(--bg-secondary)] p-3 rounded-lg">
                        <span className="text-sm text-[var(--text-muted)]">Input Tokens</span>
                        <p className="text-xl font-mono font-bold">
                          {formatNumber(singleResult.metrics?.input_tokens || 0)}
                        </p>
                      </div>
                      <div className="bg-[var(--bg-secondary)] p-3 rounded-lg">
                        <span className="text-sm text-[var(--text-muted)]">Output Tokens</span>
                        <p className="text-xl font-mono font-bold">
                          {formatNumber(singleResult.metrics?.output_tokens || 0)}
                        </p>
                      </div>
                    </div>

                    <div>
                      <h5 className="font-medium mb-2">Full Response:</h5>
                      <div className="p-4 bg-[var(--bg-secondary)] rounded-lg max-h-96 overflow-y-auto prose prose-sm dark:prose-invert max-w-none">
                        <ReactMarkdown>
                          {singleResult.content || ''}
                        </ReactMarkdown>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="text-red-500 bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
                    <ExclamationTriangleIcon className="w-5 h-5 inline mr-2" />
                    {singleResult.error}
                  </div>
                )}
              </motion.div>
            )}
          </div>
        )}

        {activeTab === 'stress' && (
          <div className="space-y-6">
            <div className="card p-4">
              <h3 className="font-semibold text-[var(--text-primary)] mb-3">Token Stress Test</h3>
              <p className="text-sm text-[var(--text-secondary)] mb-4">
                Test the maximum token generation capacity of each model. This pushes the model to generate
                as many tokens as possible up to the OTPM limit.
              </p>
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                  Target Output Tokens
                </label>
                <input
                  type="range"
                  min="1000"
                  max="20000"
                  step="500"
                  value={stressTestTokens}
                  onChange={(e) => setStressTestTokens(parseInt(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-sm text-[var(--text-muted)] mt-1">
                  <span>1,000</span>
                  <span className="font-mono font-semibold text-lava-600">
                    {formatNumber(stressTestTokens)} tokens
                  </span>
                  <span>20,000</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <span className="text-blue-700 dark:text-blue-300">Sonnet 4.5 OTPM Limit:</span>
                  <span className="float-right font-mono">{formatNumber(5000)}</span>
                  {stressTestTokens > 5000 && (
                    <p className="text-xs text-orange-600 mt-1">⚠️ Exceeds limit - will be capped</p>
                  )}
                </div>
                <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                  <span className="text-purple-700 dark:text-purple-300">Opus 4.5 OTPM Limit:</span>
                  <span className="float-right font-mono">{formatNumber(20000)}</span>
                  {stressTestTokens > 20000 && (
                    <p className="text-xs text-orange-600 mt-1">⚠️ Exceeds limit - will be capped</p>
                  )}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => runStressTest('databricks-claude-sonnet-4-5')}
                disabled={isStressTesting}
                className="btn-secondary p-4 flex flex-col items-center gap-2 border-2 border-blue-300 hover:border-blue-500"
              >
                {isStressTesting ? (
                  <ArrowPathIcon className="w-6 h-6 animate-spin" />
                ) : (
                  <SparklesIcon className="w-6 h-6 text-blue-600" />
                )}
                <span>Stress Test Sonnet 4.5</span>
              </button>
              <button
                onClick={() => runStressTest('databricks-claude-opus-4-5')}
                disabled={isStressTesting}
                className="btn-secondary p-4 flex flex-col items-center gap-2 border-2 border-purple-300 hover:border-purple-500"
              >
                {isStressTesting ? (
                  <ArrowPathIcon className="w-6 h-6 animate-spin" />
                ) : (
                  <SparklesIcon className="w-6 h-6 text-purple-600" />
                )}
                <span>Stress Test Opus 4.5</span>
              </button>
            </div>

            {stressResult && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="card p-6"
              >
                <div className="flex items-center justify-between mb-4">
                  <h4 className="font-semibold text-lg">
                    {stressResult.model} Stress Test Results
                  </h4>
                  {stressResult.success ? (
                    <CheckCircleIcon className="w-6 h-6 text-green-500" />
                  ) : (
                    <XCircleIcon className="w-6 h-6 text-red-500" />
                  )}
                </div>

                {stressResult.success ? (
                  <>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                      <div className="bg-[var(--bg-secondary)] p-3 rounded-lg">
                        <span className="text-sm text-[var(--text-muted)]">Total Time</span>
                        <p className="text-xl font-mono font-bold">
                          {stressResult.metrics?.total_latency_seconds}s
                        </p>
                      </div>
                      <div className="bg-[var(--bg-secondary)] p-3 rounded-lg">
                        <span className="text-sm text-[var(--text-muted)]">Output Tokens</span>
                        <p className="text-xl font-mono font-bold">
                          {formatNumber(stressResult.actual_output_tokens)}
                        </p>
                      </div>
                      <div className="bg-[var(--bg-secondary)] p-3 rounded-lg">
                        <span className="text-sm text-[var(--text-muted)]">Tokens/Second</span>
                        <p className="text-xl font-mono font-bold">
                          {stressResult.metrics?.tokens_per_second}
                        </p>
                      </div>
                      <div className="bg-[var(--bg-secondary)] p-3 rounded-lg">
                        <span className="text-sm text-[var(--text-muted)]">Utilization</span>
                        <p className="text-xl font-mono font-bold">
                          {stressResult.metrics?.output_token_utilization}%
                        </p>
                      </div>
                    </div>

                    <div className="mb-4">
                      <div className="flex justify-between text-sm mb-1">
                        <span>Token Generation Progress</span>
                        <span>{formatNumber(stressResult.actual_output_tokens)} / {formatNumber(stressResult.target_output_tokens)}</span>
                      </div>
                      <div className="w-full bg-[var(--bg-tertiary)] rounded-full h-3">
                        <div 
                          className="bg-lava-600 h-3 rounded-full transition-all"
                          style={{ width: `${Math.min(100, stressResult.metrics?.output_token_utilization || 0)}%` }}
                        />
                      </div>
                    </div>

                    <div className="text-sm text-[var(--text-muted)]">
                      <span className="font-medium">Finish Reason: </span>
                      <span className={clsx(
                        'px-2 py-0.5 rounded',
                        stressResult.finish_reason === 'stop' 
                          ? 'bg-green-100 text-green-700' 
                          : 'bg-yellow-100 text-yellow-700'
                      )}>
                        {stressResult.finish_reason}
                      </span>
                    </div>

                    <div className="mt-4">
                      <h5 className="font-medium mb-2">Response Preview:</h5>
                      <div className="p-4 bg-[var(--bg-secondary)] rounded-lg max-h-60 overflow-y-auto text-sm">
                        {stressResult.content_preview}
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="text-red-500 bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
                    <ExclamationTriangleIcon className="w-5 h-5 inline mr-2" />
                    {stressResult.error}
                  </div>
                )}
              </motion.div>
            )}
          </div>
        )}

        {/* System Prompt Modal */}
        {showSystemPrompt && systemPromptInfo && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-[var(--bg-primary)] rounded-lg shadow-xl max-w-5xl w-full max-h-[90vh] overflow-hidden"
            >
              <div className="p-4 border-b border-[var(--border-primary)] flex justify-between items-center">
                <h3 className="font-semibold text-[var(--text-primary)]">
                  AI Assistant System Prompt & Tools
                </h3>
                <button 
                  onClick={() => setShowSystemPrompt(false)}
                  className="text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                >
                  <XCircleIcon className="w-6 h-6" />
                </button>
              </div>
              <div className="p-4 overflow-y-auto max-h-[calc(90vh-80px)]">
                <div className="mb-4">
                  <span className="text-sm text-[var(--text-muted)]">
                    System Prompt Length: {formatNumber(systemPromptInfo.system_prompt_length)} characters
                  </span>
                </div>
                
                <h4 className="font-medium text-[var(--text-primary)] mb-3">Available Tools ({systemPromptInfo.tools_count}):</h4>
                <div className="space-y-3 mb-6">
                  {systemPromptInfo.tools?.map((tool: any, idx: number) => (
                    <details key={idx} className="bg-[var(--bg-secondary)] rounded-lg overflow-hidden">
                      <summary className="p-3 cursor-pointer hover:bg-[var(--bg-tertiary)] flex items-center gap-2">
                        <span className="font-semibold text-lava-600">{tool.name}</span>
                      </summary>
                      <div className="p-3 pt-0 border-t border-[var(--border-primary)]">
                        <div className="mb-2">
                          <span className="text-xs font-medium text-[var(--text-muted)]">Description:</span>
                          <p className="text-sm text-[var(--text-primary)] whitespace-pre-wrap mt-1">{tool.description}</p>
                        </div>
                        {tool.parameters && Object.keys(tool.parameters).length > 0 && (
                          <div>
                            <span className="text-xs font-medium text-[var(--text-muted)]">Parameters:</span>
                            <pre className="text-xs bg-[var(--bg-primary)] p-2 rounded mt-1 overflow-x-auto">
                              {JSON.stringify(tool.parameters, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    </details>
                  ))}
                </div>

                <h4 className="font-medium text-[var(--text-primary)] mb-2">System Prompt:</h4>
                <pre className="p-4 bg-[var(--bg-secondary)] rounded-lg text-sm overflow-x-auto whitespace-pre-wrap max-h-96">
                  {systemPromptInfo.system_prompt}
                </pre>
              </div>
            </motion.div>
          </div>
        )}

        {/* Reference Info */}
        <div className="mt-8 p-4 bg-[var(--bg-secondary)] rounded-lg">
          <h4 className="font-medium text-[var(--text-primary)] mb-2">📚 Reference</h4>
          <p className="text-sm text-[var(--text-secondary)]">
            Rate limits based on{' '}
            <a 
              href="https://docs.databricks.com/aws/en/machine-learning/foundation-model-apis/limits"
              target="_blank"
              rel="noopener noreferrer"
              className="text-lava-600 hover:underline"
            >
              Databricks Foundation Model APIs limits documentation
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}
