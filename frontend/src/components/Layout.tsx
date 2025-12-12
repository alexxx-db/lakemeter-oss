import { Link, Outlet, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  Squares2X2Icon, 
  PlusCircleIcon,
  SunIcon,
  MoonIcon,
  ComputerDesktopIcon,
  ChevronDownIcon
} from '@heroicons/react/24/outline'
import clsx from 'clsx'
import { useState, useRef, useEffect } from 'react'
import { useTheme, Theme } from '../hooks/useTheme'

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
  const { theme, setTheme } = useTheme()
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  
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
    </div>
  )
}
