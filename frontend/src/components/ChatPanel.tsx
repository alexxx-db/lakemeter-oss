/**
 * AI Chat Panel Component
 * 
 * Provides a conversational interface for the AI assistant to help users
 * create and manage estimates.
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import clsx from 'clsx'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { motion, AnimatePresence } from 'framer-motion'
import {
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

interface ProposedWorkload {
  proposal_id: string
  workload_type: string
  workload_name: string
  reason: string
  [key: string]: any
}

interface ProposedEstimate {
  proposal_id: string
  name: string
  cloud: string
  region: string
  description?: string
  reason?: string
}

interface ChatPanelProps {
  isOpen: boolean
  onClose: () => void
  onEstimateCreated?: (estimateId: string) => void
  onEstimateConfirmed?: (estimateConfig: any) => Promise<void>  // Called when user confirms a proposed estimate
  onWorkloadConfirmed?: (workloadConfig: any) => Promise<void>  // Called when user confirms a proposed workload
  currentEstimate?: any
  currentWorkloads?: any[]
  // Calculated costs for each workload (keyed by item_id)
  itemCosts?: Record<string, { total: number; dbu: number; vm: number }>
  // Mode: 'estimates_list' for home page (create only), 'estimate_detail' for full functionality
  mode?: 'estimates_list' | 'estimate_detail'
}

export function ChatPanel({
  isOpen,
  onClose,
  onEstimateCreated,
  onEstimateConfirmed,
  onWorkloadConfirmed,
  currentEstimate,
  currentWorkloads,
  itemCosts,
  mode = 'estimate_detail'
}: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [draftEstimate, setDraftEstimate] = useState<DraftEstimate | null>(null)
  const [draftWorkloads, setDraftWorkloads] = useState<DraftWorkload[]>([])
  const [proposedWorkloads, setProposedWorkloads] = useState<ProposedWorkload[]>([])
  const [proposedEstimate, setProposedEstimate] = useState<ProposedEstimate | null>(null)
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

  // Build welcome message content based on context
  const buildWelcomeContent = useCallback(() => {
    if (mode === 'estimates_list') {
      // Estimates list page - create only mode
      return `Hi! I'm your Databricks pricing assistant. I can help you **create new estimates**.\n\nTell me about your project and I'll set up an estimate for you. For example:\n- "Create an estimate for a data lakehouse on AWS"\n- "I need to plan costs for our Azure ML platform"\n- "Set up a GCP estimate for our analytics team"\n\n💡 *Once created, you can click on the estimate to add workloads and get detailed recommendations.*`
    } else if (currentEstimate) {
      // Estimate detail page with existing estimate
      const estimateName = currentEstimate.estimate_name || currentEstimate.name || 'Unnamed'
      const cloud = (currentEstimate.cloud || 'AWS').toUpperCase()
      const region = currentEstimate.region || 'unknown region'
      const tier = currentEstimate.tier || 'PREMIUM'
      const workloadCount = currentWorkloads?.length || 0
      
      // Calculate total cost from itemCosts
      let totalCost = 0
      if (itemCosts && currentWorkloads) {
        currentWorkloads.forEach(w => {
          const itemId = w.item_id || w.line_item_id
          const costs = itemCosts[itemId]
          if (costs?.total) {
            totalCost += costs.total
          }
        })
      }
      
      // Build estimate context display (simplified - no workload list)
      let contextInfo = `📋 **Current Estimate:** ${estimateName}\n`
      contextInfo += `☁️ ${cloud} • ${region} • ${tier}\n`
      contextInfo += `📊 ${workloadCount} workload${workloadCount !== 1 ? 's' : ''}`
      
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
  }, [mode, currentEstimate, currentWorkloads, itemCosts])
  
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
  
  // Update welcome message when estimate data loads (only if no conversation has started)
  useEffect(() => {
    if (isOpen && messages.length === 1 && messages[0].id === 'welcome' && currentEstimate) {
      // Update the welcome message with fresh data
      setMessages([{
        id: 'welcome',
        role: 'assistant',
        content: buildWelcomeContent(),
        timestamp: new Date()
      }])
    }
  }, [isOpen, currentEstimate, currentWorkloads, itemCosts, buildWelcomeContent])

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
      
      // Build enriched workloads context with actual calculated costs
      const enrichedWorkloads = (currentWorkloads || draftWorkloads || []).map(w => {
        const itemId = w.item_id || w.draft_id
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
          stream: true,
          mode: mode
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
              } else if (chunk.type === 'proposal') {
                // AI proposed a workload - add to pending proposals
                if (chunk.workload) {
                  setProposedWorkloads(prev => [...prev, chunk.workload])
                }
              } else if (chunk.type === 'estimate_proposal') {
                // AI proposed an estimate - set pending proposal
                if (chunk.estimate) {
                  setProposedEstimate(chunk.estimate)
                }
              } else if (chunk.type === 'done') {
                // Update draft state from final response
                if (chunk.estimate) {
                  setDraftEstimate(chunk.estimate)
                }
                if (chunk.workloads) {
                  setDraftWorkloads(chunk.workloads)
                }
                if (chunk.proposed_workloads) {
                  setProposedWorkloads(chunk.proposed_workloads)
                }
                if (chunk.proposed_estimate) {
                  setProposedEstimate(chunk.proposed_estimate)
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
  }, [inputValue, isLoading, conversationId, currentEstimate, currentWorkloads, draftEstimate, draftWorkloads, itemCosts, mode])

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
    setProposedWorkloads([])
    setProposedEstimate(null)
    setError(null)
  }
  
  const handleConfirmEstimate = async () => {
    if (!conversationId || !proposedEstimate) return
    
    try {
      const response = await fetch(`/api/v1/chat/${conversationId}/confirm-estimate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmed: true })
      })
      
      if (!response.ok) throw new Error('Failed to confirm estimate')
      
      const result = await response.json()
      
      // Clear the proposal
      setProposedEstimate(null)
      
      // Call the parent callback with the estimate config and AWAIT the result
      // The callback will actually create the estimate in the database
      if (onEstimateConfirmed && result.estimate_config) {
        try {
          await onEstimateConfirmed(result.estimate_config)
          
          // Only show success message AFTER the estimate is actually created
          setMessages(prev => [...prev, {
            id: `system-${Date.now()}`,
            role: 'system',
            content: `✅ Estimate "${result.estimate_config?.estimate_name}" created! Click on it to add workloads.`,
            timestamp: new Date()
          }])
        } catch (createErr: any) {
          // Show error if creation failed
          setMessages(prev => [...prev, {
            id: `system-${Date.now()}`,
            role: 'system',
            content: `❌ Failed to create estimate: ${createErr.message || 'Database error'}. Please try again.`,
            timestamp: new Date()
          }])
          setError(createErr.message || 'Failed to create estimate in database')
        }
      }
      
    } catch (err: any) {
      setError(err.message || 'Failed to confirm estimate')
    }
  }
  
  const handleRejectEstimate = async () => {
    if (!conversationId) return
    
    try {
      const response = await fetch(`/api/v1/chat/${conversationId}/confirm-estimate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmed: false })
      })
      
      if (!response.ok) throw new Error('Failed to reject estimate')
      
      // Clear the proposal
      const name = proposedEstimate?.name
      setProposedEstimate(null)
      
      // Add info message
      setMessages(prev => [...prev, {
        id: `system-${Date.now()}`,
        role: 'system',
        content: `❌ Estimate "${name}" proposal rejected.`,
        timestamp: new Date()
      }])
      
    } catch (err: any) {
      setError(err.message || 'Failed to reject estimate')
    }
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

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div 
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className="fixed inset-y-0 right-0 w-full sm:w-[420px] bg-[var(--bg-primary)] border-l border-[var(--border-primary)] shadow-2xl z-50 flex flex-col"
        >
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

      {/* Proposed Estimate - Awaiting Confirmation */}
      {proposedEstimate && (
        <div className="px-4 py-3 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800">
          <div className="flex items-center gap-2 mb-2">
            <ExclamationCircleIcon className="w-4 h-4 text-amber-600" />
            <span className="text-sm font-medium text-amber-700 dark:text-amber-300">
              Proposed Estimate - Confirm to Create
            </span>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-amber-200 dark:border-amber-700">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-sm text-gray-900 dark:text-gray-100 truncate">
                    {proposedEstimate.name}
                  </span>
                </div>
                <div className="flex flex-wrap gap-2 text-xs text-gray-600 dark:text-gray-400">
                  <span className="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded">
                    {proposedEstimate.cloud?.toUpperCase()}
                  </span>
                  <span>{proposedEstimate.region}</span>
                </div>
                {proposedEstimate.description && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                    {proposedEstimate.description}
                  </p>
                )}
                {proposedEstimate.reason && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 italic">
                    💡 {proposedEstimate.reason}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-1 flex-shrink-0">
                <button
                  onClick={handleConfirmEstimate}
                  className="p-1.5 rounded-full bg-green-100 hover:bg-green-200 dark:bg-green-900/30 dark:hover:bg-green-800/50 text-green-700 dark:text-green-400 transition-colors"
                  title="Confirm & Create"
                >
                  <CheckCircleIcon className="w-4 h-4" />
                </button>
                <button
                  onClick={handleRejectEstimate}
                  className="p-1.5 rounded-full bg-red-100 hover:bg-red-200 dark:bg-red-900/30 dark:hover:bg-red-800/50 text-red-700 dark:text-red-400 transition-colors"
                  title="Reject"
                >
                  <XMarkIcon className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      
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
                  <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-headings:my-2 prose-pre:my-2 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:bg-black/10 dark:prose-code:bg-white/10">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {message.content}
                    </ReactMarkdown>
                  </div>
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
        </motion.div>
      )}
    </AnimatePresence>
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

