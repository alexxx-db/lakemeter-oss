import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  Squares2X2Icon, 
  PlusCircleIcon,
  SunIcon,
  MoonIcon,
  ComputerDesktopIcon,
  ChevronDownIcon,
  UserCircleIcon
} from '@heroicons/react/24/outline'
import clsx from 'clsx'
import { useState, useRef, useEffect } from 'react'
import { useTheme, Theme } from '../hooks/useTheme'
import { useStore } from '../store/useStore'
import { ChatPanel } from './ChatPanel'
import toast from 'react-hot-toast'

// Sparkles Icon for AI Assistant
function SparklesIcon({ className }: { className?: string }) {
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

const navigation = [
  { name: 'Estimates', href: '/', icon: Squares2X2Icon },
  { name: 'New Estimate', href: '/calculator', icon: PlusCircleIcon },
]

// Databricks logo SVG component
const DatabricksLogo = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 text-orange-500">
    <path d="M12 2L2 7v10l10 5 10-5V7L12 2zm0 2.18l6.9 3.45L12 11.08 5.1 7.63 12 4.18zM4 8.63l7 3.5v7.24l-7-3.5V8.63zm16 7.24l-7 3.5v-7.24l7-3.5v7.24z"/>
  </svg>
)

const themeOptions: { value: Theme; label: string; icon: typeof SunIcon }[] = [
  { value: 'light', label: 'Light', icon: SunIcon },
  { value: 'dark', label: 'Dark', icon: MoonIcon },
  { value: 'system', label: 'System', icon: ComputerDesktopIcon },
]

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { theme, setTheme } = useTheme()
  const [isOpen, setIsOpen] = useState(false)
  const [isChatOpen, setIsChatOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  
  const { 
    currentUser, 
    isAuthenticated, 
    authError, 
    fetchCurrentUser,
    currentEstimate,
    lineItems,
    workloadCosts,
    createEstimate,
    createLineItem,
    calculateAllWorkloadCosts
  } = useStore()
  
  // Determine chat mode based on current route
  const isEstimateDetailPage = location.pathname.startsWith('/calculator/') && location.pathname !== '/calculator'
  const chatMode = isEstimateDetailPage ? 'estimate_detail' : 'estimates_list'
  
  // Fetch current user on mount
  useEffect(() => {
    fetchCurrentUser()
  }, [fetchCurrentUser])
  
  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])
  
  const currentTheme = themeOptions.find(t => t.value === theme) || themeOptions[2]
  const CurrentIcon = currentTheme.icon
  
  // Show auth error screen if not authenticated
  if (authError) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-8" style={{ backgroundColor: 'var(--bg-primary)' }}>
        <div 
          className="max-w-md w-full p-8 rounded-xl border text-center"
          style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-primary)' }}
        >
          <div className="w-16 h-16 mx-auto mb-6 rounded-full flex items-center justify-center bg-orange-500/10">
            <DatabricksLogo />
          </div>
          <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
            Authentication Required
          </h1>
          <p className="mb-6" style={{ color: 'var(--text-secondary)' }}>
            {authError}
          </p>
          <div 
            className="p-4 rounded-lg text-sm text-left"
            style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-muted)' }}
          >
            <p className="font-medium mb-2" style={{ color: 'var(--text-primary)' }}>For local development:</p>
            <p className="mb-2">Set the <code className="px-1.5 py-0.5 rounded bg-black/20">LOCAL_DEV_EMAIL</code> environment variable:</p>
            <code className="block p-2 rounded bg-black/30 text-orange-400 text-xs">
              LOCAL_DEV_EMAIL=your.email@databricks.com
            </code>
          </div>
        </div>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen flex flex-col transition-colors duration-200" style={{ backgroundColor: 'var(--bg-primary)' }}>
      {/* Top Navigation */}
      <header 
        className="sticky top-0 z-50 backdrop-blur-xl border-b transition-colors"
        style={{ 
          backgroundColor: 'var(--bg-secondary)', 
          borderColor: 'var(--border-primary)' 
        }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2.5 group">
              <div 
                className="w-8 h-8 rounded-lg flex items-center justify-center border group-hover:border-orange-500/50 transition-colors"
                style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-primary)' }}
              >
                <DatabricksLogo />
              </div>
              <div>
                <span className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
                  Lakemeter
                </span>
                <span className="hidden sm:inline text-[10px] ml-2 uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                  Pricing Calculator
                </span>
              </div>
            </Link>
            
            {/* Navigation */}
            <div className="flex items-center gap-3">
              <nav className="flex items-center gap-1">
                {navigation.map((item) => {
                  const isActive = location.pathname === item.href || 
                    (item.href !== '/' && location.pathname.startsWith(item.href))
                  
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      className={clsx(
                        'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200',
                        isActive && 'border'
                      )}
                      style={isActive ? {
                        backgroundColor: 'rgba(255, 54, 33, 0.1)',
                        color: 'var(--databricks-red)',
                        borderColor: 'rgba(255, 54, 33, 0.2)'
                      } : {
                        color: 'var(--text-secondary)'
                      }}
                    >
                      <item.icon className="w-4 h-4" />
                      <span className="hidden sm:inline">{item.name}</span>
                    </Link>
                  )
                })}
              </nav>
              
              {/* User Info */}
              {isAuthenticated && currentUser && (
                <div 
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg border"
                  style={{ 
                    backgroundColor: 'var(--bg-tertiary)', 
                    borderColor: 'var(--border-primary)',
                    color: 'var(--text-secondary)'
                  }}
                >
                  <UserCircleIcon className="w-4 h-4" />
                  <span className="text-sm hidden md:inline max-w-[150px] truncate">
                    {currentUser.full_name || currentUser.email.split('@')[0]}
                  </span>
                </div>
              )}
              
              {/* Theme Dropdown */}
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setIsOpen(!isOpen)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-colors border border-transparent hover:border-current"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  <CurrentIcon className="w-4 h-4" />
                  <span className="text-sm hidden sm:inline">{currentTheme.label}</span>
                  <ChevronDownIcon className={clsx('w-3 h-3 transition-transform', isOpen && 'rotate-180')} />
                </button>
                
                {isOpen && (
                  <div 
                    className="absolute right-0 mt-1 w-36 rounded-lg shadow-lg py-1 z-50 border"
                    style={{ 
                      backgroundColor: 'var(--bg-secondary)', 
                      borderColor: 'var(--border-primary)' 
                    }}
                  >
                    {themeOptions.map((option) => {
                      const Icon = option.icon
                      const isSelected = theme === option.value
                      return (
                        <button
                          key={option.value}
                          onClick={() => {
                            setTheme(option.value)
                            setIsOpen(false)
                          }}
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors"
                          style={isSelected ? {
                            backgroundColor: 'rgba(255, 54, 33, 0.1)',
                            color: 'var(--databricks-red)'
                          } : {
                            color: 'var(--text-secondary)'
                          }}
                        >
                          <Icon className="w-4 h-4" />
                          <span>{option.label}</span>
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
              
              {/* AI Assistant Button */}
              <button
                onClick={() => setIsChatOpen(true)}
                className={clsx(
                  "flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 border",
                  isChatOpen 
                    ? "bg-gradient-to-r from-orange-500 to-amber-500 text-white border-transparent" 
                    : "hover:bg-gradient-to-r hover:from-orange-500/10 hover:to-amber-500/10"
                )}
                style={!isChatOpen ? { 
                  color: 'var(--text-secondary)',
                  borderColor: 'var(--border-primary)'
                } : undefined}
                title="AI Assistant"
              >
                <SparklesIcon className="w-4 h-4" />
                <span className="hidden sm:inline">AI</span>
              </button>
            </div>
          </div>
        </div>
      </header>
      
      {/* Main content */}
      <main className="flex-1">
        <motion.div
          key={location.pathname}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
        >
          <Outlet />
        </motion.div>
      </main>
      
      {/* Footer */}
      <footer className="border-t py-4 mt-auto" style={{ borderColor: 'var(--border-primary)' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-xs" style={{ color: 'var(--text-muted)' }}>
            <span className="text-orange-500">Databricks</span> Pricing Calculator • Powered by Lakebase
          </p>
        </div>
      </footer>
      
      {/* AI Chat Panel - Global */}
      <ChatPanel
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        currentEstimate={isEstimateDetailPage ? currentEstimate : undefined}
        currentWorkloads={isEstimateDetailPage ? lineItems : undefined}
        itemCosts={isEstimateDetailPage ? Object.fromEntries(
          Object.entries(workloadCosts).map(([id, response]) => [
            id,
            {
              total: response?.data?.total_cost?.cost_per_month || response?.data?.cost?.total_cost || 0,
              dbu: response?.data?.dbu_calculation?.dbu_cost_per_month || response?.data?.dbu_costs?.dbu_cost_per_month || 0,
              vm: response?.data?.vm_costs?.vm_cost_per_month || 0
            }
          ])
        ) : undefined}
        onEstimateCreated={(estimateId) => {
          navigate(`/calculator/${estimateId}`)
          setIsChatOpen(false)
        }}
        onEstimateConfirmed={async (estimateConfig) => {
          try {
            const newEstimate = await createEstimate({
              ...estimateConfig,
              owner_user_id: currentUser?.user_id
            })
            if (newEstimate?.estimate_id) {
              navigate(`/calculator/${newEstimate.estimate_id}`)
              setIsChatOpen(false)
            }
          } catch (err: any) {
            toast.error(err.message || 'Failed to create estimate')
          }
        }}
        onWorkloadConfirmed={async (workloadConfig) => {
          if (currentEstimate?.estimate_id) {
            try {
              await createLineItem({
                estimate_id: currentEstimate.estimate_id,
                ...workloadConfig
              })
              calculateAllWorkloadCosts(currentEstimate.estimate_id)
              toast.success(`Workload "${workloadConfig.workload_name}" added!`)
            } catch (err: any) {
              toast.error(err.message || 'Failed to add workload')
            }
          }
        }}
        mode={chatMode}
      />
    </div>
  )
}
