import React, { useEffect, useState, useMemo, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  PlusIcon,
  ArrowDownTrayIcon,
  ArrowLeftIcon,
  ArrowPathIcon,
  CheckIcon,
  TrashIcon,
  DocumentDuplicateIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  BoltIcon,
  CpuChipIcon,
  CurrencyDollarIcon,
  ServerStackIcon,
  ExclamationTriangleIcon,
  BuildingOfficeIcon,
  PlayCircleIcon,
  CircleStackIcon,
  ArrowsRightLeftIcon,
  MagnifyingGlassCircleIcon,
  SparklesIcon,
  ServerIcon,
  TableCellsIcon,
  Squares2X2Icon,
  ListBulletIcon
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import { useStore } from '../store/useStore'
import { 
  exportEstimateToExcel,
  fetchSalesforceAccounts,
  fetchSalesforceOpportunities,
  fetchSalesforceUseCases,
  type RegionResponse
} from '../api/client'
import { saveAs } from 'file-saver'
import WorkloadForm from '../components/WorkloadForm'
import SearchableSelect from '../components/SearchableSelect'
import type { LineItem, SalesforceAccount, SalesforceOpportunity, SalesforceUseCase } from '../types'
import {
  getInstanceDBURate as getBundleInstanceDBURate,
  getPhotonMultiplier as getBundlePhotonMultiplier,
  getDBUPrice as getBundleDBUPrice,
  getDBSQLRate as getBundleDBSQLRate,
  getDBSQLWarehouseConfig as getBundleDBSQLWarehouseConfig,
  getVectorSearchRate as getBundleVectorSearchRate,
  getModelServingRate as getBundleModelServingRate,
  getFMAPIDatabricksRate as getBundleFMAPIDatabricksRate,
  getFMAPIProprietaryRate as getBundleFMAPIProprietaryRate,
  getAvailableRegionsFromBundle
} from '../utils/pricingBundle'

// Cloud provider visual options
const CLOUD_PROVIDERS = [
  { id: 'aws', name: 'AWS', logo: '/aws.svg', bgClass: 'from-amber-600/20 to-amber-900/10' },
  { id: 'azure', name: 'Azure', logo: '/azure.svg', bgClass: 'from-sky-600/20 to-sky-900/10' },
  { id: 'gcp', name: 'GCP', logo: '/gcp.svg', bgClass: 'from-red-600/20 to-red-900/10' }
]

// Workload type visual config - icons, colors, and labels
const WORKLOAD_TYPE_CONFIG: Record<string, { 
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>, 
  color: string, 
  bgColor: string,
  label: string 
}> = {
  'JOBS': { 
    icon: PlayCircleIcon, 
    color: 'text-emerald-500', 
    bgColor: 'bg-emerald-500/10',
    label: 'Jobs'
  },
  'ALL_PURPOSE': { 
    icon: CpuChipIcon, 
    color: 'text-blue-500', 
    bgColor: 'bg-blue-500/10',
    label: 'AP'
  },
  'DLT': { 
    icon: ArrowsRightLeftIcon, 
    color: 'text-purple-500', 
    bgColor: 'bg-purple-500/10',
    label: 'SDP'
  },
  'DBSQL': { 
    icon: CircleStackIcon, 
    color: 'text-cyan-500', 
    bgColor: 'bg-cyan-500/10',
    label: 'DB SQL'
  },
  'VECTOR_SEARCH': { 
    icon: MagnifyingGlassCircleIcon, 
    color: 'text-rose-500', 
    bgColor: 'bg-rose-500/10',
    label: 'VS'
  },
  'MODEL_SERVING': { 
    icon: SparklesIcon, 
    color: 'text-amber-500', 
    bgColor: 'bg-amber-500/10',
    label: 'MS'
  },
  'FMAPI_DATABRICKS': { 
    icon: SparklesIcon, 
    color: 'text-orange-500', 
    bgColor: 'bg-orange-500/10',
    label: 'FMAPI DBX'
  },
  'FMAPI_PROPRIETARY': { 
    icon: SparklesIcon, 
    color: 'text-pink-500', 
    bgColor: 'bg-pink-500/10',
    label: 'FMAPI Prop'
  },
  'LAKEBASE': { 
    icon: ServerIcon, 
    color: 'text-indigo-500', 
    bgColor: 'bg-indigo-500/10',
    label: 'Lakebase'
  }
}

// Get workload type visual config with fallback
const getWorkloadTypeConfig = (workloadType: string | null | undefined) => {
  if (!workloadType) {
    return { 
      icon: CpuChipIcon, 
      color: 'text-orange-500', 
      bgColor: 'bg-orange-500/10',
      label: 'Workload'
    }
  }
  return WORKLOAD_TYPE_CONFIG[workloadType] || { 
    icon: CpuChipIcon, 
    color: 'text-orange-500', 
    bgColor: 'bg-orange-500/10',
    label: workloadType
  }
}

// DBU Pricing ($/DBU) - PREMIUM tier fallback values
// Note: Actual prices come from pricing bundle or API, these are fallbacks
const DBU_PRICING: Record<string, Record<string, number>> = {
  aws: {
    'JOBS_COMPUTE': 0.15,
    'JOBS_COMPUTE_(PHOTON)': 0.15,  // Photon doesn't change $/DBU, only consumption
    'JOBS_SERVERLESS_COMPUTE': 0.39,  // Serverless has higher $/DBU
    'ALL_PURPOSE_COMPUTE': 0.40,
    'ALL_PURPOSE_COMPUTE_(PHOTON)': 0.40,
    'ALL_PURPOSE_SERVERLESS_COMPUTE': 0.83,  // All-Purpose Serverless
    'DLT_CORE_COMPUTE': 0.20,
    'DLT_PRO_COMPUTE': 0.25,
    'DLT_ADVANCED_COMPUTE': 0.30,
    'DLT_CORE_COMPUTE_(PHOTON)': 0.25,
    'DELTA_LIVE_TABLES_SERVERLESS': 0.30,
    'SQL_COMPUTE': 0.22,
    'SQL_PRO_COMPUTE': 0.55,
    'SERVERLESS_SQL_COMPUTE': 0.70,
    'SERVERLESS_REAL_TIME_INFERENCE': 0.07,  // Vector Search, Model Serving, FMAPI Databricks
    'DATABASE_SERVERLESS_COMPUTE': 0.48  // Lakebase
  },
  azure: {
    'JOBS_COMPUTE': 0.15,
    'JOBS_COMPUTE_(PHOTON)': 0.15,
    'JOBS_SERVERLESS_COMPUTE': 0.39,
    'ALL_PURPOSE_COMPUTE': 0.40,
    'ALL_PURPOSE_COMPUTE_(PHOTON)': 0.40,
    'ALL_PURPOSE_SERVERLESS_COMPUTE': 0.83,
    'DLT_CORE_COMPUTE': 0.20,
    'DLT_PRO_COMPUTE': 0.25,
    'DLT_ADVANCED_COMPUTE': 0.30,
    'DLT_CORE_COMPUTE_(PHOTON)': 0.25,
    'DELTA_LIVE_TABLES_SERVERLESS': 0.30,
    'SQL_COMPUTE': 0.22,
    'SQL_PRO_COMPUTE': 0.55,
    'SERVERLESS_SQL_COMPUTE': 0.70,
    'SERVERLESS_REAL_TIME_INFERENCE': 0.07,  // Vector Search, Model Serving, FMAPI Databricks
    'DATABASE_SERVERLESS_COMPUTE': 0.48  // Lakebase
  },
  gcp: {
    'JOBS_COMPUTE': 0.15,
    'JOBS_COMPUTE_(PHOTON)': 0.15,
    'JOBS_SERVERLESS_COMPUTE': 0.39,
    'ALL_PURPOSE_COMPUTE': 0.40,
    'ALL_PURPOSE_COMPUTE_(PHOTON)': 0.40,
    'ALL_PURPOSE_SERVERLESS_COMPUTE': 0.83,
    'DLT_CORE_COMPUTE': 0.20,
    'DLT_PRO_COMPUTE': 0.25,
    'DLT_ADVANCED_COMPUTE': 0.30,
    'DLT_CORE_COMPUTE_(PHOTON)': 0.25,
    'DELTA_LIVE_TABLES_SERVERLESS': 0.30,
    'SQL_COMPUTE': 0.22,
    'SQL_PRO_COMPUTE': 0.55,
    'SERVERLESS_SQL_COMPUTE': 0.70,
    'SERVERLESS_REAL_TIME_INFERENCE': 0.07,  // Vector Search, Model Serving, FMAPI Databricks
    'DATABASE_SERVERLESS_COMPUTE': 0.48  // Lakebase
  }
}

// Note: Instance DBU rates are now fetched dynamically from instanceTypes
// The hardcoded INSTANCE_DBU_RATES has been replaced with lookups using instanceTypes.dbu_rate


// DBSQL warehouse DBU rates (keys must match database CHECK constraint: chk_dbsql_warehouse_size)
const DBSQL_DBU_RATES: Record<string, number> = {
  '2X-Small': 4, 'X-Small': 6, 'Small': 12, 'Medium': 24,
  'Large': 40, 'X-Large': 80, '2X-Large': 144, '3X-Large': 272, '4X-Large': 528
}

interface CostBreakdown {
  monthlyDBUs: number
  dbuCost: number
  vmCost: number
  totalCost: number
  // Optional fields for specific workload types
  unitsUsed?: number  // Vector Search units
  dbuPerHour?: number // DBU per hour for display
  dbuPrice?: number   // $/DBU rate for display
}

export default function Calculator() {
  const { id } = useParams()
  const navigate = useNavigate()
  const {
    currentEstimate,
    lineItems,
    workloadTypes,
    fetchEstimateWithLineItems,
    fetchReferenceData, // Still needed for manual refresh button
    clearReferenceCache,
    isLoadingReferenceData,
    isReferenceDataLoaded,
    regionsMap,
    getRegionsForCloud,
    createEstimate,
    updateEstimate,
    deleteLineItem,
    cloneLineItem,
    setSelectedCloud,
    setSelectedRegion,
    fetchVMCostForInstance,
    getVMPrice,
    // VM pricing map - subscribe to trigger re-render when prices are fetched
    vmPricingMap,
    // DBU Rates
    dbuRatesMap,
    fetchDBURates,
    // Instance types for DBU rate lookup
    instanceTypes,
    // Photon multipliers
    photonMultipliers,
    // DBSQL sizes for warehouse DBU rates
    dbsqlSizes,
    // Model Serving GPU types for DBU rates
    modelServingGPUTypes,
    // Vector Search modes for DBU rates
    vectorSearchModes,
    getVectorSearchRate,
    // FMAPI rates (cached lookups)
    getFMAPIDatabricksRate,
    getFMAPIProprietaryRate,
    // Pricing Bundle (for instant local calculations)
    pricingBundle,
    isPricingBundleLoaded,
    // NOTE: loadPricingBundle is now called in Layout.tsx at app startup
    // State management
    clearEstimateState
  } = useStore()
  
  const [isSaving, setIsSaving] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [showAddForm, setShowAddForm] = useState(false)
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  
  // Pending form edits for real-time cost updates
  const [pendingFormEdits, setPendingFormEdits] = useState<Record<string, Partial<LineItem>>>({})
  const [isLoadingEstimate, setIsLoadingEstimate] = useState(false)
  const [isLoadingLineItems, setIsLoadingLineItems] = useState(false)
  const [lineItemsLoaded, setLineItemsLoaded] = useState(false)
  // Track VM cost loading to show proper loading state instead of "jumping" prices
  const [isLoadingVMCosts, setIsLoadingVMCosts] = useState(false)
  
  // Salesforce data
  const [sfAccounts, setSfAccounts] = useState<SalesforceAccount[]>([])
  const [sfOpportunities, setSfOpportunities] = useState<SalesforceOpportunity[]>([])
  const [sfUseCases, setSfUseCases] = useState<SalesforceUseCase[]>([])
  const [sfAccountSearch, setSfAccountSearch] = useState('')
  const [sfOpportunitySearch, setSfOpportunitySearch] = useState('')
  const [sfUseCaseSearch, setSfUseCaseSearch] = useState('')
  const [isLoadingSfAccounts, setIsLoadingSfAccounts] = useState(false)
  const [isLoadingSfOpportunities, setIsLoadingSfOpportunities] = useState(false)
  const [isLoadingSfUseCases, setIsLoadingSfUseCases] = useState(false)
  
  // Regions data (fetched from API based on cloud)
  const [regions, setRegions] = useState<RegionResponse[]>([])
  const [isLoadingRegions, setIsLoadingRegions] = useState(false)
  
  // Form state - using correct column names
  const [formData, setFormData] = useState({
    estimate_name: '',
    customer_name: '',
    sfdc_account_id: '',  // Salesforce Account ID
    opportunity_id: '',  // Salesforce Opportunity ID
    uco_id: '',  // Salesforce Use Case ID
    cloud: 'aws',
    region: '',
    tier: ''  // No default - must be selected
  })
  
  // Configuration panel collapsed state
  const [isConfigCollapsed, setIsConfigCollapsed] = useState(false)
  
  // Cost summary panel collapsed state
  const [isCostSummaryCollapsed, setIsCostSummaryCollapsed] = useState(false)
  // Cost summary sticky (pinned) state
  const [isCostSummaryPinned, setIsCostSummaryPinned] = useState(true)
  // Cost summary expanded details state
  const [showCostDetails, setShowCostDetails] = useState(false)
  
  // Workloads view mode: 'cards' (default, compact), 'expanded', 'table'
  const [workloadsViewMode, setWorkloadsViewMode] = useState<'cards' | 'expanded' | 'table'>('cards')
  
  // Bulk selection for delete
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set())
  
  // Track changes
  const markAsChanged = useCallback(() => {
    setHasUnsavedChanges(true)
  }, [])
  
  // Browser beforeunload warning
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault()
        e.returnValue = ''
      }
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [hasUnsavedChanges])
  
  // NOTE: fetchReferenceData() and loadPricingBundle() are now called in Layout.tsx at app startup
  // This significantly speeds up Calculator page load
  
  // Salesforce lazy loading state - only fetch when user interacts with dropdown
  const [sfAccountsFetched, setSfAccountsFetched] = useState(false)
  
  // Lazy load Salesforce accounts - only fetch when user starts searching or dropdown is opened
  // This is a major performance optimization - Salesforce API calls are slow
  const fetchSfAccountsLazy = useCallback(async (search?: string) => {
    setIsLoadingSfAccounts(true)
    try {
      const accounts = await fetchSalesforceAccounts({ 
        search: search || undefined,
        limit: 1000 
      })
      setSfAccounts(accounts)
      setSfAccountsFetched(true)
    } catch (error) {
      console.error('Failed to fetch Salesforce accounts:', error)
    } finally {
      setIsLoadingSfAccounts(false)
    }
  }, [])
  
  // Fetch when search changes (debounced), but only if already fetched once or user is searching
  useEffect(() => {
    if (!sfAccountsFetched && !sfAccountSearch) {
      // Don't auto-fetch on mount - wait for user interaction
      return
    }
    
    const timeoutId = setTimeout(() => {
      fetchSfAccountsLazy(sfAccountSearch)
    }, 300) // 300ms debounce
    
    return () => clearTimeout(timeoutId)
  }, [sfAccountSearch, sfAccountsFetched, fetchSfAccountsLazy])
  
  // Fetch Salesforce opportunities when account is selected or search changes
  useEffect(() => {
    if (!formData.sfdc_account_id) {
      setSfOpportunities([])
      return
    }
    
    const timeoutId = setTimeout(async () => {
      setIsLoadingSfOpportunities(true)
      try {
        const opportunities = await fetchSalesforceOpportunities({ 
          account_id: formData.sfdc_account_id,
          limit: 1000 
        })
        setSfOpportunities(opportunities)
      } catch (error) {
        console.error('Failed to fetch Salesforce opportunities:', error)
      } finally {
        setIsLoadingSfOpportunities(false)
      }
    }, 300)
    
    return () => clearTimeout(timeoutId)
  }, [formData.sfdc_account_id, sfOpportunitySearch])
  
  // Fetch Salesforce use cases when account is selected or search changes
  useEffect(() => {
    if (!formData.sfdc_account_id) {
      setSfUseCases([])
      return
    }
    
    const timeoutId = setTimeout(async () => {
      setIsLoadingSfUseCases(true)
      try {
        const useCases = await fetchSalesforceUseCases({ 
          account_id: formData.sfdc_account_id,
          limit: 1000 
        })
        setSfUseCases(useCases)
      } catch (error) {
        console.error('Failed to fetch Salesforce use cases:', error)
      } finally {
        setIsLoadingSfUseCases(false)
      }
    }, 300)
    
    return () => clearTimeout(timeoutId)
  }, [formData.sfdc_account_id, sfUseCaseSearch])
  
  // NOTE: Removed bulk fetchVMPricing call (was loading 16+ MB of data)
  // VM pricing is now fetched on-demand via fetchVMCostForInstance for each selected instance type
  // This reduces data transfer from ~16 MB to ~1 KB per instance
  
  // Fetch VM costs for all unique instance types used in line items
  // This ensures VM pricing is available for cost calculations
  // NOTE: Also depends on lineItemsLoaded to ensure formData is populated from currentEstimate
  useEffect(() => {
    // Wait for estimate to be fully loaded (formData populated AND lineItems loaded)
    if (!formData.cloud || !formData.region || lineItems.length === 0 || !lineItemsLoaded) {
      return
    }
    
    // Collect all unique (instanceType, pricingTier) combinations from line items
    const fetchConfigs = new Set<string>()
    lineItems.forEach(item => {
      // Skip serverless workloads (no VM costs)
      if (item.serverless_enabled) return
      
      // Handle DBSQL Classic/Pro warehouses - get instance types from warehouse config
      if (item.workload_type === 'DBSQL' && item.dbsql_warehouse_type !== 'SERVERLESS') {
        const warehouseConfig = getBundleDBSQLWarehouseConfig(
          pricingBundle,
          formData.cloud,
          item.dbsql_warehouse_type || 'PRO',
          item.dbsql_warehouse_size || 'Small'
        )
        
        if (warehouseConfig) {
          // Fetch driver instance type VM cost
          const driverTier = item.dbsql_driver_pricing_tier || item.driver_pricing_tier || 'on_demand'
          const driverPayment = item.dbsql_driver_payment_option || item.driver_payment_option || 'NA'
          fetchConfigs.add(`${warehouseConfig.driver_instance_type}:${driverTier}:${driverPayment}`)
          
          // Fetch worker instance type VM cost
          const workerTier = item.dbsql_worker_pricing_tier || item.worker_pricing_tier || 'on_demand'
          const workerPayment = item.dbsql_worker_payment_option || item.worker_payment_option || 'NA'
          fetchConfigs.add(`${warehouseConfig.worker_instance_type}:${workerTier}:${workerPayment}`)
        }
        return // Don't process driver_node_type/worker_node_type for DBSQL
      }
      
      // Driver pricing (for non-DBSQL workloads)
      if (item.driver_node_type) {
        const driverTier = item.driver_pricing_tier || 'on_demand'
        const driverPayment = item.driver_payment_option || 'NA'
        fetchConfigs.add(`${item.driver_node_type}:${driverTier}:${driverPayment}`)
      }
      
      // Worker pricing (for non-DBSQL workloads)
      if (item.worker_node_type) {
        const workerTier = item.worker_pricing_tier || 'spot'
        const workerPayment = item.worker_payment_option || 'NA'
        fetchConfigs.add(`${item.worker_node_type}:${workerTier}:${workerPayment}`)
      }
    })
    
    // Fetch VM costs for each unique configuration (async, non-blocking)
    // Uses Promise.all to batch all fetches and trigger single re-render when all complete
    const fetchPromises = Array.from(fetchConfigs).map(config => {
      const [instanceType, pricingTier, paymentOption] = config.split(':')
      return fetchVMCostForInstance(formData.cloud, formData.region, instanceType, pricingTier, paymentOption)
    })
    
    // Track loading state so UI can show "calculating" instead of partial costs
    if (fetchPromises.length > 0) {
      setIsLoadingVMCosts(true)
      Promise.all(fetchPromises)
        .finally(() => setIsLoadingVMCosts(false))
    }
  }, [formData.cloud, formData.region, lineItems, lineItemsLoaded, fetchVMCostForInstance, pricingBundle])
  
  // Use cached regions from store (pre-loaded for all clouds)
  // Filter to only show regions that have actual Databricks control planes (i.e., regions in pricing bundle)
  useEffect(() => {
    if (!formData.cloud) return
    
    // Get regions from store cache (instant lookup)
    const cachedRegions = getRegionsForCloud(formData.cloud)
    
    if (cachedRegions.length > 0) {
      // Filter regions to only include those with control planes (in pricing bundle)
      // This ensures users can only select regions where Databricks is actually available
      const availableRegionsInBundle = isPricingBundleLoaded 
        ? getAvailableRegionsFromBundle(pricingBundle, formData.cloud)
        : []
      
      if (availableRegionsInBundle.length > 0) {
        // Filter cached regions to only those in the pricing bundle
        const filteredRegions = cachedRegions.filter(r => 
          availableRegionsInBundle.includes(r.region_code)
        )
        setRegions(filteredRegions)
      } else {
        // Bundle not loaded yet or no regions - show all cached regions as fallback
        setRegions(cachedRegions)
      }
      setIsLoadingRegions(false)
    } else if (!isReferenceDataLoaded) {
      // Still loading reference data
      setIsLoadingRegions(true)
    } else {
      // Reference data loaded but no regions for this cloud
      setRegions([])
      setIsLoadingRegions(false)
    }
  }, [formData.cloud, regionsMap, isReferenceDataLoaded, getRegionsForCloud, pricingBundle, isPricingBundleLoaded])
  
  useEffect(() => {
    const loadEstimateData = async () => {
      if (id) {
        setIsLoadingEstimate(true)
        setIsLoadingLineItems(true)
        setLineItemsLoaded(false)
        
        // Use combined endpoint for single round-trip (much faster)
        try {
          await fetchEstimateWithLineItems(id)
        } catch (error) {
          console.error('Error loading estimate data:', error)
        } finally {
          setIsLoadingEstimate(false)
          setIsLoadingLineItems(false)
          setLineItemsLoaded(true)
        }
      } else {
        // Creating new estimate - immediately clear any stale data from previous estimate
        clearEstimateState()
        setLineItemsLoaded(false)
      }
    }
    loadEstimateData()
  }, [id, fetchEstimateWithLineItems, clearEstimateState])
  
  // Default form values for new estimates
  const defaultEstimateFormData = {
    estimate_name: '',
    customer_name: '',
    sfdc_account_id: '',
    opportunity_id: '',
    uco_id: '',
    cloud: 'aws',
    region: '',
    tier: ''
  }

  useEffect(() => {
    if (currentEstimate && id) {
      // Editing existing estimate - load saved values
      setFormData({
        estimate_name: currentEstimate.estimate_name,
        customer_name: currentEstimate.customer_name || '',
        sfdc_account_id: currentEstimate.sfdc_account_id || '',
        opportunity_id: currentEstimate.opportunity_id || '',
        uco_id: currentEstimate.uco_id || '',
        // Convert to lowercase for UI matching (DB stores uppercase)
        cloud: (currentEstimate.cloud || 'aws').toLowerCase(),
        region: currentEstimate.region || '',
        tier: (currentEstimate.tier || '').toLowerCase()
      })
      if (currentEstimate.cloud) {
        setSelectedCloud(currentEstimate.cloud.toLowerCase())
      }
      if (currentEstimate.region) {
        setSelectedRegion(currentEstimate.region)
      }
    } else if (!id) {
      // Creating new estimate - reset to defaults
      setFormData(defaultEstimateFormData)
      setSelectedCloud('aws')
      setHasUnsavedChanges(false)
    }
  }, [currentEstimate, id, setSelectedCloud, setSelectedRegion])
  
  // Fetch DBU rates when cloud/region/tier changes
  useEffect(() => {
    if (formData.cloud && formData.region && formData.tier) {
      fetchDBURates(formData.cloud.toUpperCase(), formData.region, formData.tier.toUpperCase())
    }
  }, [formData.cloud, formData.region, formData.tier, fetchDBURates])
  
  // NOTE: API cost calculation is disabled - using LOCAL calculations only for instant feedback
  // All reference data (instanceTypes, dbuRatesMap, vectorSearchModes, fmapiRates, etc.) is pre-fetched on app load
  // Benefits: No network latency, instant updates as user types, works offline
  // The calculateItemCost function below uses only cached data
  
  // Check if required fields are set for workload creation
  const canAddWorkload = Boolean(formData.region && formData.tier)
  
  // Calculate cost for a single line item with full breakdown
  // Uses LOCAL calculation for instant feedback - no API dependency
  // All reference data (instanceTypes, dbuRatesMap, vectorSearchModes, etc.) is pre-fetched
  // Supports pending form edits for real-time cost preview during editing
  const calculateItemCost = (item: LineItem, pendingEdits?: Partial<LineItem>): CostBreakdown => {
    // Merge saved item with pending edits for real-time calculation
    const effectiveItem = pendingEdits ? { ...item, ...pendingEdits } : item
    
    // ========================================================================
    // LOCAL CALCULATION - Instant feedback using pre-fetched reference data
    // All pricing data is fetched on app load: instanceTypes, dbuRatesMap, 
    // photonMultipliers, vectorSearchModes, fmapiDatabricksRates, etc.
    // Benefits: No network latency, instant updates (<1ms), works offline
    // ========================================================================
    // No network calls, no loading states, immediate results as user types
    const cloud = formData.cloud || 'aws'
    const region = formData.region // No default - must be set
    // Try to use dynamic DBU rates first, fall back to hardcoded
    const pricing = Object.keys(dbuRatesMap).length > 0 ? dbuRatesMap : (DBU_PRICING[cloud] || DBU_PRICING.aws)
    const numWorkers = effectiveItem.num_workers || 0
    
    // If no region selected, return zero costs
    if (!region) {
      return { monthlyDBUs: 0, dbuCost: 0, vmCost: 0, totalCost: 0 }
    }
    
    // ========================================
    // Step 1: Calculate hours per month
    // Formula: runs_per_day * (avg_runtime_minutes / 60) * days_per_month
    // ========================================
    let hoursPerMonth = 0
    if (effectiveItem.workload_type !== 'FMAPI_DATABRICKS' && effectiveItem.workload_type !== 'FMAPI_PROPRIETARY') {
      if (effectiveItem.hours_per_month) {
        // Direct hours input
        hoursPerMonth = effectiveItem.hours_per_month
      } else if (effectiveItem.runs_per_day && effectiveItem.avg_runtime_minutes) {
        // Calculate from runs: runs_per_day * (avg_runtime_minutes / 60) * days_per_month
        hoursPerMonth = (effectiveItem.runs_per_day * (effectiveItem.avg_runtime_minutes / 60)) * (effectiveItem.days_per_month || 30)
      }
    }
    
    // ========================================
    // Step 2: Determine product_type_for_pricing (SKU)
    // Matches the SQL view's CASE logic
    // ========================================
    let productType = ''
    const dltEdition = effectiveItem.dlt_edition || 'CORE'
    
    switch (effectiveItem.workload_type) {
      case 'JOBS':
        if (effectiveItem.serverless_enabled) {
          productType = 'JOBS_SERVERLESS_COMPUTE'
        } else if (effectiveItem.photon_enabled) {
          productType = 'JOBS_COMPUTE_(PHOTON)'
        } else {
          productType = 'JOBS_COMPUTE'
        }
        break
      
      case 'ALL_PURPOSE':
        if (effectiveItem.serverless_enabled) {
          productType = 'ALL_PURPOSE_SERVERLESS_COMPUTE'
        } else if (effectiveItem.photon_enabled) {
          productType = 'ALL_PURPOSE_COMPUTE_(PHOTON)'
        } else {
          productType = 'ALL_PURPOSE_COMPUTE'
        }
        break
      
      case 'DLT':
        if (effectiveItem.serverless_enabled) {
          // DLT Serverless uses same rate as Jobs Serverless ($0.39)
          productType = 'JOBS_SERVERLESS_COMPUTE'
        } else {
          productType = `DLT_${dltEdition}_COMPUTE`
          if (effectiveItem.photon_enabled) {
            productType += '_(PHOTON)'
          }
        }
        break
      
      case 'DBSQL':
        const warehouseType = effectiveItem.dbsql_warehouse_type || 'SERVERLESS'
        if (warehouseType === 'SERVERLESS') {
          productType = 'SERVERLESS_SQL_COMPUTE'
        } else if (warehouseType === 'PRO') {
          productType = 'SQL_PRO_COMPUTE'
        } else {
          productType = 'SQL_COMPUTE'
        }
        break
      
      case 'VECTOR_SEARCH':
        // Vector Search uses SERVERLESS_REAL_TIME_INFERENCE pricing ($0.07/DBU)
        productType = 'SERVERLESS_REAL_TIME_INFERENCE'
        break
      
      case 'MODEL_SERVING':
        productType = 'SERVERLESS_REAL_TIME_INFERENCE'
        break
      
      case 'FMAPI_DATABRICKS':
        productType = 'SERVERLESS_REAL_TIME_INFERENCE'
        break
      
      case 'FMAPI_PROPRIETARY':
        // Proprietary models use their provider-specific pricing
        // Note: Provider names must match the bundle keys (ANTHROPIC, OPENAI, GEMINI - not GOOGLE)
        const fmapiProvider = (effectiveItem.fmapi_provider || 'openai').toLowerCase()
        const providerMapping: Record<string, string> = {
          'google': 'GEMINI',  // Google uses GEMINI_MODEL_SERVING in the bundle
          'anthropic': 'ANTHROPIC',
          'openai': 'OPENAI'
        }
        productType = `${providerMapping[fmapiProvider] || fmapiProvider.toUpperCase()}_MODEL_SERVING`
        break
      
      case 'LAKEBASE':
        productType = 'DATABASE_SERVERLESS_COMPUTE'
        break
      
      default:
        productType = 'JOBS_COMPUTE'
    }
    
    // Get DBU price for this product type
    // Try pricing bundle first (static data), then runtime dbuRatesMap, then hardcoded fallback
    let dbuPrice = 0.20
    if (isPricingBundleLoaded && formData.tier) {
      const bundlePrice = getBundleDBUPrice(pricingBundle, cloud, region, formData.tier, productType)
      if (bundlePrice > 0) {
        dbuPrice = bundlePrice
      } else {
        dbuPrice = pricing[productType] || 0.20
      }
    } else {
      dbuPrice = pricing[productType] || 0.20
    }
    
    // ========================================
    // Step 3: Calculate DBU per hour based on workload type
    // Uses fetched instanceTypes for accurate DBU rates
    // ========================================
    let dbuPerHour = 0
    let monthlyDBUs = 0
    let vmCost = 0
    let unitsUsed: number | undefined = undefined  // For Vector Search
    
    // Get instance DBU rates - try pricing bundle first, then fetched instanceTypes
    let driverDBURate = 0.5 // Fallback
    let workerDBURate = 0.5
    
    if (isPricingBundleLoaded && effectiveItem.driver_node_type) {
      const bundleDriverRate = getBundleInstanceDBURate(pricingBundle, cloud, effectiveItem.driver_node_type)
      if (bundleDriverRate > 0) driverDBURate = bundleDriverRate
    }
    if (!driverDBURate || driverDBURate === 0.5) {
      const driverInstance = instanceTypes.find(it => it.id === effectiveItem.driver_node_type || it.name === effectiveItem.driver_node_type)
      if (driverInstance?.dbu_rate) driverDBURate = driverInstance.dbu_rate
    }
    
    if (isPricingBundleLoaded && effectiveItem.worker_node_type) {
      const bundleWorkerRate = getBundleInstanceDBURate(pricingBundle, cloud, effectiveItem.worker_node_type)
      if (bundleWorkerRate > 0) workerDBURate = bundleWorkerRate
    }
    if (!workerDBURate || workerDBURate === 0.5) {
      const workerInstance = instanceTypes.find(it => it.id === effectiveItem.worker_node_type || it.name === effectiveItem.worker_node_type)
      if (workerInstance?.dbu_rate) workerDBURate = workerInstance.dbu_rate
    }
    
    // Get photon multiplier - try pricing bundle first, then fetched photonMultipliers
    // NOTE: For serverless workloads, photon is ALWAYS enabled (built-in)
    const getPhotonMultiplierValue = (): number => {
      // For classic workloads, only apply if photon is explicitly enabled
      if (!effectiveItem.serverless_enabled && !effectiveItem.photon_enabled) return 1.0
      
      // For SERVERLESS workloads, use the corresponding CLASSIC SKU type for photon lookup
      // The photon multiplier for serverless is the same as classic (photon is built-in)
      let skuTypeForLookup: string
      if (effectiveItem.serverless_enabled) {
        if (effectiveItem.workload_type === 'JOBS') {
          skuTypeForLookup = 'JOBS_COMPUTE'
        } else if (effectiveItem.workload_type === 'ALL_PURPOSE') {
          skuTypeForLookup = 'ALL_PURPOSE_COMPUTE'
        } else if (effectiveItem.workload_type === 'DLT') {
          // DLT serverless uses JOBS_SERVERLESS_COMPUTE for pricing, but photon from DLT_CORE_COMPUTE
          skuTypeForLookup = 'DLT_CORE_COMPUTE'
        } else {
          skuTypeForLookup = productType.replace('_(PHOTON)', '')
        }
      } else {
        // For classic, strip _(PHOTON) suffix but keep _COMPUTE suffix
        skuTypeForLookup = productType.replace('_(PHOTON)', '')
      }
      
      // Try pricing bundle first
      if (isPricingBundleLoaded) {
        const bundleMultiplier = getBundlePhotonMultiplier(pricingBundle, cloud, skuTypeForLookup)
        if (bundleMultiplier !== 2.0) return bundleMultiplier // 2.0 is the fallback in bundle helper
      }
      
      // Fall back to fetched photonMultipliers
      const multiplierEntry = photonMultipliers.find(pm => 
        pm.sku_type === skuTypeForLookup || 
        pm.sku_type?.toLowerCase() === skuTypeForLookup.toLowerCase() ||
        pm.sku_type?.toLowerCase().includes((item.workload_type || '').toLowerCase())
      )
      return multiplierEntry?.multiplier || 2.0 // Fallback to 2.0 (typical photon multiplier)
    }
    const photonMultiplier = getPhotonMultiplierValue()
    
    // Serverless mode multiplier (performance = 2x, standard = 1x)
    // Note: All-Purpose Serverless ONLY supports Performance mode (always 2x)
    // Jobs/DLT Serverless support both Standard (1x) and Performance (2x)
    const serverlessMultiplier = !effectiveItem.serverless_enabled ? 1 
      : (effectiveItem.workload_type === 'ALL_PURPOSE') ? 2  // All-Purpose Serverless is always Performance (2x)
      : (effectiveItem.serverless_mode === 'performance') ? 2 : 1
    
    // DLT multiplier (varies by edition for classic DLT)
    const getDLTMultiplier = () => {
      if (effectiveItem.workload_type !== 'DLT') return 1.0
      // DLT has edition-based pricing, the multiplier is baked into the DBU price
      return 1.0
    }
    const dltMultiplier = getDLTMultiplier()
    
    switch (effectiveItem.workload_type) {
      case 'ALL_PURPOSE':
      case 'JOBS':
        if (effectiveItem.serverless_enabled) {
          // Serverless: DBU/Hour = base_dbu_rate × photon_multiplier (always on) × serverless_multiplier
          // Photon is ALWAYS enabled in serverless (built-in)
          // serverlessMultiplier: standard=1x, performance=2x
          dbuPerHour = (driverDBURate + (workerDBURate * numWorkers)) * photonMultiplier * serverlessMultiplier
        } else {
          // Classic: DBU/Hour = (driver_dbu_rate + worker_dbu_rate × num_workers) × photon_multiplier
          dbuPerHour = (driverDBURate + (workerDBURate * numWorkers)) * photonMultiplier
          
          // VM costs for classic compute
          const driverPricingTier = effectiveItem.driver_pricing_tier || 'on_demand'
          const driverPaymentOption = effectiveItem.driver_payment_option || 'NA'
          const workerPricingTier = effectiveItem.worker_pricing_tier || 'spot'
          const workerPaymentOption = effectiveItem.worker_payment_option || 'NA'
          
          // Driver VM cost/hour
          const driverVMCostPerHour = getVMPrice(cloud, region, effectiveItem.driver_node_type || '', driverPricingTier, driverPaymentOption)
          
          // Worker VM cost/hour
          const workerVMCostPerHour = getVMPrice(cloud, region, effectiveItem.worker_node_type || '', workerPricingTier, workerPaymentOption)
          
          // VM Cost/Month = VM Cost/Hour × Hours/Month
          const totalVMCostPerHour = driverVMCostPerHour + (workerVMCostPerHour * numWorkers)
          vmCost = totalVMCostPerHour * hoursPerMonth
        }
        // DBU/Month = DBU/Hour × Hours/Month
        monthlyDBUs = dbuPerHour * hoursPerMonth
        break
      
      case 'DLT':
        if (effectiveItem.serverless_enabled) {
          // DLT Serverless: DBU/Hour = base_dbu_rate × photon (always on) × dlt_multiplier × serverless_multiplier
          // Photon is ALWAYS enabled in serverless (built-in)
          dbuPerHour = (driverDBURate + (workerDBURate * numWorkers)) * photonMultiplier * dltMultiplier * serverlessMultiplier
        } else {
          // DLT Classic: DBU/Hour = (driver_dbu + worker_dbu × workers) × photon_multiplier × dlt_multiplier
          dbuPerHour = (driverDBURate + (workerDBURate * numWorkers)) * photonMultiplier * dltMultiplier
          
          // VM costs for classic compute
          const driverPricingTier = effectiveItem.driver_pricing_tier || 'on_demand'
          const driverPaymentOption = effectiveItem.driver_payment_option || 'NA'
          const workerPricingTier = effectiveItem.worker_pricing_tier || 'spot'
          const workerPaymentOption = effectiveItem.worker_payment_option || 'NA'
          
          const driverVMCostPerHour = getVMPrice(cloud, region, effectiveItem.driver_node_type || '', driverPricingTier, driverPaymentOption)
          const workerVMCostPerHour = getVMPrice(cloud, region, effectiveItem.worker_node_type || '', workerPricingTier, workerPaymentOption)
          
          const totalVMCostPerHour = driverVMCostPerHour + (workerVMCostPerHour * numWorkers)
          vmCost = totalVMCostPerHour * hoursPerMonth
        }
        monthlyDBUs = dbuPerHour * hoursPerMonth
        break
      
      case 'DBSQL':
        // DBSQL: lookup DBU per hour from warehouse size
        // Try pricing bundle first, then fetched dbsqlSizes, then hardcoded fallback
        const dbsqlWarehouseType = effectiveItem.dbsql_warehouse_type || 'SERVERLESS'
        const warehouseSize = effectiveItem.dbsql_warehouse_size || 'Small'
        const numClusters = effectiveItem.dbsql_num_clusters || 1
        
        let warehouseDBUs = DBSQL_DBU_RATES[warehouseSize] || 12 // Default fallback
        
        // Try pricing bundle for DBSQL rate
        if (isPricingBundleLoaded) {
          const bundleDbsqlRate = getBundleDBSQLRate(pricingBundle, cloud, dbsqlWarehouseType, warehouseSize)
          if (bundleDbsqlRate && bundleDbsqlRate.dbu_per_hour > 0) {
            warehouseDBUs = bundleDbsqlRate.dbu_per_hour
          }
        }
        
        // Fall back to fetched dbsqlSizes
        if (!warehouseDBUs || warehouseDBUs === (DBSQL_DBU_RATES[warehouseSize] || 12)) {
          const dbsqlSize = dbsqlSizes.find(s => s.id === warehouseSize || s.name === warehouseSize)
          if (dbsqlSize?.dbu_per_hour) warehouseDBUs = dbsqlSize.dbu_per_hour
        }
        
        // DBU/Hour = warehouse_dbu_rate × num_clusters
        dbuPerHour = warehouseDBUs * numClusters
        monthlyDBUs = dbuPerHour * hoursPerMonth
        
        // VM costs only for CLASSIC and PRO (not SERVERLESS)
        if (dbsqlWarehouseType !== 'SERVERLESS') {
          // Try to get warehouse config from pricing bundle for VM details
          const warehouseConfig = isPricingBundleLoaded 
            ? getBundleDBSQLWarehouseConfig(pricingBundle, cloud, dbsqlWarehouseType, warehouseSize)
            : null
          
          if (warehouseConfig) {
            // Use config from bundle: driver + workers VM costs
            // DBSQL has separate driver and worker pricing tier selections
            const dbsqlDriverPricingTier = effectiveItem.dbsql_driver_pricing_tier || effectiveItem.driver_pricing_tier || 'on_demand'
            const dbsqlDriverPaymentOption = effectiveItem.dbsql_driver_payment_option || effectiveItem.driver_payment_option || 'NA'
            const dbsqlWorkerPricingTier = effectiveItem.dbsql_worker_pricing_tier || effectiveItem.worker_pricing_tier || 'spot'
            const dbsqlWorkerPaymentOption = effectiveItem.dbsql_worker_payment_option || effectiveItem.worker_payment_option || 'NA'
            
            const driverVMCost = getVMPrice(cloud, region, warehouseConfig.driver_instance_type, dbsqlDriverPricingTier, dbsqlDriverPaymentOption)
            const workerVMCost = getVMPrice(cloud, region, warehouseConfig.worker_instance_type, dbsqlWorkerPricingTier, dbsqlWorkerPaymentOption)
            
            // VM Cost/Hour = (driver_count × driver_vm + worker_count × worker_vm) × num_clusters
            const dbsqlVMCostPerHour = (
              (warehouseConfig.driver_count * driverVMCost) + 
              (warehouseConfig.worker_count * workerVMCost)
            ) * numClusters
            vmCost = dbsqlVMCostPerHour * hoursPerMonth
          } else if (effectiveItem.driver_node_type) {
            // Fallback: use driver/worker node types if specified
            const dbsqlDriverPricingTier = effectiveItem.dbsql_driver_pricing_tier || effectiveItem.driver_pricing_tier || 'on_demand'
            const dbsqlDriverPaymentOption = effectiveItem.dbsql_driver_payment_option || effectiveItem.driver_payment_option || 'NA'
            const dbsqlWorkerPricingTier = effectiveItem.dbsql_worker_pricing_tier || effectiveItem.worker_pricing_tier || 'spot'
            const dbsqlWorkerPaymentOption = effectiveItem.dbsql_worker_payment_option || effectiveItem.worker_payment_option || 'NA'
            
            const dbsqlDriverVMCost = getVMPrice(cloud, region, effectiveItem.driver_node_type, dbsqlDriverPricingTier, dbsqlDriverPaymentOption)
            const dbsqlWorkerVMCost = effectiveItem.worker_node_type 
              ? getVMPrice(cloud, region, effectiveItem.worker_node_type, dbsqlWorkerPricingTier, dbsqlWorkerPaymentOption)
              : 0
            const dbsqlNumWorkers = effectiveItem.num_workers || 0
            
            const dbsqlVMCostPerHour = (dbsqlDriverVMCost + (dbsqlWorkerVMCost * dbsqlNumWorkers)) * numClusters
            vmCost = dbsqlVMCostPerHour * hoursPerMonth
          }
        }
        // SERVERLESS: No VM costs
        break
      
      case 'VECTOR_SEARCH':
        // Vector Search: Units = CEILING(vector_capacity / divisor)
        // Standard: 2M vectors per unit, 4.00 DBU/hour per unit
        // Storage Optimized: 64M vectors per unit, 18.29 DBU/hour per unit
        const vectorMode = effectiveItem.vector_search_mode || 'standard'
        const vectorCapacity = effectiveItem.vector_capacity_millions || 1
        
        // Try pricing bundle first, then fetched data, then defaults
        let vectorDivisor = vectorMode === 'storage_optimized' ? 64000000 : 2000000  // Default divisors
        let vectorModeDBURate = vectorMode === 'storage_optimized' ? 18.29 : 4  // Default DBU rates
        
        if (isPricingBundleLoaded) {
          const bundleVectorRate = getBundleVectorSearchRate(pricingBundle, cloud, vectorMode)
          if (bundleVectorRate) {
            vectorDivisor = bundleVectorRate.input_divisor
            vectorModeDBURate = bundleVectorRate.dbu_rate
          }
        } else {
          // Fall back to fetched vectorSearchModes
          const vectorRateData = getVectorSearchRate(vectorMode)
          if (vectorRateData) {
            vectorDivisor = vectorRateData.input_divisor
            vectorModeDBURate = vectorRateData.dbu_per_hour
          }
        }
        
        // Convert vector capacity from millions to total vectors
        const vectorsTotal = vectorCapacity * 1000000
        const vectorUnitsUsed = Math.ceil(vectorsTotal / vectorDivisor)
        unitsUsed = vectorUnitsUsed  // Store for return
        
        // DBU/Hour = units_used × mode_dbu_rate
        dbuPerHour = vectorUnitsUsed * vectorModeDBURate
        monthlyDBUs = dbuPerHour * hoursPerMonth
        break
      
      case 'MODEL_SERVING':
        // Model Serving: DBU/Hour = gpu_type_dbu_rate
        const gpuType = effectiveItem.model_serving_gpu_type || 'cpu'
        
        // Try pricing bundle first, then fetched data, then default
        let gpuDBURate = 2 // Default fallback
        
        if (isPricingBundleLoaded) {
          const bundleGpuRate = getBundleModelServingRate(pricingBundle, cloud, gpuType)
          if (bundleGpuRate && bundleGpuRate.dbu_rate > 0) {
            gpuDBURate = bundleGpuRate.dbu_rate
          }
        }
        
        // Fall back to fetched modelServingGPUTypes
        if (gpuDBURate === 2) {
          const gpuTypeData = modelServingGPUTypes.find(g => g.id === gpuType || g.name === gpuType)
          if (gpuTypeData?.dbu_per_hour) gpuDBURate = gpuTypeData.dbu_per_hour
        }
        
        // Total Cost = DBU/Hour × hours_per_month × dbu_price
        dbuPerHour = gpuDBURate
        monthlyDBUs = dbuPerHour * hoursPerMonth
        break
      
      case 'LAKEBASE':
        // LAKEBASE (Managed PostgreSQL)
        // Formula: DBU/Hour = cu_size × num_nodes
        // Total Cost = DBU/Hour × hours_per_month × dbu_price
        const lakebaseCU = effectiveItem.lakebase_cu || 1
        const lakebaseNodes = effectiveItem.lakebase_ha_nodes || 1  // 1-3 nodes for HA
        
        dbuPerHour = lakebaseCU * lakebaseNodes
        monthlyDBUs = dbuPerHour * hoursPerMonth
        break
      
      case 'FMAPI_DATABRICKS':
        // Foundation Models (Databricks) - llama, gpt-oss, gemma, bge, gte, etc.
        const fmapiDbxQuantity = effectiveItem.fmapi_quantity || 0
        const fmapiDbxRateType = effectiveItem.fmapi_rate_type || 'input_token'
        const fmapiDbxIsProvisioned = ['provisioned_scaling', 'provisioned_entry'].includes(fmapiDbxRateType)
        
        // Try pricing bundle first
        let dbxDbuRate: number | null = null
        
        if (isPricingBundleLoaded && effectiveItem.fmapi_model) {
          const bundleDbxRate = getBundleFMAPIDatabricksRate(pricingBundle, cloud, effectiveItem.fmapi_model, fmapiDbxRateType)
          if (bundleDbxRate) {
            dbxDbuRate = bundleDbxRate.dbu_rate
          }
        }
        
        // Fall back to store's cached rate
        if (dbxDbuRate === null && effectiveItem.fmapi_model) {
          const dbxRateData = getFMAPIDatabricksRate(effectiveItem.fmapi_model, fmapiDbxRateType)
          if (dbxRateData) {
            if (fmapiDbxIsProvisioned) {
              dbxDbuRate = dbxRateData.dbu_per_hour || null
            } else {
              dbxDbuRate = dbxRateData.dbu_per_1M_tokens || null
            }
          }
        }
        
        // Apply defaults if still no rate found
        if (dbxDbuRate === null) {
          if (fmapiDbxIsProvisioned) {
            dbxDbuRate = fmapiDbxRateType === 'provisioned_scaling' ? 200 : 50
          } else {
            dbxDbuRate = fmapiDbxRateType === 'output_token' ? 3.0 : 1.0
          }
        }
        
        monthlyDBUs = fmapiDbxQuantity * dbxDbuRate
        break
      
      case 'FMAPI_PROPRIETARY':
        // Foundation Models (Proprietary) - OpenAI, Anthropic, Google
        const fmapiPropQuantity = effectiveItem.fmapi_quantity || 0
        const fmapiPropRateType = effectiveItem.fmapi_rate_type || 'input_token'
        const fmapiPropIsProvisioned = fmapiPropRateType === 'provisioned_scaling'
        
        // Try pricing bundle first
        let propDbuRate: number | null = null
        
        if (isPricingBundleLoaded && effectiveItem.fmapi_provider && effectiveItem.fmapi_model) {
          // Bundle key format: "cloud:provider:model:endpoint_type:context_length:rate_type"
          // Use defaults for endpoint_type and context_length if not specified
          const endpointType = effectiveItem.fmapi_endpoint_type || 'global'
          const contextLength = effectiveItem.fmapi_context_length || 'long'
          const bundlePropRate = getBundleFMAPIProprietaryRate(
            pricingBundle, cloud, effectiveItem.fmapi_provider, effectiveItem.fmapi_model, 
            endpointType, contextLength, fmapiPropRateType
          )
          if (bundlePropRate) {
            propDbuRate = bundlePropRate.dbu_rate
          }
        }
        
        // Fall back to store's cached rate
        if (propDbuRate === null && effectiveItem.fmapi_provider && effectiveItem.fmapi_model) {
          const propRateData = getFMAPIProprietaryRate(effectiveItem.fmapi_provider, effectiveItem.fmapi_model, fmapiPropRateType)
          if (propRateData) {
            if (fmapiPropIsProvisioned) {
              propDbuRate = propRateData.dbu_per_hour || null
            } else {
              propDbuRate = propRateData.dbu_per_1M_tokens || null
            }
          }
        }
        
        // Apply defaults if still no rate found
        if (propDbuRate === null) {
          if (fmapiPropIsProvisioned) {
            propDbuRate = 150
          } else {
            switch (fmapiPropRateType) {
              case 'output_token': propDbuRate = 6.0; break
              case 'cache_read': propDbuRate = 0.5; break
              case 'cache_write': propDbuRate = 1.0; break
              default: propDbuRate = 2.0 // input_token
            }
          }
        }
        
        monthlyDBUs = fmapiPropQuantity * propDbuRate
        break
      
      default:
        monthlyDBUs = 0
    }
    
    // ========================================
    // Step 4: Calculate final costs (with NaN guards)
    // ========================================
    const safeDbuPrice = isNaN(dbuPrice) || dbuPrice === undefined ? 0 : dbuPrice
    const safeMonthlyDBUs = isNaN(monthlyDBUs) || monthlyDBUs === undefined ? 0 : monthlyDBUs
    const safeVmCost = isNaN(vmCost) || vmCost === undefined ? 0 : vmCost
    
    const dbuCost = safeMonthlyDBUs * safeDbuPrice
    const totalCost = dbuCost + safeVmCost
    
    return { 
      monthlyDBUs: safeMonthlyDBUs, 
      dbuCost: isNaN(dbuCost) ? 0 : dbuCost, 
      vmCost: safeVmCost, 
      totalCost: isNaN(totalCost) ? 0 : totalCost,
      unitsUsed,  // For Vector Search
      dbuPerHour, // For display
      dbuPrice: safeDbuPrice  // $/DBU rate for display
    }
  }
  
  // Calculate total costs
  const totalCosts = useMemo(() => {
    let totalDBUs = 0
    let totalDBUCost = 0
    let totalVMCost = 0
    let totalCost = 0
    
    lineItems.forEach(item => {
      const costs = calculateItemCost(item)
      // Guard against NaN values propagating
      totalDBUs += isNaN(costs.monthlyDBUs) ? 0 : costs.monthlyDBUs
      totalDBUCost += isNaN(costs.dbuCost) ? 0 : costs.dbuCost
      totalVMCost += isNaN(costs.vmCost) ? 0 : costs.vmCost
      totalCost += isNaN(costs.totalCost) ? 0 : costs.totalCost
    })
    
    return { totalDBUs, totalDBUCost, totalVMCost, totalCost }
  }, [lineItems, formData.cloud, formData.region, formData.tier, workloadTypes, getVMPrice, vmPricingMap, instanceTypes, photonMultipliers, dbuRatesMap, dbsqlSizes, modelServingGPUTypes, vectorSearchModes, getVectorSearchRate, getFMAPIDatabricksRate, getFMAPIProprietaryRate, pricingBundle, isPricingBundleLoaded])
  
  const handleSave = async () => {
    if (!formData.estimate_name.trim()) {
      toast.error('Enter an estimate name')
      return
    }
    if (!formData.region) {
      toast.error('Select a region')
      return
    }
    if (!formData.tier) {
      toast.error('Select a Databricks tier')
      return
    }
    
    setIsSaving(true)
    try {
      // Convert cloud and tier to uppercase for database constraints
      const dataToSave = {
        ...formData,
        cloud: formData.cloud.toUpperCase(),
        tier: formData.tier.toUpperCase()
      }
      
      if (id && currentEstimate) {
        await updateEstimate(id, dataToSave)
        setHasUnsavedChanges(false)
        toast.success('All changes saved')
      } else {
        const newEstimate = await createEstimate(dataToSave)
        setHasUnsavedChanges(false)
        navigate(`/calculator/${newEstimate.estimate_id}`, { replace: true })
        toast.success('Estimate created')
      }
    } catch {
      toast.error('Failed to save')
    } finally {
      setIsSaving(false)
    }
  }
  
  const handleExport = async () => {
    if (!id) return
    
    setIsExporting(true)
    try {
      const blob = await exportEstimateToExcel(id)
      const filename = `${formData.estimate_name.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.xlsx`
      saveAs(blob, filename)
      toast.success('Exported to Excel')
    } catch {
      toast.error('Export failed')
    } finally {
      setIsExporting(false)
    }
  }
  
  const handleRefreshData = async () => {
    clearReferenceCache()
    toast.loading('Refreshing pricing data...', { id: 'refresh-data' })
    try {
      await fetchReferenceData(true) // Force refresh
      toast.success('Pricing data refreshed', { id: 'refresh-data' })
    } catch {
      toast.error('Failed to refresh data', { id: 'refresh-data' })
    }
  }
  
  const handleDeleteLineItem = async (item: LineItem) => {
    if (window.confirm(`Delete "${item.workload_name}"?`)) {
      try {
        await deleteLineItem(item.line_item_id)
        toast.success('Workload removed')
        markAsChanged()
      } catch {
        toast.error('Failed to delete')
      }
    }
  }
  
  // Bulk delete handler
  const handleBulkDelete = async () => {
    if (selectedItems.size === 0) return
    
    const itemNames = lineItems
      .filter(item => selectedItems.has(item.line_item_id))
      .map(item => item.workload_name)
      .join(', ')
    
    if (window.confirm(`Delete ${selectedItems.size} workload(s)?\n\n${itemNames}`)) {
      try {
        let deletedCount = 0
        for (const itemId of selectedItems) {
          await deleteLineItem(itemId)
          deletedCount++
        }
        toast.success(`${deletedCount} workload(s) deleted`)
        setSelectedItems(new Set())
        markAsChanged()
      } catch {
        toast.error('Failed to delete some workloads')
      }
    }
  }
  
  // Toggle item selection
  const toggleItemSelection = (itemId: string) => {
    setSelectedItems(prev => {
      const newSet = new Set(prev)
      if (newSet.has(itemId)) {
        newSet.delete(itemId)
      } else {
        newSet.add(itemId)
      }
      return newSet
    })
  }
  
  // Select/deselect all
  const toggleSelectAll = () => {
    if (selectedItems.size === lineItems.length) {
      setSelectedItems(new Set())
    } else {
      setSelectedItems(new Set(lineItems.map(item => item.line_item_id)))
    }
  }
  
  const handleCloneWorkload = async (e: React.MouseEvent, item: LineItem) => {
    e.stopPropagation()
    try {
      const cloned = await cloneLineItem(item.line_item_id)
      if (cloned) {
        toast.success(`Workload "${item.workload_name}" cloned`)
        markAsChanged()
      }
    } catch {
      toast.error('Failed to clone workload')
    }
  }
  
  const handleNavigateBack = () => {
    if (hasUnsavedChanges) {
      if (window.confirm('You have unsaved changes. Are you sure you want to leave?')) {
        navigate('/')
      }
    } else {
      navigate('/')
    }
  }
  
  const toggleExpand = (itemId: string) => {
    const newExpanded = new Set(expandedItems)
    if (newExpanded.has(itemId)) {
      newExpanded.delete(itemId)
    } else {
      newExpanded.add(itemId)
    }
    setExpandedItems(newExpanded)
  }
  
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount)
  }
  
  const formatNumber = (num: number, decimals: number = 2) => {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    }).format(num)
  }
  
  // Get usage summary for a workload
  const getUsageSummary = (item: LineItem) => {
    if (item.hours_per_month) {
      return `${item.hours_per_month}h/month`
    }
    if (item.runs_per_day) {
      return `${item.runs_per_day} runs/day × ${item.avg_runtime_minutes || 30}min`
    }
    return null
  }
  
  // Get workload-specific summary details
  const getWorkloadSummaryDetails = (item: LineItem): { label: string; value: string }[] => {
    const details: { label: string; value: string }[] = []
    
    // Add serverless mode for compute workloads when serverless is enabled
    if (['JOBS', 'ALL_PURPOSE', 'DLT'].includes(item.workload_type || '') && item.serverless_enabled) {
      details.push({ 
        label: 'Mode', 
        value: item.serverless_mode === 'performance' ? 'Performance' : 'Standard'
      })
    }
    
    switch (item.workload_type) {
      case 'VECTOR_SEARCH':
        if (item.vector_search_mode) {
          details.push({ 
            label: 'Mode', 
            value: item.vector_search_mode === 'storage_optimized' ? 'Storage Optimized' : 'Standard'
          })
        }
        if (item.vector_capacity_millions) {
          details.push({ label: 'Capacity', value: `${item.vector_capacity_millions}M vectors` })
        }
        break
        
      case 'MODEL_SERVING':
        if (item.model_serving_gpu_type) {
          const gpuLabels: Record<string, string> = {
            'cpu': 'CPU',
            'gpu_small_t4': 'GPU Small (T4)',
            'gpu_medium_a10g_1x': 'GPU Medium (A10G)',
            'gpu_large_a10g_4x': 'GPU Large (4x A10G)',
            'gpu_medium_a100_1x': 'GPU A100',
            'gpu_large_a100_2x': 'GPU A100 (2x)',
            'gpu_small': 'GPU Small',
            'gpu_medium': 'GPU Medium',
            'gpu_large': 'GPU Large'
          }
          details.push({ label: 'Endpoint', value: gpuLabels[item.model_serving_gpu_type] || item.model_serving_gpu_type })
        }
        break
        
      case 'LAKEBASE':
        if (item.lakebase_cu) {
          details.push({ label: 'CU', value: `${item.lakebase_cu}` })
        }
        if (item.lakebase_ha_nodes) {
          details.push({ label: 'Nodes', value: `${item.lakebase_ha_nodes}${item.lakebase_ha_nodes > 1 ? ' (HA)' : ''}` })
        }
        break
        
      case 'FMAPI_DATABRICKS':
        if (item.fmapi_model) {
          details.push({ label: 'Model', value: item.fmapi_model })
        }
        if (item.fmapi_rate_type) {
          const rateLabels: Record<string, string> = {
            'input_token': 'Input Tokens',
            'output_token': 'Output Tokens',
            'provisioned_scaling': 'Provisioned Scaling',
            'provisioned_entry': 'Provisioned Entry'
          }
          details.push({ label: 'Rate', value: rateLabels[item.fmapi_rate_type] || item.fmapi_rate_type })
        }
        if (item.fmapi_quantity) {
          const isProvisioned = ['provisioned_scaling', 'provisioned_entry'].includes(item.fmapi_rate_type || '')
          details.push({ 
            label: isProvisioned ? 'Hours' : 'Quantity', 
            value: isProvisioned ? `${item.fmapi_quantity}h/mo` : `${item.fmapi_quantity}M` 
          })
        }
        break
        
      case 'FMAPI_PROPRIETARY':
        if (item.fmapi_provider && item.fmapi_model) {
          details.push({ label: 'Model', value: `${item.fmapi_provider}/${item.fmapi_model}` })
        }
        if (item.fmapi_rate_type) {
          const rateLabels: Record<string, string> = {
            'input_token': 'Input',
            'output_token': 'Output',
            'cache_read': 'Cache Read',
            'cache_write': 'Cache Write'
          }
          details.push({ label: 'Rate', value: rateLabels[item.fmapi_rate_type] || item.fmapi_rate_type })
        }
        if (item.fmapi_quantity) {
          details.push({ label: 'Quantity', value: `${item.fmapi_quantity}M tokens` })
        }
        break
        
      case 'DLT':
        if (item.dlt_edition) {
          details.push({ label: 'Edition', value: item.dlt_edition })
        }
        break
        
      case 'DBSQL':
        if (item.dbsql_warehouse_type) {
          details.push({ label: 'Type', value: item.dbsql_warehouse_type })
        }
        if (item.dbsql_warehouse_size) {
          details.push({ label: 'Size', value: item.dbsql_warehouse_size })
        }
        if (item.dbsql_num_clusters && item.dbsql_num_clusters > 1) {
          details.push({ label: 'Clusters', value: `${item.dbsql_num_clusters}` })
        }
        break
    }
    
    return details
  }
  
  // Check if opportunity OR use case is selected (at least one required)
  const hasOpportunityOrUseCase = Boolean(formData.opportunity_id || formData.uco_id)
  
  // Validation: check if all required fields are filled
  const canCreateEstimate = formData.estimate_name.trim() && 
    formData.sfdc_account_id && 
    hasOpportunityOrUseCase &&
    formData.region && 
    formData.tier
  
  // Get missing fields for helpful message
  const getMissingFields = () => {
    const missing: string[] = []
    if (!formData.estimate_name.trim()) missing.push('Estimate Name')
    if (!formData.sfdc_account_id) missing.push('Salesforce Account')
    if (!hasOpportunityOrUseCase) missing.push('Opportunity or Use Case')
    if (!formData.region) missing.push('Region')
    if (!formData.tier) missing.push('Databricks Tier')
    return missing
  }
  
  // Show loading state when loading an existing estimate
  if (id && isLoadingEstimate && !currentEstimate) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => navigate('/estimates')}
            className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
          >
            <ArrowLeftIcon className="w-5 h-5" />
          </button>
          <div className="h-7 w-48 bg-[var(--bg-tertiary)] rounded animate-pulse"></div>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content Skeleton */}
          <div className="lg:col-span-2 space-y-6">
            {/* Config Card Skeleton */}
            <div className="card p-5">
              <div className="h-5 w-32 bg-[var(--bg-tertiary)] rounded animate-pulse mb-4"></div>
              <div className="grid grid-cols-3 gap-3 mb-6">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-16 bg-[var(--bg-tertiary)] rounded-xl animate-pulse"></div>
                ))}
              </div>
              <div className="space-y-4">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-10 bg-[var(--bg-tertiary)] rounded animate-pulse"></div>
                ))}
              </div>
            </div>
            
            {/* Workloads Skeleton */}
            <div className="space-y-4">
              <div className="h-6 w-28 bg-[var(--bg-tertiary)] rounded animate-pulse"></div>
              <div className="card p-8">
                <div className="flex flex-col items-center gap-4">
                  <div className="relative">
                    <div className="w-12 h-12 rounded-full border-4 border-[var(--border-primary)] border-t-orange-500 animate-spin"></div>
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-medium text-[var(--text-primary)]">Loading estimate...</p>
                    <p className="text-xs text-[var(--text-muted)] mt-1">Please wait while we fetch your data</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          {/* Summary Sidebar Skeleton */}
          <div className="lg:col-span-1">
            <div className="card p-5 space-y-4">
              <div className="h-5 w-20 bg-[var(--bg-tertiary)] rounded animate-pulse"></div>
              <div className="h-24 bg-[var(--bg-tertiary)] rounded animate-pulse"></div>
              <div className="h-12 bg-[var(--bg-tertiary)] rounded animate-pulse"></div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button
            onClick={handleNavigateBack}
            className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
          >
            <ArrowLeftIcon className="w-5 h-5" />
          </button>
          
          <div>
            {isLoadingEstimate && id ? (
              // Loading skeleton for estimate name
              <div className="space-y-1.5">
                <div className="h-7 w-48 bg-[var(--bg-tertiary)] rounded animate-pulse" />
                <div className="h-4 w-20 bg-[var(--bg-tertiary)] rounded animate-pulse" />
              </div>
            ) : (
              <>
                <input
                  type="text"
                  value={formData.estimate_name}
                  onChange={(e) => {
                    setFormData(prev => ({ ...prev, estimate_name: e.target.value }))
                    markAsChanged()
                  }}
                  placeholder="Untitled Estimate"
                  className="text-xl font-semibold bg-transparent border-none p-0 focus:ring-0 w-full min-w-[200px] text-[var(--text-primary)] placeholder-[var(--text-muted)]"
                />
                {currentEstimate && (
                  <p className="text-xs mt-0.5 text-[var(--text-muted)]">Version {currentEstimate.version}</p>
                )}
              </>
            )}
          </div>
          
          {hasUnsavedChanges && (
            <span className="flex items-center gap-1 text-xs text-orange-500 font-medium">
              <ExclamationTriangleIcon className="w-3.5 h-3.5" />
              Unsaved
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefreshData}
            disabled={isLoadingReferenceData}
            title="Refresh pricing data from server"
            className="btn btn-ghost text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          >
            <ArrowPathIcon className={clsx("w-4 h-4", isLoadingReferenceData && "animate-spin")} />
          </button>
          
          <button
            onClick={handleExport}
            disabled={isExporting || !id}
            className="btn btn-secondary"
          >
            <ArrowDownTrayIcon className="w-4 h-4" />
            <span className="hidden sm:inline">Excel</span>
          </button>
        </div>
      </div>
      
      <div className={clsx(
        "grid grid-cols-1 gap-6",
        isCostSummaryCollapsed ? "lg:grid-cols-1" : "lg:grid-cols-4"
      )}>
        {/* Main Content - Expands when sidebar is collapsed */}
        <div className={clsx(
          "space-y-6",
          isCostSummaryCollapsed ? "lg:col-span-1" : "lg:col-span-3"
        )}>
          {/* Configuration Section - Collapsible */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="card"
          >
            {/* Header - Always visible, clickable to expand/collapse */}
            <div 
              className="p-4 cursor-pointer hover:bg-[var(--bg-tertiary)]/50 transition-colors flex items-center justify-between"
              onClick={() => setIsConfigCollapsed(!isConfigCollapsed)}
            >
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 bg-orange-500/10">
                  <CpuChipIcon className="w-5 h-5 text-orange-500" />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="font-semibold text-[var(--text-primary)]">Configuration</h3>
                  <p className="text-xs text-[var(--text-muted)] truncate">
                    {formData.cloud.toUpperCase()} • {formData.region || 'No region'} • {formData.tier ? formData.tier.charAt(0).toUpperCase() + formData.tier.slice(1) : 'No tier'}
                    {formData.customer_name && ` • ${formData.customer_name}`}
                  </p>
                </div>
              </div>
              <button className="p-1 rounded hover:bg-[var(--bg-tertiary)] transition-colors flex-shrink-0 ml-2">
                {isConfigCollapsed ? (
                  <ChevronDownIcon className="w-5 h-5 text-[var(--text-muted)]" />
                ) : (
                  <ChevronUpIcon className="w-5 h-5 text-[var(--text-muted)]" />
                )}
              </button>
            </div>
            
            {/* Collapsible content */}
            {!isConfigCollapsed && (
              <div className="px-4 pb-4 space-y-5 border-t border-[var(--border-primary)]">
                {/* Cloud Selection + Region + Tier */}
                <div className="pt-4 space-y-4">
                  <div>
                    <label className="block text-xs font-medium mb-2 text-[var(--text-secondary)]">Cloud Provider</label>
                    {isLoadingEstimate && id ? (
                      <div className="grid grid-cols-3 gap-3">
                        {[1, 2, 3].map(i => (
                          <div
                            key={i}
                            className="p-4 rounded-xl border-2 border-dashed border-[var(--border-secondary)]"
                          >
                            <div className="h-6 w-16 mx-auto bg-[var(--bg-tertiary)] rounded animate-pulse" />
                          </div>
                        ))}
                      </div>
                    ) : (
                      <>
                        {lineItems.length > 0 && (
                          <div className="mb-2 text-xs text-amber-500 flex items-center gap-1">
                            <ExclamationTriangleIcon className="w-3.5 h-3.5" />
                            Cloud provider locked. Remove all workloads to change.
                          </div>
                        )}
                        <div className="grid grid-cols-3 gap-3">
                          {CLOUD_PROVIDERS.map(cloud => {
                            const isLocked = lineItems.length > 0 && formData.cloud !== cloud.id
                            return (
                              <button
                                key={cloud.id}
                                disabled={isLocked}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  if (isLocked) return
                                  setFormData(prev => ({ 
                                    ...prev, 
                                    cloud: cloud.id, 
                                    region: '',
                                    tier: (cloud.id === 'azure' && prev.tier === 'enterprise') ? '' : prev.tier
                                  }))
                                  setSelectedCloud(cloud.id)
                                  markAsChanged()
                                }}
                                className={clsx(
                                  'relative p-4 rounded-xl border-2 transition-all text-center',
                                  formData.cloud === cloud.id
                                    ? 'border-orange-500 bg-orange-500/10'
                                    : 'border-dashed border-[var(--border-secondary)]',
                                  isLocked
                                    ? 'opacity-40 cursor-not-allowed'
                                    : formData.cloud !== cloud.id && 'hover:border-orange-500/50 hover:bg-orange-500/5'
                                )}
                                title={isLocked ? 'Remove all workloads to change cloud provider' : undefined}
                              >
                                <div className={clsx(
                                  'text-lg font-semibold',
                                  formData.cloud === cloud.id ? 'text-orange-500' : 'text-[var(--text-primary)]'
                                )}>
                                  {cloud.name}
                                </div>
                                {formData.cloud === cloud.id && (
                                  <div className="absolute top-2 right-2">
                                    <CheckIcon className="w-4 h-4 text-orange-500" />
                                  </div>
                                )}
                              </button>
                            )
                          })}
                        </div>
                      </>
                    )}
                  </div>
                  
                  {/* Region and Tier - underneath Cloud Provider */}
                  {isLoadingEstimate && id ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <div className="h-4 w-16 bg-[var(--bg-tertiary)] rounded animate-pulse mb-1.5" />
                        <div className="h-10 w-full bg-[var(--bg-tertiary)] rounded animate-pulse" />
                      </div>
                      <div>
                        <div className="h-4 w-24 bg-[var(--bg-tertiary)] rounded animate-pulse mb-1.5" />
                        <div className="h-10 w-full bg-[var(--bg-tertiary)] rounded animate-pulse" />
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4" onClick={(e) => e.stopPropagation()}>
                      <div>
                        <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">
                          Region <span className="text-red-500">*</span>
                        </label>
                        <select
                          value={formData.region}
                          onChange={(e) => {
                            setFormData(prev => ({ ...prev, region: e.target.value }))
                            setSelectedRegion(e.target.value)
                            markAsChanged()
                          }}
                          className={clsx(
                            "w-full text-sm",
                            !formData.region && "border-orange-500/50 ring-1 ring-orange-500/30"
                          )}
                        >
                          <option value="">{isLoadingRegions ? 'Loading regions...' : 'Select region'}</option>
                          {regions.map(region => (
                            <option key={region.region_code} value={region.region_code}>
                              {region.region_code} ({region.sku_region})
                            </option>
                          ))}
                        </select>
                      </div>
                      
                      <div>
                        <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">
                          Databricks Tier <span className="text-red-500">*</span>
                        </label>
                        <select
                          value={formData.tier}
                          onChange={(e) => {
                            setFormData(prev => ({ ...prev, tier: e.target.value }))
                            markAsChanged()
                          }}
                          className={clsx(
                            "w-full text-sm",
                            !formData.tier && "border-orange-500/50 ring-1 ring-orange-500/30"
                          )}
                        >
                          <option value="">Select tier</option>
                          <option value="premium">Premium</option>
                          {formData.cloud !== 'azure' && (
                            <option value="enterprise">Enterprise</option>
                          )}
                        </select>
                      </div>
                    </div>
                  )}
                </div>
                
                {/* Salesforce Selection */}
                <div className="border-t border-[var(--border-primary)] pt-5">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-4 flex items-center gap-2">
                    <BuildingOfficeIcon className="w-4 h-4" />
                    Salesforce Context
                  </h4>
                  
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4" onClick={(e) => e.stopPropagation()}>
                    {/* Account Selection */}
                    <div>
                      <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">
                        Salesforce Account <span className="text-red-500">*</span>
                      </label>
                      <SearchableSelect
                        options={(() => {
                          if (isLoadingSfAccounts && sfAccounts.length === 0) return []
                          const searchOptions = sfAccounts.map(a => ({
                            value: a.salesforce_account_id,
                            label: a.salesforce_account_name || a.salesforce_account_id
                          }))
                          if (formData.sfdc_account_id && formData.customer_name) {
                            const existsInSearch = sfAccounts.some(a => a.salesforce_account_id === formData.sfdc_account_id)
                            if (!existsInSearch) {
                              return [{ value: formData.sfdc_account_id, label: formData.customer_name }, ...searchOptions]
                            }
                          }
                          return searchOptions
                        })()}
                        value={formData.sfdc_account_id}
                        onChange={(value) => {
                          const selectedAccount = sfAccounts.find(a => a.salesforce_account_id === value)
                          setFormData(prev => ({ 
                            ...prev, 
                            sfdc_account_id: value,
                            customer_name: selectedAccount?.salesforce_account_name || prev.customer_name,
                            opportunity_id: '',
                            uco_id: ''
                          }))
                          setSfOpportunitySearch('')
                          setSfUseCaseSearch('')
                          markAsChanged()
                        }}
                        onSearchChange={setSfAccountSearch}
                        onOpen={() => {
                          // Lazy load Salesforce accounts when dropdown opens (first time only)
                          if (!sfAccountsFetched && !isLoadingSfAccounts) {
                            fetchSfAccountsLazy()
                          }
                        }}
                        placeholder={isLoadingSfAccounts ? "Loading accounts..." : "Select account..."}
                        searchPlaceholder="Search accounts..."
                        isLoading={isLoadingSfAccounts}
                        required
                      />
                    </div>
                    
                    {/* Opportunity Selection */}
                    <div>
                      <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">
                        Opportunity
                        {!formData.sfdc_account_id && (
                          <span className="text-[var(--text-muted)] text-[10px] ml-1">(select account first)</span>
                        )}
                      </label>
                      <SearchableSelect
                        options={sfOpportunities.map(o => ({
                          value: o.id,
                          label: o.name || o.id
                        }))}
                        value={formData.opportunity_id}
                        onChange={(value) => {
                          setFormData(prev => ({ ...prev, opportunity_id: value }))
                          markAsChanged()
                        }}
                        onSearchChange={setSfOpportunitySearch}
                        placeholder={!formData.sfdc_account_id ? "Select account first" : isLoadingSfOpportunities ? "Loading opportunities..." : "Select opportunity..."}
                        searchPlaceholder="Search opportunities..."
                        isLoading={isLoadingSfOpportunities}
                        disabled={!formData.sfdc_account_id}
                      />
                    </div>
                    
                    {/* Use Case Selection */}
                    <div>
                      <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">
                        Use Case
                        {!formData.sfdc_account_id && (
                          <span className="text-[var(--text-muted)] text-[10px] ml-1">(select account first)</span>
                        )}
                      </label>
                      <SearchableSelect
                        options={sfUseCases.map(uc => ({
                          value: uc.salesforce_use_case_id,
                          label: uc.salesforce_use_case_name || uc.salesforce_use_case_id
                        }))}
                        value={formData.uco_id}
                        onChange={(value) => {
                          setFormData(prev => ({ ...prev, uco_id: value }))
                          markAsChanged()
                        }}
                        onSearchChange={setSfUseCaseSearch}
                        placeholder={!formData.sfdc_account_id ? "Select account first" : isLoadingSfUseCases ? "Loading use cases..." : "Select use case..."}
                        searchPlaceholder="Search use cases..."
                        isLoading={isLoadingSfUseCases}
                        disabled={!formData.sfdc_account_id}
                      />
                    </div>
                  </div>
                </div>
                
                {/* Save Button */}
                <div className="border-t border-[var(--border-primary)] pt-4 flex items-center justify-between">
                  <div className="text-xs text-[var(--text-muted)]">
                    {hasUnsavedChanges ? (
                      <span className="text-amber-500 flex items-center gap-1">
                        <ExclamationTriangleIcon className="w-3.5 h-3.5" />
                        Unsaved changes
                      </span>
                    ) : id ? (
                      <span className="text-green-500 flex items-center gap-1">
                        <CheckIcon className="w-3.5 h-3.5" />
                        All changes saved
                      </span>
                    ) : null}
                  </div>
                  <button
                    onClick={handleSave}
                    disabled={isSaving || !canCreateEstimate}
                    title={!canCreateEstimate ? `Missing: ${getMissingFields().join(', ')}` : undefined}
                    className={clsx(
                      "btn btn-primary",
                      hasUnsavedChanges && "ring-2 ring-orange-500/50 ring-offset-2 ring-offset-[var(--bg-primary)]"
                    )}
                  >
                    <CheckIcon className="w-4 h-4" />
                    {isSaving ? 'Saving...' : id ? 'Save Configuration' : 'Create Estimate'}
                  </button>
                </div>
              </div>
            )}
          </motion.div>
          
          {/* Workloads List */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="space-y-4"
          >
            <div className="flex items-center justify-between flex-wrap gap-2">
              <h2 className="text-lg font-semibold flex items-center gap-2 text-[var(--text-primary)]">
                <ServerStackIcon className="w-5 h-5 text-orange-500" />
                Workloads
                <span className="ml-1 text-sm font-normal text-[var(--text-muted)]">
                  ({lineItems.length})
                </span>
              </h2>
              
              <div className="flex items-center gap-2">
                {/* Bulk Delete Button */}
                {selectedItems.size > 0 && (
                  <button
                    onClick={handleBulkDelete}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 bg-red-500/10 hover:bg-red-500/20 rounded-lg transition-colors"
                  >
                    <TrashIcon className="w-4 h-4" />
                    Delete ({selectedItems.size})
                  </button>
                )}
                
                {/* View Mode Toggle */}
                {lineItems.length > 0 && (
                  <div className="flex items-center gap-1 bg-[var(--bg-tertiary)] rounded-lg p-0.5">
                    <button
                      onClick={() => setWorkloadsViewMode('cards')}
                      className={clsx(
                        "p-1.5 rounded-md transition-colors",
                        workloadsViewMode === 'cards'
                          ? "bg-[var(--bg-primary)] text-orange-500 shadow-sm"
                          : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                      )}
                      title="Compact cards (default)"
                    >
                      <Squares2X2Icon className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setWorkloadsViewMode('expanded')}
                      className={clsx(
                        "p-1.5 rounded-md transition-colors",
                        workloadsViewMode === 'expanded'
                          ? "bg-[var(--bg-primary)] text-orange-500 shadow-sm"
                          : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                      )}
                      title="Expanded cards with details"
                    >
                      <ListBulletIcon className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setWorkloadsViewMode('table')}
                      className={clsx(
                        "p-1.5 rounded-md transition-colors",
                        workloadsViewMode === 'table'
                          ? "bg-[var(--bg-primary)] text-orange-500 shadow-sm"
                          : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                      )}
                      title="Table view for comparison"
                    >
                      <TableCellsIcon className="w-4 h-4" />
                    </button>
                  </div>
                )}
              </div>
            </div>
            
            {!id ? (
              <div className="card p-8 text-center">
                {!canCreateEstimate ? (
                  <>
                    <p className="text-sm mb-2 text-[var(--text-muted)]">Complete required fields to create estimate</p>
                    <p className="text-xs text-orange-500 mb-3">
                      Missing: {getMissingFields().join(', ')}
                    </p>
                  </>
                ) : (
                  <p className="text-sm mb-3 text-[var(--text-muted)]">Save the estimate first to add workloads</p>
                )}
                <button
                  onClick={handleSave}
                  disabled={isSaving || !canCreateEstimate}
                  className="btn btn-primary"
                >
                  <CheckIcon className="w-4 h-4" />
                  Create Estimate
                </button>
              </div>
            ) : isLoadingLineItems && !lineItemsLoaded ? (
              <div className="card p-8 text-center">
                <div className="flex flex-col items-center gap-4">
                  <div className="relative">
                    <div className="w-12 h-12 rounded-full border-4 border-[var(--border-primary)] border-t-orange-500 animate-spin"></div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-[var(--text-primary)]">Loading workloads...</p>
                    <p className="text-xs text-[var(--text-muted)] mt-1">Fetching line items for this estimate</p>
                  </div>
                </div>
              </div>
            ) : (
              <>
                {/* Table View - Simplified & Usable */}
                {workloadsViewMode === 'table' && lineItems.length > 0 && (
                  <div className="card overflow-hidden">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-[var(--border-primary)] bg-[var(--bg-tertiary)]">
                          <th className="w-6 p-1.5 pl-2">
                            <input
                              type="checkbox"
                              checked={selectedItems.size === lineItems.length && lineItems.length > 0}
                              onChange={toggleSelectAll}
                              className="w-3 h-3 rounded border-[var(--border-primary)] text-orange-500 focus:ring-orange-500"
                            />
                          </th>
                          <th className="text-left p-1.5 font-medium text-[var(--text-muted)] uppercase text-[10px] tracking-wider">Workload</th>
                          <th className="text-left p-1.5 font-medium text-[var(--text-muted)] uppercase text-[10px] tracking-wider">Usage</th>
                          <th className="text-right p-1.5 font-medium text-[var(--text-muted)] uppercase text-[10px] tracking-wider pr-2">Cost/mo</th>
                          <th className="w-16 p-1.5"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {lineItems.map((item) => {
                          // Use pending form edits for real-time cost preview during editing
                          const costs = calculateItemCost(item, pendingFormEdits[item.line_item_id])
                          const typeConfig = getWorkloadTypeConfig(item.workload_type)
                          const TypeIcon = typeConfig.icon
                          const isExpanded = expandedItems.has(item.line_item_id)
                          const isSelected = selectedItems.has(item.line_item_id)
                          
                          // Build usage summary
                          const usageParts: string[] = []
                          if (item.runs_per_day && item.avg_runtime_minutes) {
                            usageParts.push(`${item.runs_per_day}×${item.avg_runtime_minutes}m/day`)
                          } else if (item.hours_per_month) {
                            usageParts.push(`${item.hours_per_month}h/mo`)
                          }
                          if (item.num_workers) {
                            usageParts.push(`${item.num_workers}w`)
                          }
                          const usageSummary = usageParts.join(' • ') || '—'
                          
                          // Check if VM costs loading
                          const wType = item.workload_type || ''
                          const needsVMCosts = !item.serverless_enabled && 
                            ['JOBS', 'ALL_PURPOSE', 'DLT'].includes(wType) ||
                            (wType === 'DBSQL' && item.dbsql_warehouse_type !== 'SERVERLESS')
                          const showVMLoading = isLoadingVMCosts && needsVMCosts && costs.vmCost === 0
                          
                          return (
                            <React.Fragment key={item.line_item_id}>
                              <tr 
                                className={clsx(
                                  "border-b border-[var(--border-primary)] hover:bg-[var(--bg-hover)] cursor-pointer",
                                  isSelected && "bg-orange-500/5",
                                  isExpanded && "bg-[var(--bg-tertiary)]"
                                )}
                                onClick={() => toggleExpand(item.line_item_id)}
                              >
                                <td className="p-1.5 pl-2" onClick={(e) => e.stopPropagation()}>
                                  <input
                                    type="checkbox"
                                    checked={isSelected}
                                    onChange={() => toggleItemSelection(item.line_item_id)}
                                    className="w-3 h-3 rounded border-[var(--border-primary)] text-orange-500 focus:ring-orange-500"
                                  />
                                </td>
                                <td className="p-1.5">
                                  <div className="flex items-center gap-2">
                                    <div className={clsx("w-6 h-6 rounded flex items-center justify-center flex-shrink-0", typeConfig.bgColor)}>
                                      <TypeIcon className={clsx("w-3.5 h-3.5", typeConfig.color)} />
                                    </div>
                                    <div className="min-w-0">
                                      <div className="flex items-center gap-1.5">
                                        <p className="font-medium text-[var(--text-primary)] text-xs truncate max-w-[180px]">{item.workload_name}</p>
                                        {(item.serverless_enabled || (item.workload_type === 'DBSQL' && item.dbsql_warehouse_type === 'SERVERLESS')) && (
                                          <span className="text-[9px] px-1 rounded bg-teal-500/10 text-teal-600 dark:text-teal-400 flex-shrink-0">S</span>
                                        )}
                                        {item.photon_enabled && (
                                          <span className="text-[9px] px-1 rounded bg-orange-500/10 text-orange-600 dark:text-orange-400 flex-shrink-0">⚡</span>
                                        )}
                                      </div>
                                      <p className="text-[10px] text-[var(--text-muted)]">
                                        {workloadTypes.find(w => w.workload_type === item.workload_type)?.display_name || item.workload_type}
                                      </p>
                                    </div>
                                  </div>
                                </td>
                                <td className="p-1.5">
                                  <span className="text-[10px] text-[var(--text-secondary)]">{usageSummary}</span>
                                </td>
                                <td className="p-1.5 pr-2 text-right">
                                  <p className={clsx(
                                    "font-bold text-sm",
                                    showVMLoading ? "text-orange-500/60" : "text-orange-500"
                                  )}>
                                    {formatCurrency(costs.totalCost)}
                                  </p>
                                  <p className="text-[9px] text-[var(--text-muted)]">
                                    {formatNumber(costs.monthlyDBUs)} DBUs
                                  </p>
                                </td>
                                <td className="p-1.5">
                                  <div className="flex items-center justify-end gap-0.5">
                                    <button
                                      onClick={(e) => handleCloneWorkload(e, item)}
                                      className="p-1 rounded text-[var(--text-muted)] hover:text-blue-500 hover:bg-blue-500/10"
                                      title="Clone"
                                    >
                                      <DocumentDuplicateIcon className="w-3 h-3" />
                                    </button>
                                    <button
                                      onClick={(e) => { e.stopPropagation(); handleDeleteLineItem(item) }}
                                      className="p-1 rounded text-[var(--text-muted)] hover:text-red-500 hover:bg-red-500/10"
                                      title="Delete"
                                    >
                                      <TrashIcon className="w-3 h-3" />
                                    </button>
                                    {isExpanded ? (
                                      <ChevronUpIcon className="w-3 h-3 text-orange-500" />
                                    ) : (
                                      <ChevronDownIcon className="w-3 h-3 text-[var(--text-muted)]" />
                                    )}
                                  </div>
                                </td>
                              </tr>
                              {/* Expanded Form Row */}
                              {isExpanded && (
                                <tr>
                                  <td colSpan={5} className="p-0 bg-[var(--bg-secondary)] border-b-2 border-orange-500/20">
                                    <div className="p-4">
                                      <WorkloadForm
                                        estimateId={id}
                                        lineItem={item}
                                        onClose={() => {
                                          setExpandedItems(new Set())
                                          // Clear pending edits when closing
                                          setPendingFormEdits(prev => {
                                            const next = { ...prev }
                                            delete next[item.line_item_id]
                                            return next
                                          })
                                        }}
                                        onSave={() => {
                                          markAsChanged()
                                          // Clear pending edits after save
                                          setPendingFormEdits(prev => {
                                            const next = { ...prev }
                                            delete next[item.line_item_id]
                                            return next
                                          })
                                        }}
                                        onFormChange={(formData) => {
                                          setPendingFormEdits(prev => ({
                                            ...prev,
                                            [item.line_item_id]: formData
                                          }))
                                        }}
                                        inline
                                      />
                                    </div>
                                  </td>
                                </tr>
                              )}
                            </React.Fragment>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
                
                {/* Card Views (Compact and Expanded) */}
                {workloadsViewMode !== 'table' && lineItems.map((item, index) => {
                  // Use pending form edits for real-time cost preview during editing
                  const costs = calculateItemCost(item, pendingFormEdits[item.line_item_id])
                  const isExpanded = expandedItems.has(item.line_item_id)
                  const usageSummary = getUsageSummary(item)
                  const typeConfig = getWorkloadTypeConfig(item.workload_type)
                  const TypeIcon = typeConfig.icon
                  // Show details row only in 'expanded' mode OR when the item is expanded for editing
                  const showDetailsRow = workloadsViewMode === 'expanded' || isExpanded
                  
                  return (
                    <motion.div
                      key={item.line_item_id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.02 }}
                      className="card overflow-hidden"
                    >
                      {/* Workload Header */}
                      <div 
                        className={clsx(
                          "p-4 cursor-pointer hover:bg-[var(--bg-hover)] transition-colors",
                          workloadsViewMode === 'cards' && !isExpanded && "py-3"
                        )}
                        onClick={() => toggleExpand(item.line_item_id)}
                      >
                        {/* Top row: name, badges, cost, actions */}
                        <div className="flex items-center gap-4">
                          <div className={clsx(
                            "rounded-lg flex items-center justify-center flex-shrink-0",
                            workloadsViewMode === 'cards' && !isExpanded ? "w-8 h-8" : "w-10 h-10",
                            typeConfig.bgColor
                          )}>
                            <TypeIcon className={clsx(
                              typeConfig.color,
                              workloadsViewMode === 'cards' && !isExpanded ? "w-4 h-4" : "w-5 h-5"
                            )} />
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <h4 className={clsx(
                                "font-semibold truncate text-[var(--text-primary)]",
                                workloadsViewMode === 'cards' && !isExpanded && "text-sm"
                              )}>{item.workload_name}</h4>
                              {(item.serverless_enabled || (item.workload_type === 'DBSQL' && item.dbsql_warehouse_type === 'SERVERLESS')) && (
                                <span className="badge badge-teal">Serverless</span>
                              )}
                              {item.photon_enabled && (
                                <span className="badge badge-orange">
                                  <BoltIcon className="w-3 h-3 mr-0.5" />
                                  Photon
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] mt-0.5">
                              <span>{workloadTypes.find(w => w.workload_type === item.workload_type)?.display_name || item.workload_type}</span>
                            </div>
                          </div>
                          
                          {/* Cost - Instant local calculation */}
                          <div className="text-right min-w-[100px]">
                            {/* Check if this workload needs VM costs and we're still loading them */}
                            {(() => {
                              // Workloads that need VM costs: classic compute (not serverless)
                              const wType = item.workload_type || ''
                              const needsVMCosts = !item.serverless_enabled && 
                                ['JOBS', 'ALL_PURPOSE', 'DLT'].includes(wType) ||
                                (wType === 'DBSQL' && item.dbsql_warehouse_type !== 'SERVERLESS')
                              const showVMLoading = isLoadingVMCosts && needsVMCosts && costs.vmCost === 0
                              
                              return (
                                <>
                                  <p className={clsx(
                                    "font-bold text-orange-500 transition-opacity",
                                    workloadsViewMode === 'cards' && !isExpanded ? "text-base" : "text-lg",
                                    showVMLoading && "opacity-60"
                                  )}>
                                    {formatCurrency(costs.totalCost)}
                                    {showVMLoading && <span className="text-xs font-normal text-[var(--text-muted)] ml-1">...</span>}
                                  </p>
                                  <p className="text-xs text-[var(--text-muted)]">{formatNumber(costs.monthlyDBUs)} DBUs/mo</p>
                                </>
                              )
                            })()}
                          </div>
                          
                          {/* Actions */}
                          <div className="flex items-center gap-1">
                            <button
                              onClick={(e) => handleCloneWorkload(e, item)}
                              className="p-1.5 rounded-md text-[var(--text-muted)] hover:text-blue-500 hover:bg-blue-500/10"
                              title="Clone workload"
                            >
                              <DocumentDuplicateIcon className="w-4 h-4" />
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                handleDeleteLineItem(item)
                              }}
                              className="p-1.5 rounded-md text-[var(--text-muted)] hover:text-red-500 hover:bg-red-500/10"
                              title="Delete workload"
                            >
                              <TrashIcon className="w-4 h-4" />
                            </button>
                            {isExpanded ? (
                              <ChevronUpIcon className="w-5 h-5 text-[var(--text-muted)]" />
                            ) : (
                              <ChevronDownIcon className="w-5 h-5 text-[var(--text-muted)]" />
                            )}
                          </div>
                        </div>
                        
                        {/* Bottom row: Cost breakdown & config summary (only in expanded mode or when item is expanded) */}
                        {showDetailsRow && (
                          <>
                            <div className="mt-3 pt-3 border-t border-[var(--border-primary)] grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 text-xs">
                              <div>
                                <span className="text-[var(--text-muted)]">DBU Cost</span>
                                <p className="font-semibold text-[var(--text-primary)]">{formatCurrency(costs.dbuCost)}</p>
                              </div>
                              {/* Hide VM Cost for serverless workloads */}
                              {!['VECTOR_SEARCH', 'MODEL_SERVING', 'FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY', 'LAKEBASE'].includes(item.workload_type || '') && (
                                <div>
                                  <span className="text-[var(--text-muted)]">VM Cost</span>
                                  <p className="font-semibold text-[var(--text-primary)]">{formatCurrency(costs.vmCost)}</p>
                                </div>
                              )}
                              
                              {/* Vector Search: Units Used (prominent) */}
                              {item.workload_type === 'VECTOR_SEARCH' && costs.unitsUsed !== undefined && (
                                <div>
                                  <span className="text-[var(--text-muted)]">Units Used</span>
                                  <p className="font-semibold text-blue-600 dark:text-blue-400">{costs.unitsUsed} unit{costs.unitsUsed !== 1 ? 's' : ''}</p>
                                </div>
                              )}
                              
                              {/* Compute workloads: show driver/worker nodes */}
                              {(item.workload_type === 'JOBS' || item.workload_type === 'ALL_PURPOSE' || item.workload_type === 'DLT') && (
                                <>
                                  {item.driver_node_type && (
                                    <div>
                                      <span className="text-[var(--text-muted)]">Driver</span>
                                      <p className="font-mono text-[var(--text-primary)] text-[10px]">{item.driver_node_type}</p>
                                    </div>
                                  )}
                                  {item.worker_node_type && (
                                    <div>
                                      <span className="text-[var(--text-muted)]">Workers</span>
                                      <p className="text-[var(--text-primary)]">{item.num_workers}× <span className="font-mono text-[10px]">{item.worker_node_type}</span></p>
                                    </div>
                                  )}
                                </>
                              )}
                              
                              {/* Workload-specific details */}
                              {getWorkloadSummaryDetails(item).map((detail, idx) => (
                                <div key={idx}>
                                  <span className="text-[var(--text-muted)]">{detail.label}</span>
                                  <p className="text-[var(--text-primary)]">{detail.value}</p>
                                </div>
                              ))}
                              
                              {/* Usage summary */}
                              {usageSummary && (
                                <div>
                                  <span className="text-[var(--text-muted)]">Usage</span>
                                  <p className="text-[var(--text-primary)]">{usageSummary}</p>
                                </div>
                              )}
                            </div>
                            
                            {/* Calculation Formula Display */}
                            <div className="mt-2 pt-2 border-t border-dashed border-[var(--border-primary)]">
                              <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-muted)] flex-wrap">
                                <span className="text-[var(--text-secondary)] font-semibold">Formula:</span>
                                {(() => {
                                  const hoursPerMonth = item.hours_per_month || 
                                    (item.runs_per_day && item.avg_runtime_minutes 
                                      ? item.runs_per_day * (item.avg_runtime_minutes / 60) * (item.days_per_month || 30)
                                      : 730)
                                  const dbuPriceDisplay = costs.dbuPrice?.toFixed(2) || '0.00'
                                  
                                  // Vector Search
                                  if (item.workload_type === 'VECTOR_SEARCH') {
                                    return (
                                      <>
                                        <span className="text-blue-500">{costs.unitsUsed || 1} units</span>
                                        <span>×</span>
                                        <span className="text-purple-500">{costs.dbuPerHour?.toFixed(2) || '4.00'} DBU/hr</span>
                                        <span>×</span>
                                        <span className="text-green-500">{hoursPerMonth.toFixed(0)}h</span>
                                        <span>=</span>
                                        <span className="text-orange-500">{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                        <span>×</span>
                                        <span className="text-pink-500">${dbuPriceDisplay}/DBU</span>
                                        <span>=</span>
                                        <span className="text-orange-600 font-semibold">{formatCurrency(costs.totalCost)}</span>
                                      </>
                                    )
                                  }
                                  
                                  // FMAPI (token-based)
                                  if (item.workload_type === 'FMAPI_DATABRICKS' || item.workload_type === 'FMAPI_PROPRIETARY') {
                                    return (
                                      <>
                                        <span className="text-blue-500">{item.fmapi_quantity || 0}M tokens</span>
                                        <span>×</span>
                                        <span className="text-purple-500">{(costs.monthlyDBUs / (item.fmapi_quantity || 1)).toFixed(2)} DBU/M</span>
                                        <span>=</span>
                                        <span className="text-orange-500">{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                        <span>×</span>
                                        <span className="text-pink-500">${dbuPriceDisplay}/DBU</span>
                                        <span>=</span>
                                        <span className="text-orange-600 font-semibold">{formatCurrency(costs.totalCost)}</span>
                                      </>
                                    )
                                  }
                                  
                                  // Lakebase
                                  if (item.workload_type === 'LAKEBASE') {
                                    return (
                                      <>
                                        <span className="text-blue-500">{item.lakebase_cu || 1} CU</span>
                                        <span>×</span>
                                        <span className="text-purple-500">{item.lakebase_ha_nodes || 1} nodes</span>
                                        <span>×</span>
                                        <span className="text-green-500">{hoursPerMonth.toFixed(0)}h</span>
                                        <span>=</span>
                                        <span className="text-orange-500">{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                        <span>×</span>
                                        <span className="text-pink-500">${dbuPriceDisplay}/DBU</span>
                                        <span>=</span>
                                        <span className="text-orange-600 font-semibold">{formatCurrency(costs.totalCost)}</span>
                                      </>
                                    )
                                  }
                                  
                                  // Model Serving
                                  if (item.workload_type === 'MODEL_SERVING') {
                                    return (
                                      <>
                                        <span className="text-purple-500">{costs.dbuPerHour?.toFixed(2) || '2.00'} DBU/hr</span>
                                        <span>×</span>
                                        <span className="text-green-500">{hoursPerMonth.toFixed(0)}h</span>
                                        <span>=</span>
                                        <span className="text-orange-500">{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                        <span>×</span>
                                        <span className="text-pink-500">${dbuPriceDisplay}/DBU</span>
                                        <span>=</span>
                                        <span className="text-orange-600 font-semibold">{formatCurrency(costs.totalCost)}</span>
                                      </>
                                    )
                                  }
                                  
                                  // Compute workloads (JOBS, ALL_PURPOSE, DLT, DBSQL)
                                  const hasVMCost = costs.vmCost > 0
                                  return (
                                    <>
                                      {costs.dbuPerHour && costs.dbuPerHour > 0 && (
                                        <>
                                          <span className="text-purple-500">{costs.dbuPerHour.toFixed(2)} DBU/hr</span>
                                          <span>×</span>
                                        </>
                                      )}
                                      <span className="text-green-500">{hoursPerMonth.toFixed(0)}h</span>
                                      <span>=</span>
                                      <span className="text-orange-500">{formatNumber(costs.monthlyDBUs)} DBUs</span>
                                      <span>×</span>
                                      <span className="text-pink-500">${dbuPriceDisplay}/DBU</span>
                                      {hasVMCost ? (
                                        <>
                                          <span className="mx-1">|</span>
                                          <span className="text-blue-500">{formatCurrency(costs.dbuCost)}</span>
                                          <span>+</span>
                                          <span className="text-teal-500">VM: {formatCurrency(costs.vmCost)}</span>
                                          <span>=</span>
                                        </>
                                      ) : (
                                        <span>=</span>
                                      )}
                                      <span className="text-orange-600 font-semibold">{formatCurrency(costs.totalCost)}</span>
                                    </>
                                  )
                                })()}
                              </div>
                            </div>
                          </>
                        )}
                      </div>
                      
                      {/* Expanded: Edit Form */}
                      {isExpanded && (
                        <div className="border-t border-[var(--border-primary)] p-4 bg-[var(--bg-tertiary)]">
                          <WorkloadForm
                            estimateId={id}
                            lineItem={item}
                            onClose={() => {
                              setExpandedItems(new Set())
                              // Clear pending edits when closing
                              setPendingFormEdits(prev => {
                                const next = { ...prev }
                                delete next[item.line_item_id]
                                return next
                              })
                            }}
                            onSave={() => {
                              markAsChanged()
                              // Clear pending edits after save
                              setPendingFormEdits(prev => {
                                const next = { ...prev }
                                delete next[item.line_item_id]
                                return next
                              })
                            }}
                            onFormChange={(formData) => {
                              setPendingFormEdits(prev => ({
                                ...prev,
                                [item.line_item_id]: formData
                              }))
                            }}
                            inline
                          />
                        </div>
                      )}
                    </motion.div>
                  )
                })}
                
                {/* Add New Workload Section */}
                {!canAddWorkload ? (
                  <div className="p-4 rounded-xl border-2 border-dashed border-[var(--border-secondary)] bg-[var(--bg-tertiary)] text-center">
                    <ExclamationTriangleIcon className="w-6 h-6 mx-auto mb-2 text-orange-500" />
                    <p className="text-sm text-[var(--text-muted)]">
                      Please select a <span className="font-semibold text-[var(--text-secondary)]">Region</span> and <span className="font-semibold text-[var(--text-secondary)]">Databricks Tier</span> before adding workloads
                    </p>
                  </div>
                ) : showAddForm ? (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="card p-5"
                  >
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-semibold text-[var(--text-primary)]">Add New Workload</h3>
                      <button
                        onClick={() => setShowAddForm(false)}
                        className="text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                      >
                        Cancel
                      </button>
                    </div>
                    <WorkloadForm
                      estimateId={id}
                      lineItem={null}
                      onClose={() => setShowAddForm(false)}
                      onSave={markAsChanged}
                      inline
                    />
                  </motion.div>
                ) : (
                  <button
                    onClick={() => setShowAddForm(true)}
                    className="w-full p-4 rounded-xl border-2 border-dashed border-[var(--border-secondary)] hover:border-orange-500/50 hover:bg-orange-500/5 transition-all flex items-center justify-center gap-2 text-[var(--text-muted)] hover:text-orange-500"
                  >
                    <PlusIcon className="w-5 h-5" />
                    Add Workload
                  </button>
                )}
              </>
            )}
          </motion.div>
        </div>
        
        {/* Cost Summary Sidebar - Right column, Collapsible */}
        <div className={clsx(
          "lg:col-span-1",
          isCostSummaryCollapsed && "fixed right-0 top-24 z-40"
        )}>
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.15 }}
            className={clsx(
              "card",
              isCostSummaryCollapsed ? "p-2 w-14" : "p-4",
              isCostSummaryPinned ? "sticky top-24" : ""
            )}
          >
            {/* Toggle Button */}
            <button
              onClick={() => setIsCostSummaryCollapsed(!isCostSummaryCollapsed)}
              className={clsx(
                "absolute -left-3 top-6 z-10 w-6 h-6 rounded-full border flex items-center justify-center",
                "bg-[var(--bg-secondary)] border-[var(--border-primary)] hover:bg-[var(--bg-tertiary)]",
                "shadow-sm"
              )}
              title={isCostSummaryCollapsed ? "Expand cost summary" : "Collapse cost summary"}
            >
              {isCostSummaryCollapsed ? (
                <ChevronLeftIcon className="w-3.5 h-3.5 text-[var(--text-secondary)]" />
              ) : (
                <ChevronRightIcon className="w-3.5 h-3.5 text-[var(--text-secondary)]" />
              )}
            </button>
            
            {/* Collapsed View - Just show total */}
            {isCostSummaryCollapsed ? (
              <div className="flex flex-col items-center gap-2 py-2">
                <CurrencyDollarIcon className="w-5 h-5 text-orange-500" />
                <div className="writing-mode-vertical text-center">
                  <p className="text-xs font-bold text-orange-500 [writing-mode:vertical-rl] rotate-180">
                    {formatCurrency(totalCosts.totalCost)}
                  </p>
                  <p className="text-[9px] text-[var(--text-muted)] [writing-mode:vertical-rl] rotate-180 mt-1">
                    /month
                  </p>
                </div>
              </div>
            ) : (
              <>
            <div className="flex items-center justify-between mb-3">
              <h3 className="section-title flex items-center gap-2 mb-0">
                <CurrencyDollarIcon className="w-4 h-4" />
                <span className="text-sm">Cost Summary</span>
                {(isLoadingLineItems && !lineItemsLoaded) && (
                  <div className="w-3 h-3 border-2 border-orange-500/30 border-t-orange-500 rounded-full animate-spin" />
                )}
              </h3>
              {/* Pin/Unpin Toggle */}
              <button
                onClick={() => setIsCostSummaryPinned(!isCostSummaryPinned)}
                className={clsx(
                  "p-1 rounded text-[10px]",
                  isCostSummaryPinned 
                    ? "text-orange-500 bg-orange-500/10" 
                    : "text-[var(--text-muted)] hover:bg-[var(--bg-tertiary)]"
                )}
                title={isCostSummaryPinned ? "Unpin (scroll with page)" : "Pin to viewport"}
              >
                {isCostSummaryPinned ? "📌" : "📍"}
              </button>
            </div>
            
            {!canAddWorkload ? (
              <div className="text-center py-6">
                <ExclamationTriangleIcon className="w-10 h-10 mx-auto mb-2 text-orange-500" />
                <p className="text-sm text-[var(--text-muted)]">Select a region and tier to see cost estimates</p>
              </div>
            ) : (isLoadingLineItems && !lineItemsLoaded) ? (
              /* Loading line items state */
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-orange-500" />
                    <span className="text-sm text-[var(--text-secondary)]">DBU Cost</span>
                  </div>
                  <div className="h-5 w-20 bg-[var(--bg-tertiary)] rounded animate-pulse" />
                </div>
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-orange-400" />
                    <span className="text-sm text-[var(--text-secondary)]">VM Cost</span>
                  </div>
                  <div className="h-5 w-20 bg-[var(--bg-tertiary)] rounded animate-pulse" />
                </div>
                <div className="border-t border-[var(--border-primary)] pt-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-semibold text-[var(--text-primary)]">Monthly Total</span>
                    <div className="h-8 w-28 bg-[var(--bg-tertiary)] rounded animate-pulse" />
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-[var(--text-muted)]">Annual Total</span>
                    <div className="h-5 w-24 bg-[var(--bg-tertiary)] rounded animate-pulse" />
                  </div>
                </div>
                <div className="pt-3 border-t border-[var(--border-primary)]">
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-[var(--text-muted)]">Total DBUs/month</span>
                    <div className="h-5 w-16 bg-[var(--bg-tertiary)] rounded animate-pulse" />
                  </div>
                </div>
                <p className="text-xs text-center text-[var(--text-muted)] pt-2">Loading workloads...</p>
              </div>
            ) : lineItems.length > 0 ? (
              <div className="space-y-3">
                {/* Monthly Total - Compact Hero */}
                <div className="text-center pb-3 border-b border-[var(--border-primary)]">
                  <div className="relative">
                    <p className={clsx(
                      "text-2xl font-bold text-orange-500",
                      isLoadingVMCosts && "opacity-60"
                    )}>
                      {formatCurrency(totalCosts.totalCost)}
                      <span className="text-sm font-normal text-[var(--text-muted)]">/mo</span>
                    </p>
                    {isLoadingVMCosts && (
                      <p className="text-[10px] text-[var(--text-muted)] animate-pulse">
                        Calculating...
                      </p>
                    )}
                  </div>
                  <p className="text-xs text-[var(--text-secondary)]">
                    {formatCurrency(totalCosts.totalCost * 12)}/year
                  </p>
                </div>
                
                {/* Cost Breakdown - Inline */}
                <div className="flex justify-between text-xs">
                  <span className="text-[var(--text-muted)]">DBU: <span className="text-[var(--text-primary)] font-medium">{formatCurrency(totalCosts.totalDBUCost)}</span></span>
                  <span className="text-[var(--text-muted)]">VM: <span className={clsx("font-medium", isLoadingVMCosts ? "text-[var(--text-muted)]" : "text-[var(--text-primary)]")}>{isLoadingVMCosts ? '...' : formatCurrency(totalCosts.totalVMCost)}</span></span>
                  <span className="text-[var(--text-muted)]">{formatNumber(totalCosts.totalDBUs)} DBUs</span>
                </div>
                
                {/* Workload Breakdown - Progressive Disclosure */}
                {lineItems.length > 0 && (
                  <div className="pt-2 border-t border-[var(--border-primary)]">
                    {/* Show expand button for <5 workloads OR always show for >=5 */}
                    {lineItems.length < 5 && !showCostDetails ? (
                      <button
                        onClick={() => setShowCostDetails(true)}
                        className="w-full text-xs text-[var(--text-muted)] hover:text-orange-500 py-1"
                      >
                        Show breakdown ({lineItems.length} workloads) ▼
                      </button>
                    ) : (
                      <>
                        <div className="flex items-center justify-between mb-1.5">
                          <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--text-muted)]">
                            Workloads ({lineItems.length})
                          </p>
                          {lineItems.length < 5 && (
                            <button
                              onClick={() => setShowCostDetails(false)}
                              className="text-[10px] text-[var(--text-muted)] hover:text-orange-500"
                            >
                              Hide ▲
                            </button>
                          )}
                        </div>
                        <div className="space-y-1 max-h-48 overflow-y-auto">
                          {(() => {
                            const sortedItems = [...lineItems]
                              .map(item => ({ item, costs: calculateItemCost(item) }))
                              .sort((a, b) => b.costs.totalCost - a.costs.totalCost)
                            
                            const barColors = ['bg-orange-500', 'bg-amber-500', 'bg-blue-500', 'bg-emerald-500', 'bg-purple-500', 'bg-pink-500', 'bg-cyan-500', 'bg-indigo-500']
                            
                            return sortedItems.map(({ item, costs }, idx) => {
                              const percent = totalCosts.totalCost > 0 ? (costs.totalCost / totalCosts.totalCost) * 100 : 0
                              const barColor = barColors[idx % barColors.length]
                              return (
                                <div key={item.line_item_id} className="group">
                                  <div className="flex items-center justify-between text-[11px] mb-0.5">
                                    <span className="text-[var(--text-secondary)] truncate max-w-[90px]" title={item.workload_name}>{item.workload_name}</span>
                                    <div className="flex items-center gap-1.5">
                                      <span className="text-[var(--text-muted)] text-[10px]">{percent.toFixed(0)}%</span>
                                      <span className="font-medium text-[var(--text-primary)] w-14 text-right">{formatCurrency(costs.totalCost)}</span>
                                    </div>
                                  </div>
                                  <div className="h-1 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
                                    <div 
                                      className={clsx("h-full rounded-full", barColor)}
                                      style={{ width: `${Math.max(percent, 1)}%` }}
                                    />
                                  </div>
                                </div>
                              )
                            })
                          })()}
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-6">
                <CurrencyDollarIcon className="w-10 h-10 mx-auto mb-2 text-[var(--text-muted)]" />
                <p className="text-sm text-[var(--text-muted)]">Add workloads to see cost estimates</p>
              </div>
            )}
            
            {/* Disclaimer */}
            <p className="mt-3 text-[10px] text-[var(--text-muted)] text-center">
              Estimates based on published pricing
            </p>
              </>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  )
}
