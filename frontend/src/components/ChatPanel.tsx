/**
 * AI Chat Panel Component
 * 
 * Provides a conversational interface for the AI assistant to help users
 * create and manage estimates.
 */
import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import clsx from 'clsx'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  PaperAirplaneIcon,
  XMarkIcon,
  SparklesIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ArrowPathIcon,
  DocumentPlusIcon,
  TrashIcon,
  MinusIcon,
  ChevronUpIcon
} from '@heroicons/react/24/outline'
// AI Chat Panel uses fetch directly - no store needed

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  toolResults?: ToolResult[]
  isStreaming?: boolean
  isThinking?: boolean
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

interface ProposedWorkload {
  proposal_id: string
  workload_type: string
  workload_name: string
  reason: string
  [key: string]: any
}

interface ChatPanelProps {
  isOpen: boolean
  onClose: () => void
  onEstimateCreated?: (estimateId: string) => void
  onWorkloadConfirmed?: (workloadConfig: any) => Promise<void>  // Called when user confirms a proposed workload
  currentEstimate?: any
  currentWorkloads?: any[]
  // Calculated costs for each workload (keyed by item_id)
  itemCosts?: Record<string, { total: number; dbu: number; vm: number }>
  // Controlled panel width for push layout
  panelWidth?: number
  onWidthChange?: (width: number) => void
}

export function ChatPanel({
  isOpen,
  onClose,
  onEstimateCreated: _onEstimateCreated, // Reserved for future use
  onWorkloadConfirmed,
  currentEstimate,
  currentWorkloads,
  itemCosts,
  panelWidth: controlledWidth,
  onWidthChange
}: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [draftEstimate, setDraftEstimate] = useState<DraftEstimate | null>(null)
  const [draftWorkloads, setDraftWorkloads] = useState<DraftWorkload[]>([])
  const [proposedWorkloads, setProposedWorkloads] = useState<ProposedWorkload[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isMinimized, setIsMinimized] = useState(false)
  const [localPanelWidth, setLocalPanelWidth] = useState(380)
  const [isResizing, setIsResizing] = useState(false)
  const [showQuickActions, setShowQuickActions] = useState(true)
  
  // Use controlled width if provided, otherwise use local state
  const panelWidth = controlledWidth ?? localPanelWidth
  const setPanelWidth = onWidthChange ?? setLocalPanelWidth
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  
  // Calculate total cost from itemCosts - memoized for real-time updates
  const totalCost = useMemo(() => {
    if (!itemCosts || !currentWorkloads) return 0
    let total = 0
    currentWorkloads.forEach(w => {
      const itemId = w.item_id || w.line_item_id
      const costs = itemCosts[itemId]
      if (costs?.total) {
        total += costs.total
      }
    })
    return total
  }, [itemCosts, currentWorkloads])
  
  // Handle resize drag
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
  }, [])
  
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return
      const newWidth = window.innerWidth - e.clientX
      setPanelWidth(Math.min(Math.max(320, newWidth), 700))
    }
    
    const handleMouseUp = () => {
      setIsResizing(false)
    }
    
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'ew-resize'
      document.body.style.userSelect = 'none'
    }
    
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizing])
  
  // Auto-resize textarea as user types
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value)
    // Auto-resize
    const textarea = e.target
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px'
  }, [])
  
  // Quick action chips - context-aware suggestions with explicit tool-triggering prompts
  const quickActions = useMemo(() => {
    const hasWorkloads = (currentWorkloads?.length || 0) > 0
    if (!hasWorkloads) {
      return [
        { label: '💡 Optimize', action: 'Analyze my workloads and suggest specific optimizations to reduce costs.' },
        { label: '📊 Summary', action: 'Give me a summary of my current estimate with cost breakdown by workload type.' },
        { label: '➕ Add workload', action: 'Propose a new workload for my existing estimate. Ask me what type I need.' },
        { label: '❓ Pricing', action: 'Explain how Databricks pricing works for the workload types I have.' },
      ]
    }
    return [
      { label: '💡 Optimize', action: 'Analyze my workloads and suggest specific optimizations to reduce costs.' },
      { label: '📊 Summary', action: 'Give me a summary of my current estimate with cost breakdown by workload type.' },
      { label: '➕ Add workload', action: 'Propose a new workload for my existing estimate. Ask me what type I need.' },
      { label: '❓ Pricing', action: 'Explain how Databricks pricing works for the workload types I have.' },
    ]
  }, [currentWorkloads])

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

  // Build welcome message content based on context
  const buildWelcomeContent = useCallback(() => {
    if (currentEstimate) {
      // Estimate detail page with existing estimate
      const estimateName = currentEstimate.estimate_name || currentEstimate.name || 'Unnamed'
      const cloud = (currentEstimate.cloud || 'AWS').toUpperCase()
      const region = currentEstimate.region || 'unknown region'
      const tier = currentEstimate.tier || 'PREMIUM'
      const workloadCount = currentWorkloads?.length || 0
      
      // Build estimate context display (simplified - no workload list)
      let contextInfo = `📋 **Current Estimate:** ${estimateName}\n`
      contextInfo += `☁️ ${cloud} • ${region} • ${tier}\n`
      contextInfo += `📊 ${workloadCount} workload${workloadCount !== 1 ? 's' : ''}`
      
      // Use the memoized totalCost for real-time sync
      if (totalCost > 0) {
        contextInfo += ` • **$${totalCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}/mo**`
      }
      
      contextInfo += `\n\n---\n\nHow can I help you?\n`
      contextInfo += `• 📊 **Analyze** your workloads and costs\n`
      contextInfo += `• 💡 **Suggest optimizations** to save money\n`
      contextInfo += `• ➕ **Add new workloads** to your estimate\n`
      contextInfo += `• ❓ **Answer questions** about Databricks pricing`
      
      return contextInfo
    } else {
      // Estimate detail page without estimate (loading or new)
      return `Hi! I'm your Databricks pricing assistant. I can help you create and manage cost estimates.\n\n*Loading estimate details...*`
    }
  }, [currentEstimate, currentWorkloads, totalCost])
  
  // Add welcome message on first open
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      const welcomeMessage: Message = {
        id: 'welcome',
        role: 'assistant',
        content: buildWelcomeContent(),
        timestamp: new Date()
      }
      setMessages([welcomeMessage])
    }
  }, [isOpen, buildWelcomeContent])
  
  // Update welcome message when estimate data or costs change (only if no conversation has started)
  useEffect(() => {
    if (isOpen && messages.length === 1 && messages[0].id === 'welcome' && currentEstimate) {
      // Update the welcome message with fresh data including synced costs
      setMessages([{
        id: 'welcome',
        role: 'assistant',
        content: buildWelcomeContent(),
        timestamp: new Date()
      }])
    }
  }, [isOpen, currentEstimate, currentWorkloads, totalCost, buildWelcomeContent])

  const sendMessage = useCallback(async (directMessage?: string) => {
    const messageToSend = directMessage || inputValue.trim()
    if (!messageToSend || isLoading) return

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: messageToSend,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)
    setError(null)

    // Create placeholder for assistant response with thinking indicator
    const assistantMessageId = `assistant-${Date.now()}`
    setMessages(prev => [...prev, {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
      isThinking: true  // Show thinking indicator until content starts
    }])

    try {
      abortControllerRef.current = new AbortController()
      
      // Build enriched workloads context with actual calculated costs
      const enrichedWorkloads = (currentWorkloads || draftWorkloads || []).map(w => {
        // lineItems use line_item_id, drafts use draft_id
        const itemId = w.line_item_id || w.item_id || w.draft_id
        const costs = itemCosts?.[itemId]
        return {
          ...w,
          total_cost: costs?.total || w.total_cost || 0,
          dbu_cost: costs?.dbu || w.dbu_cost || 0,
          vm_cost: costs?.vm || w.vm_cost || 0
        }
      })
      
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: userMessage.content,
          conversation_id: conversationId,
          estimate_context: currentEstimate || draftEstimate,
          workloads_context: enrichedWorkloads,
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
                    ? { ...m, content: fullContent, isThinking: false }
                    : m
                ))
              } else if (chunk.type === 'tool_result') {
                toolResults.push({
                  tool: chunk.tool,
                  result: chunk.result
                })
              } else if (chunk.type === 'proposal') {
                // AI proposed a workload - add to pending proposals (deduplicate by proposal_id)
                if (chunk.workload && chunk.workload.proposal_id) {
                  setProposedWorkloads(prev => {
                    // Check if this proposal already exists
                    const exists = prev.some(p => p.proposal_id === chunk.workload.proposal_id)
                    if (exists) return prev
                    return [...prev, chunk.workload]
                  })
                }
              } else if (chunk.type === 'done') {
                // Only update proposals if there wasn't an error in the content
                // (Don't show stale proposals when AI service errors occur)
                const hasError = fullContent.includes('Error getting response') || fullContent.includes('AI service error')
                
                if (!hasError) {
                  // Update draft state from final response
                  if (chunk.estimate) {
                    setDraftEstimate(chunk.estimate)
                  }
                  if (chunk.workloads) {
                    setDraftWorkloads(chunk.workloads)
                  }
                  if (chunk.proposed_workloads && chunk.proposed_workloads.length > 0) {
                    setProposedWorkloads(chunk.proposed_workloads)
                  }
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
  }, [inputValue, isLoading, conversationId, currentEstimate, currentWorkloads, draftEstimate, draftWorkloads, itemCosts])

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
    // Clear all state
    setConversationId(null)
    setDraftEstimate(null)
    setDraftWorkloads([])
    setProposedWorkloads([])
    setError(null)
    
    // Restore welcome message with fresh context
    const welcomeMessage: Message = {
      id: 'welcome',
      role: 'assistant',
      content: buildWelcomeContent(),
      timestamp: new Date()
    }
    setMessages([welcomeMessage])
  }
  
  const handleConfirmWorkload = async (proposalId: string) => {
    if (!conversationId) return
    
    try {
      const response = await fetch(`/api/v1/chat/${conversationId}/confirm-workload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proposal_id: proposalId, confirmed: true })
      })
      
      if (!response.ok) throw new Error('Failed to confirm workload')
      
      const result = await response.json()
      
      // Remove from pending proposals
      setProposedWorkloads(prev => prev.filter(p => p.proposal_id !== proposalId))
      
      // Call the parent callback with the workload config and AWAIT the result
      if (onWorkloadConfirmed && result.workload_config) {
        try {
          await onWorkloadConfirmed(result.workload_config)
          
          // Only show success message AFTER the workload is actually created
          setMessages(prev => [...prev, {
            id: `system-${Date.now()}`,
            role: 'system',
            content: `✅ Workload "${result.workload_config?.workload_name}" added to estimate.`,
            timestamp: new Date()
          }])
        } catch (createErr: any) {
          // Show error if creation failed
          setMessages(prev => [...prev, {
            id: `system-${Date.now()}`,
            role: 'system',
            content: `❌ Failed to add workload: ${createErr.message || 'Database error'}. Please try again.`,
            timestamp: new Date()
          }])
          setError(createErr.message || 'Failed to add workload to database')
        }
      }
      
    } catch (err: any) {
      setError(err.message || 'Failed to confirm workload')
    }
  }
  
  const handleRejectWorkload = async (proposalId: string) => {
    if (!conversationId) return
    
    try {
      const response = await fetch(`/api/v1/chat/${conversationId}/confirm-workload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proposal_id: proposalId, confirmed: false })
      })
      
      if (!response.ok) throw new Error('Failed to reject workload')
      
      // Remove from pending proposals
      const rejected = proposedWorkloads.find(p => p.proposal_id === proposalId)
      setProposedWorkloads(prev => prev.filter(p => p.proposal_id !== proposalId))
      
      // Add info message
      setMessages(prev => [...prev, {
        id: `system-${Date.now()}`,
        role: 'system',
        content: `❌ Workload "${rejected?.workload_name}" proposal rejected.`,
        timestamp: new Date()
      }])
      
    } catch (err: any) {
      setError(err.message || 'Failed to reject workload')
    }
  }

  if (!isOpen) return null
  
  return (
    <>
      {/* Minimized Dock */}
      {isMinimized ? (
        <div className="fixed bottom-4 right-4 z-50">
          <button
            onClick={() => setIsMinimized(false)}
            className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-orange-500 to-amber-500 text-white rounded-full shadow-lg hover:shadow-xl"
          >
            <SparklesIcon className="w-5 h-5" />
            <span className="font-medium text-sm">AI Assistant</span>
            <ChevronUpIcon className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <div 
          ref={panelRef}
          className="fixed inset-y-0 right-0 bg-[var(--bg-primary)] border-l border-[var(--border-primary)] shadow-2xl z-50 flex flex-col"
          style={{ width: `min(100vw, ${panelWidth}px)` }}
        >
          {/* Resize Handle */}
          <div
            onMouseDown={handleMouseDown}
            className={clsx(
              "absolute left-0 top-0 bottom-0 w-1.5 cursor-ew-resize hover:bg-orange-500/30 transition-colors z-10",
              isResizing && "bg-orange-500/50"
            )}
          >
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-12 rounded-full bg-[var(--border-secondary)] opacity-0 hover:opacity-100 transition-opacity" />
          </div>
          
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-primary)] bg-gradient-to-r from-[var(--bg-secondary)] to-[var(--bg-primary)]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center shadow-sm">
            <SparklesIcon className="w-4 h-4 text-white" />
          </div>
          <div>
            <h2 className="font-semibold text-sm text-[var(--text-primary)]">AI Assistant</h2>
            {conversationId ? (
              <span className="text-[10px] text-green-600 dark:text-green-400 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                Active session
              </span>
            ) : (
              <span className="text-[10px] text-[var(--text-muted)]">Ready to help</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={clearConversation}
            className="p-2 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 text-[var(--text-secondary)] hover:text-red-600 dark:hover:text-red-400 transition-colors"
            title="Clear conversation"
          >
            <TrashIcon className="w-4 h-4" />
          </button>
          <button
            onClick={() => setIsMinimized(true)}
            className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)] transition-colors"
            title="Minimize"
          >
            <MinusIcon className="w-4 h-4" />
          </button>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)] transition-colors"
            title="Close"
          >
            <XMarkIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Current Estimate Context - Shows the estimate being worked on */}
      {currentEstimate && (
        <div className="px-4 py-3 bg-gradient-to-r from-slate-50 to-slate-100 dark:from-slate-800/50 dark:to-slate-900/50 border-b border-[var(--border-primary)]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                <DocumentPlusIcon className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <div className="font-medium text-sm text-[var(--text-primary)] truncate max-w-[150px]">
                  {currentEstimate.estimate_name || currentEstimate.name || 'Estimate'}
                </div>
                <div className="flex items-center gap-1.5 text-[10px] text-[var(--text-muted)]">
                  <span className="px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium">
                    {(currentEstimate.cloud || 'AWS').toUpperCase()}
                  </span>
                  <span>{currentEstimate.region || 'N/A'}</span>
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] text-[var(--text-muted)] mb-0.5">
                {currentWorkloads?.length || 0} workload{(currentWorkloads?.length || 0) !== 1 ? 's' : ''}
              </div>
              <div className="font-bold text-base text-[var(--text-primary)]">
                {totalCost > 0 ? (
                  <span className="text-green-600 dark:text-green-400">
                    ${totalCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                ) : (
                  <span className="text-[var(--text-muted)]">—</span>
                )}
                <span className="text-[10px] font-normal text-[var(--text-muted)]">/mo</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Proposed Workloads - Awaiting Confirmation */}
      {proposedWorkloads.length > 0 && (
        <div className="px-4 py-3 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800">
          <div className="flex items-center gap-2 mb-3">
            <ExclamationCircleIcon className="w-4 h-4 text-amber-600" />
            <span className="text-sm font-medium text-amber-700 dark:text-amber-300">
              Proposed Workload{proposedWorkloads.length !== 1 ? 's' : ''} - Confirm to Add
            </span>
          </div>
          <div className="space-y-2">
            {proposedWorkloads.map((proposal) => (
              <div 
                key={proposal.proposal_id}
                className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-amber-200 dark:border-amber-700"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm text-gray-900 dark:text-gray-100 truncate">
                        {proposal.workload_name}
                      </span>
                      <span className="text-xs px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
                        {proposal.workload_type}
                      </span>
                    </div>
                    {proposal.reason && (
                      <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2">
                        {proposal.reason}
                      </p>
                    )}
                    <div className="flex flex-wrap gap-2 mt-2 text-xs text-gray-500 dark:text-gray-400">
                      {proposal.serverless_enabled && <span className="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded">Serverless</span>}
                      {proposal.photon_enabled && <span className="px-1.5 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded">Photon</span>}
                      {proposal.num_workers && <span>{proposal.num_workers} workers</span>}
                      {proposal.dbsql_warehouse_size && <span>{proposal.dbsql_warehouse_size}</span>}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <button
                      onClick={() => handleConfirmWorkload(proposal.proposal_id)}
                      className="p-1.5 rounded-full bg-green-100 hover:bg-green-200 dark:bg-green-900/30 dark:hover:bg-green-800/50 text-green-700 dark:text-green-400 transition-colors"
                      title="Confirm & Add"
                    >
                      <CheckCircleIcon className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleRejectWorkload(proposal.proposal_id)}
                      className="p-1.5 rounded-full bg-red-100 hover:bg-red-200 dark:bg-red-900/30 dark:hover:bg-red-800/50 text-red-700 dark:text-red-400 transition-colors"
                      title="Reject"
                    >
                      <XMarkIcon className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
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
              'w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5',
              message.role === 'user' 
                ? 'bg-gradient-to-br from-blue-500 to-blue-600' 
                : message.role === 'system'
                ? 'bg-gradient-to-br from-green-500 to-emerald-600'
                : 'bg-gradient-to-br from-orange-500 to-amber-500'
            )}>
              {message.role === 'user' ? (
                <span className="text-[10px] font-bold text-white">You</span>
              ) : message.role === 'system' ? (
                <CheckCircleIcon className="w-4 h-4 text-white" />
              ) : (
                <SparklesIcon className="w-4 h-4 text-white" />
              )}
            </div>

            {/* Message Content */}
            <div className={clsx(
              'flex-1 min-w-0',
              message.role === 'user' ? 'text-right' : 'text-left'
            )}>
              {/* Role Label */}
              <div className={clsx(
                'text-[11px] font-medium mb-1.5',
                message.role === 'user' 
                  ? 'text-blue-600 dark:text-blue-400' 
                  : message.role === 'system'
                  ? 'text-green-600 dark:text-green-400'
                  : 'text-orange-600 dark:text-orange-400'
              )}>
                {message.role === 'user' ? 'You' : message.role === 'system' ? 'System' : 'AI Assistant'}
              </div>
              
              <div className={clsx(
                'inline-block text-[13px] leading-[1.7]',
                message.role === 'user'
                  ? 'bg-blue-600 text-white px-4 py-2.5 rounded-2xl rounded-tr-md max-w-[85%] whitespace-pre-wrap text-left shadow-sm'
                  : message.role === 'system'
                  ? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-200 px-4 py-2.5 rounded-xl border border-green-200 dark:border-green-800'
                  : 'text-[var(--text-primary)] max-w-full'
              )}>
                {(message.isStreaming || message.isThinking) && !message.content ? (
                  <div className="flex items-center gap-3 px-2 py-2">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-orange-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-orange-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-orange-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span className="text-sm text-[var(--text-secondary)] italic">
                      {message.isThinking ? 'AI is thinking...' : 'Generating response...'}
                    </span>
                  </div>
                ) : message.role === 'user' ? (
                  // User messages - plain text with preserved whitespace
                  <span className="whitespace-pre-wrap">{message.content}</span>
                ) : (
                  // AI/System messages - enhanced markdown rendering
                  <div className="ai-message-content">
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]}
                      components={{
                        // Enhanced heading styles
                        h1: ({children}) => <h1 className="text-base font-bold text-[var(--text-primary)] mt-3 mb-2 pb-1 border-b border-[var(--border-primary)]">{children}</h1>,
                        h2: ({children}) => <h2 className="text-[14px] font-bold text-[var(--text-primary)] mt-3 mb-1.5">{children}</h2>,
                        h3: ({children}) => <h3 className="text-[13px] font-semibold text-[var(--text-primary)] mt-2 mb-1">{children}</h3>,
                        // Paragraphs with proper spacing
                        p: ({children}) => <p className="my-2 text-[var(--text-primary)] leading-relaxed">{children}</p>,
                        // Simple list styles
                        ul: ({children}) => <ul className="my-2 ml-4 space-y-1 list-disc">{children}</ul>,
                        ol: ({children}) => <ol className="my-2 ml-4 space-y-1 list-decimal">{children}</ol>,
                        li: ({children}) => <li className="text-[var(--text-primary)]">{children}</li>,
                        // Bold text
                        strong: ({children}) => <strong className="font-semibold text-[var(--text-primary)]">{children}</strong>,
                        // Italic
                        em: ({children}) => <em className="text-[var(--text-secondary)] italic">{children}</em>,
                        // Inline code
                        code: ({className, children}) => {
                          const isBlock = className?.includes('language-')
                          if (isBlock) {
                            return (
                              <code className="block bg-slate-900 dark:bg-slate-950 text-slate-100 p-3 rounded-lg text-xs font-mono overflow-x-auto my-3 border border-slate-700">
                                {children}
                              </code>
                            )
                          }
                          return (
                            <code className="px-1.5 py-0.5 bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded text-[12px] font-mono">
                              {children}
                            </code>
                          )
                        },
                        // Code blocks
                        pre: ({children}) => <pre className="my-3 overflow-hidden rounded-lg">{children}</pre>,
                        // Blockquotes
                        blockquote: ({children}) => (
                          <blockquote className="my-3 pl-3 border-l-3 border-orange-400 bg-orange-50 dark:bg-orange-900/10 py-2 pr-3 rounded-r-lg text-[var(--text-secondary)] italic">
                            {children}
                          </blockquote>
                        ),
                        // Horizontal rule
                        hr: () => <hr className="my-4 border-[var(--border-primary)]" />,
                        // Links
                        a: ({href, children}) => (
                          <a href={href} className="text-orange-600 dark:text-orange-400 hover:underline font-medium" target="_blank" rel="noopener noreferrer">
                            {children}
                          </a>
                        ),
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                  </div>
                )}
              </div>

              {/* Tool Results - More prominent styling */}
              {message.toolResults && message.toolResults.length > 0 && (
                <div className="mt-2.5 flex flex-wrap gap-2">
                  {message.toolResults.map((tr, idx) => (
                    <div
                      key={idx}
                      className="text-[11px] px-2.5 py-1.5 bg-slate-100 dark:bg-slate-800 rounded-lg flex items-center gap-1.5"
                    >
                      {tr.result?.success ? (
                        <CheckCircleIcon className="w-3.5 h-3.5 text-green-500" />
                      ) : (
                        <ArrowPathIcon className="w-3.5 h-3.5 text-orange-500" />
                      )}
                      <span className="font-medium text-slate-600 dark:text-slate-300">
                        {tr.tool.replace(/_/g, ' ')}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Timestamp */}
              <div className={clsx(
                'text-[10px] text-[var(--text-muted)] mt-2',
                message.role === 'user' ? 'text-right' : 'text-left'
              )}>
                {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          </div>
        ))}

        {/* Error Message */}
        {error && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
            <div className="flex items-start gap-2 text-sm text-red-700 dark:text-red-300">
              <ExclamationCircleIcon className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">{error.includes('400') ? 'Request failed' : 'Error'}</p>
                <p className="text-xs mt-1 opacity-80">
                  {error.includes('400') 
                    ? 'The conversation may be too long. Try clearing the chat and starting fresh.'
                    : error.includes('429')
                    ? 'Rate limited. Please wait a moment and try again.'
                    : error}
                </p>
                {error.includes('400') && (
                  <button
                    onClick={clearConversation}
                    className="mt-2 text-xs px-3 py-1.5 bg-red-100 dark:bg-red-800/50 rounded-lg hover:bg-red-200 dark:hover:bg-red-700/50 transition-colors font-medium"
                  >
                    Clear & restart
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-[var(--border-primary)] bg-gradient-to-t from-[var(--bg-secondary)] to-[var(--bg-primary)]">
        {/* Quick Action Chips - Always visible but collapsible */}
        {!isLoading && (
          <div className="mb-3">
            <button
              onClick={() => setShowQuickActions(!showQuickActions)}
              className="text-[10px] text-[var(--text-muted)] hover:text-orange-600 dark:hover:text-orange-400 flex items-center gap-1 mb-2 transition-colors"
            >
              <ChevronUpIcon className={clsx("w-3 h-3 transition-transform duration-200", showQuickActions ? "rotate-180" : "")} />
              {showQuickActions ? "Hide suggestions" : "Show suggestions"}
            </button>
            {showQuickActions && (
              <div className="flex flex-wrap gap-2">
                {quickActions.map((action: { label: string; action: string }, idx: number) => (
                  <button
                    key={idx}
                    onClick={() => sendMessage(action.action)}
                    className="text-[11px] px-3 py-2 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-primary)] hover:bg-orange-50 dark:hover:bg-orange-900/20 hover:border-orange-300 dark:hover:border-orange-700 hover:text-orange-700 dark:hover:text-orange-300 text-[var(--text-secondary)] transition-all duration-150 shadow-sm hover:shadow"
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        
        {/* Text Input with Auto-expand */}
        <div className="relative flex gap-2 items-end">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Ask about pricing, workloads, or optimization..."
              disabled={isLoading}
              rows={1}
              className="w-full resize-none rounded-xl border-2 border-[var(--border-primary)] bg-[var(--bg-primary)] px-4 py-3 text-[13px] leading-relaxed focus:outline-none focus:ring-0 focus:border-orange-400 dark:focus:border-orange-500 disabled:opacity-50 placeholder:text-[var(--text-muted)] shadow-sm transition-colors"
              style={{ minHeight: '48px', maxHeight: '150px' }}
            />
            {inputValue.length > 50 && (
              <span className="absolute right-3 bottom-2 text-[9px] text-[var(--text-muted)] bg-[var(--bg-secondary)] px-1 rounded">
                {inputValue.length}
              </span>
            )}
          </div>
          <button
            onClick={() => sendMessage()}
            disabled={!inputValue.trim() || isLoading}
            className="h-12 w-12 bg-gradient-to-br from-orange-500 to-amber-500 text-white rounded-xl hover:from-orange-600 hover:to-amber-600 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center shadow-md hover:shadow-lg transition-all duration-150 flex-shrink-0"
          >
            {isLoading ? (
              <ArrowPathIcon className="w-5 h-5 animate-spin" />
            ) : (
              <PaperAirplaneIcon className="w-5 h-5" />
            )}
          </button>
        </div>
        
        <div className="flex items-center justify-between mt-2.5 text-[9px] text-[var(--text-muted)]">
          <span>Shift+Enter for new line</span>
          <span>Powered by Claude Sonnet 4.5</span>
        </div>
      </div>
        </div>
      )}
    </>
  )
}

/**
 * Custom Sparkles Icon - Matches the provided SVG path
 */
function SparklesAnimatedIcon({ className }: { className?: string }) {
  return (
    <svg 
      xmlns="http://www.w3.org/2000/svg" 
      fill="none" 
      viewBox="0 0 24 24" 
      strokeWidth={1.5} 
      stroke="currentColor" 
      className={className}
    >
      <path 
        strokeLinecap="round" 
        strokeLinejoin="round" 
        d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" 
      />
    </svg>
  )
}

/**
 * AI Assistant Toggle Button
 * 
 * Fixed button in top right corner to open the chat panel.
 */
export function ChatToggleButton({ onClick, hasActiveConversation }: { onClick: () => void, hasActiveConversation?: boolean }) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "fixed top-4 right-4 w-10 h-10 rounded-lg shadow-lg flex items-center justify-center transition-all hover:scale-105 z-40",
        hasActiveConversation
          ? "bg-teal-600 hover:bg-teal-700"
          : "bg-gradient-to-br from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700"
      )}
      title="AI Assistant"
    >
      <SparklesAnimatedIcon className="w-5 h-5 text-white" />
      {hasActiveConversation && (
        <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white" />
      )}
    </button>
  )
}

