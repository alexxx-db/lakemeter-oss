import { useEffect, useState, useCallback, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  PlusIcon, 
  ArrowDownTrayIcon,
  TrashIcon,
  DocumentDuplicateIcon,
  FolderIcon,
  CloudIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  ChevronDownIcon,
  CheckIcon,
  XMarkIcon,
  Squares2X2Icon,
  BuildingOfficeIcon
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import { useStore } from '../store/useStore'
import { exportAllEstimatesToExcel, exportEstimateToExcel } from '../api/client'
import { saveAs } from 'file-saver'

// ============================================================================
// Constants & Types
// ============================================================================

const cloudBadges: Record<string, { label: string; bg: string; text: string; border: string }> = {
  aws: { label: 'AWS', bg: 'rgba(245, 158, 11, 0.15)', text: '#f59e0b', border: 'rgba(245, 158, 11, 0.25)' },
  azure: { label: 'Azure', bg: 'rgba(14, 165, 233, 0.15)', text: '#0ea5e9', border: 'rgba(14, 165, 233, 0.25)' },
  gcp: { label: 'GCP', bg: 'rgba(244, 63, 94, 0.15)', text: '#f43f5e', border: 'rgba(244, 63, 94, 0.25)' }
}

type SortOption = 'updated' | 'name' | 'workloads'
type CloudFilter = 'all' | 'aws' | 'azure' | 'gcp'

// ============================================================================
// Helper Functions
// ============================================================================

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffSecs / 60)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)
  const diffWeeks = Math.floor(diffDays / 7)
  const diffMonths = Math.floor(diffDays / 30)
  
  if (diffSecs < 60) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  if (diffWeeks === 1) return '1 week ago'
  if (diffWeeks < 4) return `${diffWeeks} weeks ago`
  if (diffMonths === 1) return '1 month ago'
  if (diffMonths < 12) return `${diffMonths} months ago`
  
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

// ============================================================================
// Components
// ============================================================================

interface FilterTabsProps {
  cloudFilter: CloudFilter
  setCloudFilter: (cloud: CloudFilter) => void
  cloudCounts: { all: number; aws: number; azure: number; gcp: number }
}

function FilterTabs({ cloudFilter, setCloudFilter, cloudCounts }: FilterTabsProps) {
  return (
    <div className="flex flex-col sm:flex-row gap-4 mb-6">
      {/* Cloud Filter */}
      <div className="flex items-center gap-1 p-1 rounded-lg" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
        <button
          onClick={() => setCloudFilter('all')}
          className={clsx(
            'px-3 py-1.5 text-sm font-medium rounded-md transition-all',
            cloudFilter === 'all'
              ? 'bg-white shadow-sm'
              : 'hover:bg-white/50'
          )}
          style={{
            color: cloudFilter === 'all' ? 'var(--text-primary)' : 'var(--text-muted)',
            backgroundColor: cloudFilter === 'all' ? 'var(--bg-primary)' : 'transparent'
          }}
        >
          All Clouds
          <span className="ml-1.5 text-xs opacity-60">{cloudCounts.all}</span>
        </button>
        {(['aws', 'azure', 'gcp'] as CloudFilter[]).map((cloud) => (
          <button
            key={cloud}
            onClick={() => setCloudFilter(cloud)}
            className={clsx(
              'px-3 py-1.5 text-sm font-medium rounded-md transition-all',
              cloudFilter === cloud
                ? 'shadow-sm'
                : 'hover:bg-white/50'
            )}
            style={{
              color: cloudFilter === cloud ? cloudBadges[cloud].text : 'var(--text-muted)',
              backgroundColor: cloudFilter === cloud ? cloudBadges[cloud].bg : 'transparent'
            }}
          >
            {cloudBadges[cloud].label}
            <span className="ml-1.5 text-xs opacity-60">{cloudCounts[cloud]}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

interface SortDropdownProps {
  sortBy: SortOption
  setSortBy: (sort: SortOption) => void
}

function SortDropdown({ sortBy, setSortBy }: SortDropdownProps) {
  const [isOpen, setIsOpen] = useState(false)
  
  const options: { value: SortOption; label: string }[] = [
    { value: 'updated', label: 'Recently Modified' },
    { value: 'name', label: 'Name (A-Z)' },
    { value: 'workloads', label: 'Workload Count' }
  ]
  
  const selectedOption = options.find(o => o.value === sortBy)
  
  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg border transition-colors"
        style={{ 
          borderColor: 'var(--border-primary)',
          color: 'var(--text-secondary)',
          backgroundColor: 'var(--bg-primary)'
        }}
      >
        <span>Sort: {selectedOption?.label}</span>
        <ChevronDownIcon className={clsx('w-4 h-4 transition-transform', isOpen && 'rotate-180')} />
      </button>
      
      <AnimatePresence>
        {isOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.15 }}
              className="absolute right-0 top-full mt-1 z-20 min-w-[180px] rounded-lg border shadow-lg overflow-hidden"
              style={{ 
                borderColor: 'var(--border-primary)',
                backgroundColor: 'var(--bg-primary)'
              }}
            >
              {options.map((option) => (
                <button
                  key={option.value}
                  onClick={() => {
                    setSortBy(option.value)
                    setIsOpen(false)
                  }}
                  className={clsx(
                    'w-full px-3 py-2 text-sm text-left flex items-center justify-between transition-colors',
                    sortBy === option.value ? 'bg-blue-500/10' : 'hover:bg-[var(--bg-hover)]'
                  )}
                  style={{ color: sortBy === option.value ? '#3b82f6' : 'var(--text-primary)' }}
                >
                  {option.label}
                  {sortBy === option.value && <CheckIcon className="w-4 h-4" />}
                </button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}

// ============================================================================
// Main Component
// ============================================================================

export default function Estimates() {
  const navigate = useNavigate()
  const { estimates, isLoading, fetchEstimates, deleteEstimate, duplicateEstimate } = useStore()
  
  // UI State
  const [isExporting, setIsExporting] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [cloudFilter, setCloudFilter] = useState<CloudFilter>('all')
  const [sortBy, setSortBy] = useState<SortOption>('updated')
  const [accountFilter, setAccountFilter] = useState<string>('all')
  const [isAccountDropdownOpen, setIsAccountDropdownOpen] = useState(false)
  
  // Bulk Selection State
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [isBulkMode, setIsBulkMode] = useState(false)
  const [isBulkDeleting, setIsBulkDeleting] = useState(false)
  const [isBulkExporting, setIsBulkExporting] = useState(false)
  
  // Fetch estimates on mount
  useEffect(() => {
    fetchEstimates()
  }, [fetchEstimates])
  
  // Manual refresh
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true)
    await fetchEstimates(true)
    setIsRefreshing(false)
    toast.success('Refreshed')
  }, [fetchEstimates])
  
  // Calculate cloud counts for filter tabs
  const cloudCounts = useMemo(() => {
    const all = estimates.length
    const aws = estimates.filter(e => e.cloud?.toLowerCase() === 'aws').length
    const azure = estimates.filter(e => e.cloud?.toLowerCase() === 'azure').length
    const gcp = estimates.filter(e => e.cloud?.toLowerCase() === 'gcp').length
    return { all, aws, azure, gcp }
  }, [estimates])
  
  // Calculate totals for header
  const totals = useMemo(() => {
    const totalWorkloads = estimates.reduce((sum, e) => sum + (e.line_item_count || 0), 0)
    return {
      estimates: estimates.length,
      workloads: totalWorkloads
    }
  }, [estimates])
  
  // Get unique account names for filter
  const accountNames = useMemo(() => {
    const names = new Set<string>()
    estimates.forEach(e => {
      if (e.customer_name) {
        names.add(e.customer_name)
      }
    })
    return Array.from(names).sort()
  }, [estimates])
  
  // Count estimates per account
  const accountCounts = useMemo(() => {
    const counts: Record<string, number> = { all: estimates.length }
    estimates.forEach(e => {
      if (e.customer_name) {
        counts[e.customer_name] = (counts[e.customer_name] || 0) + 1
      }
    })
    return counts
  }, [estimates])
  
  // Filter and sort estimates
  const filteredEstimates = useMemo(() => {
    let result = [...estimates]
    
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      result = result.filter(e => 
        e.estimate_name.toLowerCase().includes(query) ||
        e.customer_name?.toLowerCase().includes(query)
      )
    }
    
    // Cloud filter
    if (cloudFilter !== 'all') {
      result = result.filter(e => e.cloud?.toLowerCase() === cloudFilter)
    }
    
    // Account filter
    if (accountFilter !== 'all') {
      result = result.filter(e => e.customer_name === accountFilter)
    }
    
    // Sort
    switch (sortBy) {
      case 'updated':
        result.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
        break
      case 'name':
        result.sort((a, b) => a.estimate_name.localeCompare(b.estimate_name))
        break
      case 'workloads':
        result.sort((a, b) => (b.line_item_count || 0) - (a.line_item_count || 0))
        break
    }
    
    return result
  }, [estimates, searchQuery, cloudFilter, sortBy, accountFilter])
  
  // Handlers
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
  
  // Bulk actions
  const toggleSelectAll = () => {
    if (selectedIds.size === filteredEstimates.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredEstimates.map(e => e.estimate_id)))
    }
  }
  
  const toggleSelect = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }
  
  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return
    
    if (!window.confirm(`Delete ${selectedIds.size} estimate(s)? This cannot be undone.`)) return
    
    setIsBulkDeleting(true)
    let successCount = 0
    let failCount = 0
    
    for (const id of selectedIds) {
      try {
        await deleteEstimate(id)
        successCount++
      } catch {
        failCount++
      }
    }
    
    setIsBulkDeleting(false)
    setSelectedIds(new Set())
    
    if (failCount === 0) {
      toast.success(`Deleted ${successCount} estimate(s)`)
    } else {
      toast.error(`Deleted ${successCount}, failed ${failCount}`)
    }
  }
  
  const handleBulkExport = async () => {
    if (selectedIds.size === 0) return
    
    setIsBulkExporting(true)
    let successCount = 0
    
    for (const id of selectedIds) {
      try {
        const estimate = estimates.find(e => e.estimate_id === id)
        if (estimate) {
          const blob = await exportEstimateToExcel(id)
          saveAs(blob, `${estimate.estimate_name.replace(/[^a-z0-9]/gi, '_')}_${new Date().toISOString().split('T')[0]}.xlsx`)
          successCount++
        }
      } catch {
        // Continue with next
      }
    }
    
    setIsBulkExporting(false)
    toast.success(`Exported ${successCount} estimate(s)`)
  }
  
  const exitBulkMode = () => {
    setIsBulkMode(false)
    setSelectedIds(new Set())
  }
  
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header with Summary */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Pricing Estimates</h1>
          <p className="text-sm mt-1 flex items-center gap-3" style={{ color: 'var(--text-muted)' }}>
            <span className="flex items-center gap-1">
              <FolderIcon className="w-4 h-4" />
              {totals.estimates} estimate{totals.estimates !== 1 ? 's' : ''}
            </span>
            <span className="flex items-center gap-1">
              <Squares2X2Icon className="w-4 h-4" />
              {totals.workloads} total workloads
            </span>
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="btn btn-ghost p-2"
            title="Refresh estimates"
          >
            <ArrowPathIcon className={clsx("w-5 h-5", isRefreshing && "animate-spin")} />
          </button>
          
          {!isBulkMode ? (
            <>
              <button
                onClick={() => setIsBulkMode(true)}
                disabled={estimates.length === 0}
                className="btn btn-ghost text-sm"
                title="Select multiple"
              >
                Select
              </button>
              
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
            </>
          ) : (
            <>
              <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
                {selectedIds.size} selected
              </span>
              
              <button
                onClick={handleBulkExport}
                disabled={selectedIds.size === 0 || isBulkExporting}
                className="btn btn-secondary text-sm"
              >
                <ArrowDownTrayIcon className="w-4 h-4" />
                {isBulkExporting ? 'Exporting...' : 'Export'}
              </button>
              
              <button
                onClick={handleBulkDelete}
                disabled={selectedIds.size === 0 || isBulkDeleting}
                className="btn text-sm"
                style={{ 
                  backgroundColor: 'rgba(239, 68, 68, 0.1)', 
                  color: '#ef4444',
                  borderColor: 'rgba(239, 68, 68, 0.2)'
                }}
              >
                <TrashIcon className="w-4 h-4" />
                {isBulkDeleting ? 'Deleting...' : 'Delete'}
              </button>
              
              <button
                onClick={exitBulkMode}
                className="btn btn-ghost p-2"
                title="Cancel selection"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </>
          )}
        </div>
      </div>
      
      {/* Filter Row: Cloud Tabs + Account Dropdown */}
      <div className="flex flex-col lg:flex-row lg:items-center gap-4 mb-6">
        {/* Cloud Filter Tabs */}
        <FilterTabs
          cloudFilter={cloudFilter}
          setCloudFilter={setCloudFilter}
          cloudCounts={cloudCounts}
        />
        
        {/* Account Filter Dropdown */}
        {accountNames.length > 0 && (
          <div className="relative">
            <button
              onClick={() => setIsAccountDropdownOpen(!isAccountDropdownOpen)}
              className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg border transition-colors min-w-[200px]"
              style={{ 
                borderColor: accountFilter !== 'all' ? '#f97316' : 'var(--border-primary)',
                color: accountFilter !== 'all' ? '#f97316' : 'var(--text-secondary)',
                backgroundColor: accountFilter !== 'all' ? 'rgba(249, 115, 22, 0.1)' : 'var(--bg-primary)'
              }}
            >
              <BuildingOfficeIcon className="w-4 h-4" />
              <span className="truncate flex-1 text-left">
                {accountFilter === 'all' ? 'All Accounts' : accountFilter}
              </span>
              <span className="text-xs opacity-60 ml-1">
                {accountFilter === 'all' ? accountNames.length : accountCounts[accountFilter] || 0}
              </span>
              <ChevronDownIcon className={clsx('w-4 h-4 transition-transform flex-shrink-0', isAccountDropdownOpen && 'rotate-180')} />
            </button>
            
            <AnimatePresence>
              {isAccountDropdownOpen && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setIsAccountDropdownOpen(false)} />
                  <motion.div
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.15 }}
                    className="absolute left-0 top-full mt-1 z-20 min-w-[250px] max-h-64 overflow-y-auto rounded-lg border shadow-lg"
                    style={{ 
                      borderColor: 'var(--border-primary)',
                      backgroundColor: 'var(--bg-primary)'
                    }}
                  >
                    <button
                      onClick={() => {
                        setAccountFilter('all')
                        setIsAccountDropdownOpen(false)
                      }}
                      className={clsx(
                        'w-full px-3 py-2 text-sm text-left flex items-center justify-between transition-colors',
                        accountFilter === 'all' ? 'bg-orange-500/10' : 'hover:bg-[var(--bg-hover)]'
                      )}
                      style={{ color: accountFilter === 'all' ? '#f97316' : 'var(--text-primary)' }}
                    >
                      <span>All Accounts</span>
                      <span className="text-xs opacity-60">{accountNames.length}</span>
                    </button>
                    <div className="border-t" style={{ borderColor: 'var(--border-primary)' }} />
                    {accountNames.map((name) => (
                      <button
                        key={name}
                        onClick={() => {
                          setAccountFilter(name)
                          setIsAccountDropdownOpen(false)
                        }}
                        className={clsx(
                          'w-full px-3 py-2 text-sm text-left flex items-center justify-between transition-colors',
                          accountFilter === name ? 'bg-orange-500/10' : 'hover:bg-[var(--bg-hover)]'
                        )}
                        style={{ color: accountFilter === name ? '#f97316' : 'var(--text-primary)' }}
                      >
                        <span className="truncate">{name}</span>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <span className="text-xs opacity-60">{accountCounts[name] || 0}</span>
                          {accountFilter === name && <CheckIcon className="w-4 h-4" />}
                        </div>
                      </button>
                    ))}
                  </motion.div>
                </>
              )}
            </AnimatePresence>
          </div>
        )}
      </div>
      
      {/* Search and Sort Row */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: 'var(--text-muted)' }} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by name or customer..."
            className="w-full pl-10 pr-4"
          />
        </div>
        
        <SortDropdown sortBy={sortBy} setSortBy={setSortBy} />
      </div>
      
      {/* Estimates Table */}
      {isLoading ? (
        <div className="card overflow-hidden">
          <div className="p-4 space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-4 animate-pulse">
                <div className="w-8 h-8 rounded-lg" style={{ backgroundColor: 'var(--bg-tertiary)' }} />
                <div className="flex-1">
                  <div className="h-4 w-48 rounded mb-2" style={{ backgroundColor: 'var(--bg-tertiary)' }} />
                  <div className="h-3 w-32 rounded" style={{ backgroundColor: 'var(--bg-tertiary)' }} />
                </div>
              </div>
            ))}
          </div>
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
            {searchQuery || cloudFilter !== 'all' || accountFilter !== 'all'
              ? 'No matches found' 
              : 'No estimates yet'}
          </h3>
          <p className="text-sm mb-6 max-w-sm mx-auto" style={{ color: 'var(--text-muted)' }}>
            {searchQuery || cloudFilter !== 'all' || accountFilter !== 'all'
              ? 'Try adjusting your filters' 
              : 'Create your first pricing estimate to get started'}
          </p>
          {!searchQuery && cloudFilter === 'all' && accountFilter === 'all' && (
            <Link to="/calculator" className="btn btn-primary">
              <PlusIcon className="w-4 h-4" />
              Create Estimate
            </Link>
          )}
        </motion.div>
      ) : (
        <div className="card overflow-hidden">
          {/* Table Header */}
          <div 
            className="hidden sm:grid sm:grid-cols-12 gap-4 px-4 py-3 text-xs font-medium uppercase tracking-wider border-b"
            style={{ 
              backgroundColor: 'var(--bg-tertiary)',
              color: 'var(--text-muted)',
              borderColor: 'var(--border-primary)'
            }}
          >
            {isBulkMode && (
              <div className="col-span-1 flex items-center">
                <button
                  onClick={toggleSelectAll}
                  className="flex items-center justify-center"
                >
                  <div 
                    className={clsx(
                      'w-4 h-4 rounded border-2 flex items-center justify-center transition-colors',
                      selectedIds.size === filteredEstimates.length && filteredEstimates.length > 0
                        ? 'bg-blue-500 border-blue-500' 
                        : 'border-gray-400'
                    )}
                  >
                    {selectedIds.size === filteredEstimates.length && filteredEstimates.length > 0 && (
                      <CheckIcon className="w-3 h-3 text-white" />
                    )}
                  </div>
                </button>
              </div>
            )}
            <div className={clsx(isBulkMode ? "col-span-4" : "col-span-5")}>Estimate</div>
            <div className="col-span-3">Account</div>
            <div className="col-span-1 text-center">Cloud</div>
            <div className="col-span-1 text-center">Workloads</div>
            <div className="col-span-1">Modified</div>
            <div className="col-span-1"></div>
          </div>
          
          {/* Table Body */}
          <div className="divide-y" style={{ borderColor: 'var(--border-primary)' }}>
            {filteredEstimates.map((estimate, index) => {
              const isSelected = selectedIds.has(estimate.estimate_id)
              
              return (
                <motion.div
                  key={estimate.estimate_id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: index * 0.015 }}
                  onClick={() => !isBulkMode && navigate(`/calculator/${estimate.estimate_id}`)}
                  className={clsx(
                    'grid grid-cols-12 gap-4 px-4 py-3 items-center transition-colors',
                    !isBulkMode && 'cursor-pointer hover:bg-[var(--bg-hover)]',
                    isSelected && 'bg-blue-500/5'
                  )}
                >
                  {/* Checkbox (bulk mode) */}
                  {isBulkMode && (
                    <div className="col-span-1 flex items-center">
                      <button
                        onClick={(e) => toggleSelect(estimate.estimate_id, e)}
                        className="flex items-center justify-center"
                      >
                        <div 
                          className={clsx(
                            'w-4 h-4 rounded border-2 flex items-center justify-center transition-colors',
                            isSelected 
                              ? 'bg-blue-500 border-blue-500' 
                              : 'border-gray-400'
                          )}
                        >
                          {isSelected && <CheckIcon className="w-3 h-3 text-white" />}
                        </div>
                      </button>
                    </div>
                  )}
                  
                  {/* Estimate Name */}
                  <div className={clsx("flex items-center gap-3", isBulkMode ? "col-span-4" : "col-span-5")}>
                    <div 
                      className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                      style={{ 
                        backgroundColor: estimate.cloud && cloudBadges[estimate.cloud] 
                          ? cloudBadges[estimate.cloud].bg 
                          : 'var(--bg-tertiary)'
                      }}
                    >
                      <CloudIcon 
                        className="w-4 h-4" 
                        style={{ 
                          color: estimate.cloud && cloudBadges[estimate.cloud] 
                            ? cloudBadges[estimate.cloud].text 
                            : 'var(--text-muted)'
                        }}
                      />
                    </div>
                    <div className="min-w-0">
                      <p className="font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                        {estimate.estimate_name}
                      </p>
                      {/* Mobile-only: show account on small screens */}
                      <p className="sm:hidden text-xs truncate" style={{ color: 'var(--text-muted)' }}>
                        {estimate.customer_name || '—'}
                      </p>
                    </div>
                  </div>
                  
                  {/* Account Name */}
                  <div className="hidden sm:block col-span-3">
                    <p className="text-sm truncate" style={{ color: 'var(--text-secondary)' }}>
                      {estimate.customer_name || '—'}
                    </p>
                  </div>
                  
                  {/* Cloud Badge */}
                  <div className="hidden sm:flex col-span-1 justify-center">
                    {estimate.cloud && cloudBadges[estimate.cloud] ? (
                      <span 
                        className="px-2 py-0.5 rounded text-xs font-medium"
                        style={{
                          backgroundColor: cloudBadges[estimate.cloud].bg,
                          color: cloudBadges[estimate.cloud].text
                        }}
                      >
                        {cloudBadges[estimate.cloud].label}
                      </span>
                    ) : (
                      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>—</span>
                    )}
                  </div>
                  
                  {/* Workload Count */}
                  <div className="hidden sm:flex col-span-1 justify-center">
                    <span 
                      className={clsx(
                        "px-2 py-0.5 rounded text-xs font-medium",
                        estimate.line_item_count > 0 ? "bg-emerald-500/10 text-emerald-600" : ""
                      )}
                      style={estimate.line_item_count === 0 ? { color: 'var(--text-muted)' } : {}}
                    >
                      {estimate.line_item_count}
                    </span>
                  </div>
                  
                  {/* Last Modified */}
                  <div className="hidden sm:block col-span-1">
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                      {formatRelativeTime(estimate.updated_at)}
                    </p>
                  </div>
                  
                  {/* Actions */}
                  <div className="col-span-1 flex items-center justify-end gap-0.5">
                    {!isBulkMode && (
                      <>
                        <button
                          onClick={(e) => handleDuplicate(e, estimate.estimate_id)}
                          className="p-1.5 rounded hover:bg-[var(--bg-hover)]"
                          style={{ color: 'var(--text-muted)' }}
                          title="Duplicate"
                        >
                          <DocumentDuplicateIcon className="w-4 h-4" />
                        </button>
                        <button
                          onClick={(e) => handleDelete(e, estimate.estimate_id, estimate.estimate_name)}
                          className="p-1.5 rounded hover:text-red-500 hover:bg-red-500/10"
                          style={{ color: 'var(--text-muted)' }}
                          title="Delete"
                        >
                          <TrashIcon className="w-4 h-4" />
                        </button>
                      </>
                    )}
                  </div>
                </motion.div>
              )
            })}
          </div>
          
          {/* Table Footer */}
          <div 
            className="px-4 py-2 text-xs border-t"
            style={{ 
              backgroundColor: 'var(--bg-tertiary)',
              color: 'var(--text-muted)',
              borderColor: 'var(--border-primary)'
            }}
          >
            Showing {filteredEstimates.length} of {estimates.length} estimates
          </div>
        </div>
      )}
      
    </div>
  )
}
