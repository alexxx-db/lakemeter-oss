import { useEffect, useState, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  PlusIcon, 
  ArrowDownTrayIcon,
  TrashIcon,
  DocumentDuplicateIcon,
  FolderIcon,
  ServerStackIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import { useStore } from '../store/useStore'
import { exportAllEstimatesToExcel } from '../api/client'
import { saveAs } from 'file-saver'

const cloudBadges: Record<string, { label: string; bg: string; text: string; border: string }> = {
  aws: { label: 'AWS', bg: 'rgba(245, 158, 11, 0.15)', text: '#f59e0b', border: 'rgba(245, 158, 11, 0.25)' },
  azure: { label: 'Azure', bg: 'rgba(14, 165, 233, 0.15)', text: '#0ea5e9', border: 'rgba(14, 165, 233, 0.25)' },
  gcp: { label: 'GCP', bg: 'rgba(244, 63, 94, 0.15)', text: '#f43f5e', border: 'rgba(244, 63, 94, 0.25)' }
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { estimates, isLoading, fetchEstimates, deleteEstimate, duplicateEstimate } = useStore()
  const [isExporting, setIsExporting] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [isRefreshing, setIsRefreshing] = useState(false)
  
  // Fetch estimates using SWR pattern (shows cached data immediately, refreshes in background)
  useEffect(() => {
    fetchEstimates() // Uses SWR - returns cached immediately, refreshes if stale
  }, [fetchEstimates])
  
  // Manual refresh handler
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true)
    await fetchEstimates(true) // Force refresh
    setIsRefreshing(false)
    toast.success('Refreshed')
  }, [fetchEstimates])
  
  const filteredEstimates = estimates.filter(e => 
    e.estimate_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    e.customer_name?.toLowerCase().includes(searchQuery.toLowerCase())
  )
  
  const handleDelete = async (e: React.MouseEvent, id: string, name: string) => {
    e.stopPropagation()
    if (window.confirm(`Delete "${name}"? This cannot be undone.`)) {
      try {
        await deleteEstimate(id)
        toast.success('Estimate deleted')
      } catch {
        toast.error('Failed to delete')
      }
    }
  }
  
  const handleDuplicate = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    try {
      const newEstimate = await duplicateEstimate(id)
      toast.success('Estimate duplicated')
      navigate(`/calculator/${newEstimate.estimate_id}`)
    } catch {
      toast.error('Failed to duplicate')
    }
  }
  
  const handleExportAll = async () => {
    setIsExporting(true)
    try {
      const blob = await exportAllEstimatesToExcel()
      saveAs(blob, `databricks_estimates_${new Date().toISOString().split('T')[0]}.xlsx`)
      toast.success('Exported successfully')
    } catch {
      toast.error('Export failed')
    } finally {
      setIsExporting(false)
    }
  }
  
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    
    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays} days ago`
    
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }
  
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>
            Pricing Estimates
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            {estimates.length} estimate{estimates.length !== 1 ? 's' : ''} • {estimates.reduce((acc, e) => acc + e.line_item_count, 0)} total workloads
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={isRefreshing || isLoading}
            className="btn btn-ghost p-2"
            title="Refresh estimates"
          >
            <ArrowPathIcon className={clsx("w-5 h-5", (isRefreshing || isLoading) && "animate-spin")} />
          </button>
          
          <button
            onClick={handleExportAll}
            disabled={isExporting || estimates.length === 0}
            className="btn btn-secondary"
          >
            <ArrowDownTrayIcon className="w-4 h-4" />
            <span className="hidden sm:inline">Export All</span>
          </button>
          
          <Link to="/calculator" className="btn btn-primary">
            <PlusIcon className="w-4 h-4" />
            New Estimate
          </Link>
        </div>
      </div>
      
      {/* Search */}
      <div className="relative mb-6">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--text-muted)' }} />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search estimates..."
          className="w-full pl-9 pr-4 py-2"
        />
      </div>
      
      {/* Estimates Grid */}
      {/* Only show skeleton when loading AND no cached data */}
      {isLoading && estimates.length === 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card p-5 animate-pulse">
              <div className="h-5 w-3/4 rounded mb-3" style={{ backgroundColor: 'var(--bg-tertiary)' }} />
              <div className="h-4 w-1/2 rounded mb-4" style={{ backgroundColor: 'var(--bg-tertiary)' }} />
              <div className="flex gap-2">
                <div className="h-5 w-12 rounded" style={{ backgroundColor: 'var(--bg-tertiary)' }} />
                <div className="h-5 w-16 rounded" style={{ backgroundColor: 'var(--bg-tertiary)' }} />
              </div>
            </div>
          ))}
        </div>
      ) : filteredEstimates.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="card p-12 text-center"
        >
          <div 
            className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4 border"
            style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-primary)' }}
          >
            <FolderIcon className="w-7 h-7" style={{ color: 'var(--text-muted)' }} />
          </div>
          <h3 className="text-lg font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
            {searchQuery ? 'No matches found' : 'No estimates yet'}
          </h3>
          <p className="text-sm mb-6 max-w-sm mx-auto" style={{ color: 'var(--text-muted)' }}>
            {searchQuery 
              ? 'Try adjusting your search terms' 
              : 'Create your first pricing estimate to get started'}
          </p>
          {!searchQuery && (
            <Link to="/calculator" className="btn btn-primary">
              <PlusIcon className="w-4 h-4" />
              Create Estimate
            </Link>
          )}
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredEstimates.map((estimate, index) => (
            <motion.div
              key={estimate.estimate_id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.03 }}
              onClick={() => navigate(`/calculator/${estimate.estimate_id}`)}
              className="card card-interactive p-5 group"
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-3">
                <h3 
                  className="font-medium truncate pr-2 group-hover:text-orange-500 transition-colors"
                  style={{ color: 'var(--text-primary)' }}
                >
                  {estimate.estimate_name}
                </h3>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={(e) => handleDuplicate(e, estimate.estimate_id)}
                    className="p-1.5 rounded-md transition-colors"
                    style={{ color: 'var(--text-muted)' }}
                    title="Duplicate"
                  >
                    <DocumentDuplicateIcon className="w-4 h-4" />
                  </button>
                  <button
                    onClick={(e) => handleDelete(e, estimate.estimate_id, estimate.estimate_name)}
                    className="p-1.5 rounded-md transition-colors hover:text-red-500"
                    style={{ color: 'var(--text-muted)' }}
                    title="Delete"
                  >
                    <TrashIcon className="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              {/* Customer */}
              {estimate.customer_name && (
                <p className="text-sm mb-3 truncate" style={{ color: 'var(--text-muted)' }}>
                  {estimate.customer_name}
                </p>
              )}
              
              {/* Badges */}
              <div className="flex flex-wrap items-center gap-2 mb-4">
                {estimate.cloud && cloudBadges[estimate.cloud] && (
                  <span 
                    className="badge border"
                    style={{
                      backgroundColor: cloudBadges[estimate.cloud].bg,
                      color: cloudBadges[estimate.cloud].text,
                      borderColor: cloudBadges[estimate.cloud].border
                    }}
                  >
                    {cloudBadges[estimate.cloud].label}
                  </span>
                )}
                <span className="badge badge-default">
                  {estimate.status || 'draft'}
                </span>
              </div>
              
              {/* Footer */}
              <div 
                className="flex items-center justify-between text-xs pt-3 border-t"
                style={{ borderColor: 'var(--border-primary)', color: 'var(--text-muted)' }}
              >
                <span className="flex items-center gap-1">
                  <ServerStackIcon className="w-3.5 h-3.5" />
                  {estimate.line_item_count} workload{estimate.line_item_count !== 1 ? 's' : ''}
                </span>
                <span>{formatDate(estimate.updated_at)}</span>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
