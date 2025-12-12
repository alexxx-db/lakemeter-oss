import { useState, useRef, useEffect } from 'react'
import clsx from 'clsx'
import { ChevronDownIcon, XMarkIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline'

interface Option {
  value: string
  label: string
}

interface SearchableSelectProps {
  options: Option[]
  value: string
  onChange: (value: string) => void
  onSearchChange?: (search: string) => void
  placeholder?: string
  searchPlaceholder?: string
  isLoading?: boolean
  disabled?: boolean
  required?: boolean
  className?: string
}

export default function SearchableSelect({
  options,
  value,
  onChange,
  onSearchChange,
  placeholder = 'Select...',
  searchPlaceholder = 'Search...',
  isLoading = false,
  disabled = false,
  required = false,
  className
}: SearchableSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [search, setSearch] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Find the selected option label
  const selectedOption = options.find(o => o.value === value)
  
  // Filter options based on search
  const filteredOptions = search
    ? options.filter(o => o.label.toLowerCase().includes(search.toLowerCase()))
    : options

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
        setSearch('')
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Notify parent of search changes (for API filtering)
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      onSearchChange?.(search)
    }, 300)
    return () => clearTimeout(timeoutId)
  }, [search, onSearchChange])

  const handleSelect = (optionValue: string) => {
    onChange(optionValue)
    setIsOpen(false)
    setSearch('')
  }

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation()
    onChange('')
    setSearch('')
  }

  return (
    <div ref={containerRef} className={clsx("relative", className)}>
      {/* Main button/display */}
      <div
        onClick={() => {
          if (!disabled) {
            setIsOpen(!isOpen)
            if (!isOpen) {
              setTimeout(() => inputRef.current?.focus(), 0)
            }
          }
        }}
        className={clsx(
          "w-full flex items-center gap-2 px-3 py-2 rounded-lg border text-sm cursor-pointer transition-colors",
          "bg-[var(--bg-secondary)] border-[var(--border-primary)]",
          "hover:border-[var(--border-secondary)]",
          isOpen && "border-orange-500 ring-1 ring-orange-500/30",
          !value && required && !isOpen && "border-orange-500/50 ring-1 ring-orange-500/30",
          disabled && "opacity-50 cursor-not-allowed"
        )}
      >
        <MagnifyingGlassIcon className="w-4 h-4 text-[var(--text-muted)] flex-shrink-0" />
        
        {isOpen ? (
          <input
            ref={inputRef}
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={searchPlaceholder}
            className="flex-1 bg-transparent border-none p-0 focus:ring-0 focus:outline-none text-[var(--text-primary)] placeholder-[var(--text-muted)]"
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span className={clsx(
            "flex-1 truncate",
            value ? "text-[var(--text-primary)]" : "text-[var(--text-muted)]"
          )}>
            {selectedOption?.label || placeholder}
          </span>
        )}
        
        {value && !isOpen && (
          <button
            onClick={handleClear}
            className="p-0.5 hover:bg-[var(--bg-tertiary)] rounded"
          >
            <XMarkIcon className="w-4 h-4 text-[var(--text-muted)]" />
          </button>
        )}
        
        <ChevronDownIcon className={clsx(
          "w-4 h-4 text-[var(--text-muted)] transition-transform flex-shrink-0",
          isOpen && "rotate-180"
        )} />
      </div>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg shadow-lg max-h-60 overflow-auto">
          {isLoading ? (
            <div className="px-3 py-2 text-sm text-[var(--text-muted)]">Loading...</div>
          ) : filteredOptions.length === 0 ? (
            <div className="px-3 py-2 text-sm text-[var(--text-muted)]">
              {search ? 'No results found' : 'No options available'}
            </div>
          ) : (
            <>
              <div className="px-3 py-1.5 text-xs text-[var(--text-muted)] border-b border-[var(--border-primary)]">
                {filteredOptions.length} result{filteredOptions.length !== 1 ? 's' : ''}
              </div>
              {filteredOptions.map((option) => (
                <div
                  key={option.value}
                  onClick={() => handleSelect(option.value)}
                  className={clsx(
                    "px-3 py-2 text-sm cursor-pointer transition-colors",
                    option.value === value
                      ? "bg-orange-500/10 text-orange-500"
                      : "text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]"
                  )}
                >
                  {option.label}
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  )
}

