import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  PlusIcon, 
  ArrowDownTrayIcon,
  TrashIcon,
  DocumentDuplicateIcon,
  FolderIcon,
  CloudIcon,
  MagnifyingGlassIcon,
  CalendarIcon
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

const statusColors: Record<string, { bg: string; text: string; border: string }> = {
  draft: { bg: 'var(--bg-tertiary)', text: 'var(--text-secondary)', border: 'var(--border-primary)' },
  active: { bg: 'rgba(16, 185, 129, 0.15)', text: '#10b981', border: 'rgba(16, 185, 129, 0.25)' },
  archived: { bg: 'var(--bg-tertiary)', text: 'var(--text-muted)', border: 'var(--border-primary)' }
}

export default function Estimates() {
  const navigate = useNavigate()
  const { estimates, isLoading, fetchEstimates, deleteEstimate, duplicateEstimate } = useStore()
  const [isExporting, setIsExporting] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  
  useEffect(() => {
    fetchEstimates()
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
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }
  
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Saved Estimates</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            {estimates.length} estimate{estimates.length !== 1 ? 's' : ''}
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={handleExportAll}
            disabled={isExporting || estimates.length === 0}
            className="btn btn-secondary"
          >
            <ArrowDownTrayIcon className="w-4 h-4" />
            Export All
          </button>
          
          <Link to="/calculator" className="btn btn-primary">
            <PlusIcon className="w-4 h-4" />
            New Estimate
          </Link>
        </div>
      </div>
      
      {/* Search */}
      <div className="relative mb-6">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: 'var(--text-muted)' }} />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search estimates..."
          className="w-full pl-10 pr-4"
        />
      </div>
      
      {/* Estimates List */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card p-5 animate-pulse">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl" style={{ backgroundColor: 'var(--bg-tertiary)' }} />
                <div className="flex-1">
                  <div className="h-5 w-48 rounded mb-2" style={{ backgroundColor: 'var(--bg-tertiary)' }} />
                  <div className="h-4 w-32 rounded" style={{ backgroundColor: 'var(--bg-tertiary)' }} />
                </div>
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
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
            <FolderIcon className="w-8 h-8" style={{ color: 'var(--text-muted)' }} />
          </div>
          <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
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
        <div className="space-y-3">
          {filteredEstimates.map((estimate, index) => {
            const status = statusColors[estimate.status || 'draft']
            return (
            <motion.div
              key={estimate.estimate_id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.03 }}
              onClick={() => navigate(`/calculator/${estimate.estimate_id}`)}
              className="card card-interactive p-5"
            >
              <div className="flex items-center gap-4">
                {/* Icon */}
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-orange-500/10 to-orange-400/10 flex items-center justify-center">
                  <CloudIcon className="w-6 h-6 text-orange-500" />
                </div>
                
                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <h3 className="font-semibold truncate" style={{ color: 'var(--text-primary)' }}>
                      {estimate.estimate_name}
                    </h3>
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
                    <span 
                      className="badge border"
                      style={{
                        backgroundColor: status.bg,
                        color: status.text,
                        borderColor: status.border
                      }}
                    >
                      {estimate.status || 'draft'}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-sm" style={{ color: 'var(--text-muted)' }}>
                    {estimate.customer_name && <span>{estimate.customer_name}</span>}
                    <span className="flex items-center gap-1">
                      <CloudIcon className="w-4 h-4" />
                      {estimate.line_item_count} workloads
                    </span>
                    <span className="flex items-center gap-1">
                      <CalendarIcon className="w-4 h-4" />
                      {formatDate(estimate.updated_at)}
                    </span>
                  </div>
                </div>
                
                {/* Actions */}
                <div className="flex items-center gap-1">
                  <button
                    onClick={(e) => handleDuplicate(e, estimate.estimate_id)}
                    className="p-2 rounded-lg hover:bg-[var(--bg-hover)]"
                    style={{ color: 'var(--text-muted)' }}
                    title="Duplicate"
                  >
                    <DocumentDuplicateIcon className="w-5 h-5" />
                  </button>
                  <button
                    onClick={(e) => handleDelete(e, estimate.estimate_id, estimate.estimate_name)}
                    className="p-2 rounded-lg hover:text-red-500 hover:bg-red-500/10"
                    style={{ color: 'var(--text-muted)' }}
                    title="Delete"
                  >
                    <TrashIcon className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}

