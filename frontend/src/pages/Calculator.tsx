import { useEffect, useState, useMemo, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  PlusIcon,
  ArrowDownTrayIcon,
  ArrowLeftIcon,
  ArrowPathIcon,
  CheckIcon,
  TrashIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  BoltIcon,
  CpuChipIcon,
  CurrencyDollarIcon,
  ServerStackIcon,
  ExclamationTriangleIcon,
  BuildingOfficeIcon
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

// Cloud provider visual options
const CLOUD_PROVIDERS = [
  { id: 'aws', name: 'AWS', logo: '/aws.svg', bgClass: 'from-amber-600/20 to-amber-900/10' },
  { id: 'azure', name: 'Azure', logo: '/azure.svg', bgClass: 'from-sky-600/20 to-sky-900/10' },
  { id: 'gcp', name: 'GCP', logo: '/gcp.svg', bgClass: 'from-red-600/20 to-red-900/10' }
]

// DBU Pricing (per DBU per hour)
const DBU_PRICING: Record<string, Record<string, number>> = {
  aws: {
    'JOBS_COMPUTE': 0.15,
    'JOBS_COMPUTE_(PHOTON)': 0.20,
    'JOBS_SERVERLESS_COMPUTE': 0.25,
    'ALL_PURPOSE_COMPUTE': 0.40,
    'ALL_PURPOSE_COMPUTE_(PHOTON)': 0.55,
    'INTERACTIVE_SERVERLESS_COMPUTE': 0.70,
    'DLT_CORE_COMPUTE': 0.20,
    'DLT_PRO_COMPUTE': 0.25,
    'DLT_ADVANCED_COMPUTE': 0.30,
    'DLT_CORE_COMPUTE_(PHOTON)': 0.25,
    'DELTA_LIVE_TABLES_SERVERLESS': 0.30,
    'SQL_COMPUTE': 0.22,
    'SQL_PRO_COMPUTE': 0.55,
    'SERVERLESS_SQL_COMPUTE': 0.70,
    'VECTOR_SEARCH_ENDPOINT': 0.40,
    'SERVERLESS_REAL_TIME_INFERENCE': 0.07,
    'DATABASE_SERVERLESS_COMPUTE': 0.35
  },
  azure: {
    'JOBS_COMPUTE': 0.15,
    'JOBS_COMPUTE_(PHOTON)': 0.20,
    'JOBS_SERVERLESS_COMPUTE': 0.25,
    'ALL_PURPOSE_COMPUTE': 0.40,
    'ALL_PURPOSE_COMPUTE_(PHOTON)': 0.55,
    'INTERACTIVE_SERVERLESS_COMPUTE': 0.70,
    'DLT_CORE_COMPUTE': 0.20,
    'DLT_PRO_COMPUTE': 0.25,
    'DLT_ADVANCED_COMPUTE': 0.30,
    'DLT_CORE_COMPUTE_(PHOTON)': 0.25,
    'DELTA_LIVE_TABLES_SERVERLESS': 0.30,
    'SQL_COMPUTE': 0.22,
    'SQL_PRO_COMPUTE': 0.55,
    'SERVERLESS_SQL_COMPUTE': 0.70,
    'VECTOR_SEARCH_ENDPOINT': 0.40,
    'SERVERLESS_REAL_TIME_INFERENCE': 0.07,
    'DATABASE_SERVERLESS_COMPUTE': 0.35
  },
  gcp: {
    'JOBS_COMPUTE': 0.15,
    'JOBS_COMPUTE_(PHOTON)': 0.20,
    'JOBS_SERVERLESS_COMPUTE': 0.25,
    'ALL_PURPOSE_COMPUTE': 0.40,
    'ALL_PURPOSE_COMPUTE_(PHOTON)': 0.55,
    'INTERACTIVE_SERVERLESS_COMPUTE': 0.70,
    'DLT_CORE_COMPUTE': 0.20,
    'DLT_PRO_COMPUTE': 0.25,
    'DLT_ADVANCED_COMPUTE': 0.30,
    'DLT_CORE_COMPUTE_(PHOTON)': 0.25,
    'DELTA_LIVE_TABLES_SERVERLESS': 0.30,
    'SQL_COMPUTE': 0.22,
    'SQL_PRO_COMPUTE': 0.55,
    'SERVERLESS_SQL_COMPUTE': 0.70,
    'VECTOR_SEARCH_ENDPOINT': 0.40,
    'SERVERLESS_REAL_TIME_INFERENCE': 0.07,
    'DATABASE_SERVERLESS_COMPUTE': 0.35
  }
}

// Instance DBU rates
const INSTANCE_DBU_RATES: Record<string, number> = {
  'i3.xlarge': 0.75, 'i3.2xlarge': 1.5, 'i3.4xlarge': 3.0, 'i3.8xlarge': 6.0, 'i3.16xlarge': 12.0,
  'm5.large': 0.25, 'm5.xlarge': 0.5, 'm5.2xlarge': 1.0, 'm5.4xlarge': 2.0,
  'r5.large': 0.35, 'r5.xlarge': 0.69, 'r5.2xlarge': 1.38,
  'c5.xlarge': 0.44, 'c5.2xlarge': 0.88,
  'p3.2xlarge': 5.5, 'p3.8xlarge': 22.0,
  'Standard_DS3_v2': 0.75, 'Standard_DS4_v2': 1.5, 'Standard_DS5_v2': 3.0,
  'Standard_D4s_v3': 0.5, 'Standard_D8s_v3': 1.0, 'Standard_D16s_v3': 2.0,
  'Standard_E4s_v3': 0.69, 'Standard_E8s_v3': 1.38,
  'Standard_L8s_v2': 1.5, 'Standard_NC6s_v3': 5.5,
  'n1-standard-4': 0.5, 'n1-standard-8': 1.0, 'n1-standard-16': 2.0, 'n1-standard-32': 4.0,
  'n1-highmem-4': 0.69, 'n1-highmem-8': 1.38,
  'n2-standard-4': 0.5, 'n2-standard-8': 1.0
}


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
}

export default function Calculator() {
  const { id } = useParams()
  const navigate = useNavigate()
  const {
    currentEstimate,
    lineItems,
    workloadTypes,
    fetchEstimateWithLineItems,
    fetchReferenceData,
    clearReferenceCache,
    isLoadingReferenceData,
    isReferenceDataLoaded,
    regionsMap,
    getRegionsForCloud,
    createEstimate,
    updateEstimate,
    deleteLineItem,
    setSelectedCloud,
    setSelectedRegion,
    fetchVMPricing,
    getVMPrice,
    // Cost calculation from API
    workloadCosts,
    calculateAllWorkloadCosts,
    clearWorkloadCosts,
    isCalculatingCost,
    calculatingCostIds,
    // DBU Rates
    dbuRatesMap,
    fetchDBURates,
    // State management
    clearEstimateState
  } = useStore()
  
  const [isSaving, setIsSaving] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [showAddForm, setShowAddForm] = useState(false)
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [isLoadingEstimate, setIsLoadingEstimate] = useState(false)
  const [isLoadingLineItems, setIsLoadingLineItems] = useState(false)
  const [lineItemsLoaded, setLineItemsLoaded] = useState(false)
  
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
  
  useEffect(() => {
    fetchReferenceData()
  }, [fetchReferenceData])
  
  // Fetch Salesforce accounts on mount or when search changes (debounced)
  useEffect(() => {
    const timeoutId = setTimeout(async () => {
      setIsLoadingSfAccounts(true)
      try {
        const accounts = await fetchSalesforceAccounts({ 
          search: sfAccountSearch || undefined,
          limit: 1000 
        })
        setSfAccounts(accounts)
      } catch (error) {
        console.error('Failed to fetch Salesforce accounts:', error)
      } finally {
        setIsLoadingSfAccounts(false)
      }
    }, 300) // 300ms debounce
    
    return () => clearTimeout(timeoutId)
  }, [sfAccountSearch])
  
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
  
  // Fetch VM pricing when cloud or region changes
  useEffect(() => {
    if (formData.cloud) {
      fetchVMPricing(formData.cloud, formData.region || undefined)
    }
  }, [formData.cloud, formData.region, fetchVMPricing])
  
  // Use cached regions from store (pre-loaded for all clouds)
  // This is instant - no API call needed when switching clouds
  useEffect(() => {
    if (!formData.cloud) return
    
    // Get regions from store cache (instant lookup)
    const cachedRegions = getRegionsForCloud(formData.cloud)
    
    if (cachedRegions.length > 0) {
      // Have cached regions - use them instantly
      setRegions(cachedRegions)
      setIsLoadingRegions(false)
    } else if (!isReferenceDataLoaded) {
      // Still loading reference data
      setIsLoadingRegions(true)
    } else {
      // Reference data loaded but no regions for this cloud
      setRegions([])
      setIsLoadingRegions(false)
    }
  }, [formData.cloud, regionsMap, isReferenceDataLoaded, getRegionsForCloud])
  
  useEffect(() => {
    const loadEstimateData = async () => {
      if (id) {
        setIsLoadingEstimate(true)
        setIsLoadingLineItems(true)
        setLineItemsLoaded(false)
        
        // Clear stale workload costs from previous estimate immediately
        clearWorkloadCosts()
        
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
  }, [id, fetchEstimateWithLineItems, clearEstimateState, clearWorkloadCosts])
  
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
    } else if (!id) {
      // Creating new estimate - reset to defaults
      setFormData(defaultEstimateFormData)
      setSelectedCloud('aws')
      setHasUnsavedChanges(false)
    }
  }, [currentEstimate, id, setSelectedCloud])
  
  // Fetch DBU rates when cloud/region/tier changes
  useEffect(() => {
    if (formData.cloud && formData.region && formData.tier) {
      fetchDBURates(formData.cloud.toUpperCase(), formData.region, formData.tier.toUpperCase())
    }
  }, [formData.cloud, formData.region, formData.tier, fetchDBURates])
  
  // Calculate costs for all workloads when lineItems or pricing config changes (debounced)
  // IMPORTANT: Must wait for currentEstimate to be loaded since calculateAllWorkloadCosts uses it
  const costCalcTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  useEffect(() => {
    // Ensure currentEstimate is loaded (not null) before calculating costs
    // The store's calculateAllWorkloadCosts reads cloud/region/tier from currentEstimate
    if (id && currentEstimate && lineItems.length > 0 && currentEstimate.cloud && currentEstimate.region && currentEstimate.tier) {
      // Debounce cost calculations to avoid excessive API calls
      if (costCalcTimeoutRef.current) {
        clearTimeout(costCalcTimeoutRef.current)
      }
      costCalcTimeoutRef.current = setTimeout(() => {
        calculateAllWorkloadCosts(id)
      }, 300) // 300ms debounce
    }
    
    return () => {
      if (costCalcTimeoutRef.current) {
        clearTimeout(costCalcTimeoutRef.current)
      }
    }
  }, [id, currentEstimate, lineItems, calculateAllWorkloadCosts])
  
  // Check if required fields are set for workload creation
  const canAddWorkload = Boolean(formData.region && formData.tier)
  
  // Calculate cost for a single line item with full breakdown
  // Prefers API-calculated costs, falls back to local calculation
  const calculateItemCost = (item: LineItem): CostBreakdown => {
    // Check if we have API-calculated cost for this item
    const apiResponse = workloadCosts[item.line_item_id]
    
    // If we're actively calculating and don't have API data yet, return zeros
    // This prevents showing stale local calculations during API fetch
    if (isCalculatingCost && !apiResponse) {
      return { monthlyDBUs: 0, dbuCost: 0, vmCost: 0, totalCost: 0 }
    }
    
    if (apiResponse?.success && apiResponse?.data) {
      const data = apiResponse.data
      
      // Handle different response formats:
      // - Standard compute workloads: { dbu_calculation, vm_costs, total_cost: { cost_per_month } }
      // - FMAPI/token-based workloads: { cost: { total_cost } }
      // - DBSQL workloads: { dbu_costs, vm_costs, total_cost: { cost_per_month } }
      const totalCost = data.total_cost?.cost_per_month ?? data.cost?.total_cost ?? 0
      const dbuCost = data.dbu_calculation?.dbu_cost_per_month ?? data.dbu_costs?.dbu_cost_per_month ?? 0
      const monthlyDBUs = data.dbu_calculation?.dbu_per_month ?? data.dbu_costs?.dbu_per_month ?? 0
      
      // If API returned 0 cost for FMAPI workloads, fall back to local calculation
      // (External API may not have pricing data configured)
      const isFMAPIWorkload = item.workload_type === 'FMAPI_DATABRICKS' || item.workload_type === 'FMAPI_PROPRIETARY'
      if (isFMAPIWorkload && totalCost === 0) {
        // Continue to local calculation below
      } else {
        return {
          monthlyDBUs,
          dbuCost,
          vmCost: data.vm_costs?.vm_cost_per_month || 0,
          totalCost
        }
      }
    }
    
    // Fall back to local calculation if API cost not available
    const cloud = formData.cloud || 'aws'
    const region = formData.region // No default - must be set
    // Try to use dynamic DBU rates first, fall back to hardcoded
    const pricing = Object.keys(dbuRatesMap).length > 0 ? dbuRatesMap : (DBU_PRICING[cloud] || DBU_PRICING.aws)
    const numWorkers = item.num_workers || 0
    
    // If no region selected, return zero costs
    if (!region) {
      return { monthlyDBUs: 0, dbuCost: 0, vmCost: 0, totalCost: 0 }
    }
    
    // ========================================
    // Step 1: Calculate hours per month
    // Formula: runs_per_day * (avg_runtime_minutes / 60) * days_per_month
    // ========================================
    let hoursPerMonth = 0
    if (item.workload_type !== 'FMAPI_DATABRICKS' && item.workload_type !== 'FMAPI_PROPRIETARY') {
      if (item.hours_per_month) {
        // Direct hours input
        hoursPerMonth = item.hours_per_month
      } else if (item.runs_per_day && item.avg_runtime_minutes) {
        // Calculate from runs: runs_per_day * (avg_runtime_minutes / 60) * days_per_month
        hoursPerMonth = (item.runs_per_day * (item.avg_runtime_minutes / 60)) * (item.days_per_month || 30)
      }
    }
    
    // ========================================
    // Step 2: Determine product_type_for_pricing (SKU)
    // Matches the SQL view's CASE logic
    // ========================================
    let productType = ''
    const dltEdition = item.dlt_edition || 'CORE'
    
    switch (item.workload_type) {
      case 'JOBS':
        if (item.serverless_enabled) {
          productType = 'JOBS_SERVERLESS_COMPUTE'
        } else if (item.photon_enabled) {
          productType = 'JOBS_COMPUTE_(PHOTON)'
        } else {
          productType = 'JOBS_COMPUTE'
        }
        break
      
      case 'ALL_PURPOSE':
        if (item.serverless_enabled) {
          productType = 'INTERACTIVE_SERVERLESS_COMPUTE'
        } else if (item.photon_enabled) {
          productType = 'ALL_PURPOSE_COMPUTE_(PHOTON)'
        } else {
          productType = 'ALL_PURPOSE_COMPUTE'
        }
        break
      
      case 'DLT':
        if (item.serverless_enabled) {
          productType = 'DELTA_LIVE_TABLES_SERVERLESS'
        } else {
          productType = `DLT_${dltEdition}_COMPUTE`
          if (item.photon_enabled) {
            productType += '_(PHOTON)'
          }
        }
        break
      
      case 'DBSQL':
        const warehouseType = item.dbsql_warehouse_type || 'SERVERLESS'
        if (warehouseType === 'SERVERLESS') {
          productType = 'SERVERLESS_SQL_COMPUTE'
        } else if (warehouseType === 'PRO') {
          productType = 'SQL_PRO_COMPUTE'
        } else {
          productType = 'SQL_COMPUTE'
        }
        break
      
      case 'VECTOR_SEARCH':
        productType = 'VECTOR_SEARCH_ENDPOINT'
        break
      
      case 'MODEL_SERVING':
        productType = 'SERVERLESS_REAL_TIME_INFERENCE'
        break
      
      case 'FMAPI_DATABRICKS':
        productType = 'SERVERLESS_REAL_TIME_INFERENCE'
        break
      
      case 'FMAPI_PROPRIETARY':
        productType = `${(item.fmapi_provider || 'OPENAI').toUpperCase()}_MODEL_SERVING`
        break
      
      case 'LAKEBASE':
        productType = 'DATABASE_SERVERLESS_COMPUTE'
        break
      
      default:
        productType = 'JOBS_COMPUTE'
    }
    
    // Get DBU price for this product type
    const dbuPrice = pricing[productType] || 0.20
    
    // ========================================
    // Step 3: Calculate DBU per hour based on workload type
    // ========================================
    let dbuPerHour = 0
    let monthlyDBUs = 0
    let vmCost = 0
    
    // Get instance DBU rates
    const driverDBURate = INSTANCE_DBU_RATES[item.driver_node_type || ''] || 0.5
    const workerDBURate = INSTANCE_DBU_RATES[item.worker_node_type || ''] || 0.5
    
    // Photon multiplier (only for classic compute, serverless includes Photon)
    const photonMultiplier = (!item.serverless_enabled && item.photon_enabled) ? 1.3 : 1.0
    
    // Serverless mode multiplier (performance = 2x, standard = 1x)
    const serverlessMultiplier = (item.serverless_enabled && item.serverless_mode === 'performance') ? 2 : 1
    
    switch (item.workload_type) {
      case 'ALL_PURPOSE':
      case 'JOBS':
      case 'DLT':
        if (item.serverless_enabled) {
          // Serverless compute: (driver + workers) × serverless_multiplier
          // No VM costs for serverless
          dbuPerHour = (driverDBURate + (workerDBURate * numWorkers)) * serverlessMultiplier
        } else {
          // Classic compute: (driver + workers) × photon_multiplier
          dbuPerHour = (driverDBURate + (workerDBURate * numWorkers)) * photonMultiplier
          
          // VM costs for classic compute
          const driverPricingTier = item.driver_pricing_tier || 'on_demand'
          const driverPaymentOption = item.driver_payment_option || 'NA'
          const workerPricingTier = item.worker_pricing_tier || 'spot'
          const workerPaymentOption = item.worker_payment_option || 'NA'
          
          // Driver VM cost
          const driverVMCostPerHour = getVMPrice(cloud, region, item.driver_node_type || '', driverPricingTier, driverPaymentOption)
          
          // Worker VM cost
          const workerVMCostPerHour = getVMPrice(cloud, region, item.worker_node_type || '', workerPricingTier, workerPaymentOption)
          
          // Total VM cost per hour
          const totalVMCostPerHour = driverVMCostPerHour + (workerVMCostPerHour * numWorkers)
          vmCost = totalVMCostPerHour * hoursPerMonth
        }
        monthlyDBUs = dbuPerHour * hoursPerMonth
        break
      
      case 'DBSQL':
        // DBSQL: lookup DBU per hour from warehouse size
        const warehouseDBUs = DBSQL_DBU_RATES[item.dbsql_warehouse_size || 'Small'] || 8
        dbuPerHour = warehouseDBUs * (item.dbsql_num_clusters || 1)
        monthlyDBUs = dbuPerHour * hoursPerMonth
        // No VM costs for DBSQL
        break
      
      case 'VECTOR_SEARCH':
      case 'MODEL_SERVING':
        // Serverless products: flat DBU rate based on size
        // Using default rate for now (would come from sync_product_serverless_rates)
        dbuPerHour = 2 // Default rate
        monthlyDBUs = dbuPerHour * hoursPerMonth
        break
      
      case 'LAKEBASE':
        // LAKEBASE: CU = DBU per hour (1 CU = 1 DBU)
        dbuPerHour = item.lakebase_cu || 0
        monthlyDBUs = dbuPerHour * hoursPerMonth
        break
      
      case 'FMAPI_DATABRICKS':
      case 'FMAPI_PROPRIETARY':
        // Two pricing models:
        // 1. Token-based: quantity is in millions, rate_type determines pricing
        // 2. Provisioned: quantity is hours, rate_type is provisioned_scaling or provisioned_entry
        const fmapiQuantity = item.fmapi_quantity || 0
        const isProvisioned = ['provisioned_scaling', 'provisioned_entry'].includes(item.fmapi_rate_type || '')
        
        if (isProvisioned) {
          // Provisioned throughput: Cost = hours × DBU/hour × DBU price
          // Default DBU rates for provisioned (would come from pricing tables)
          const provisionedDbuPerHour = item.fmapi_rate_type === 'provisioned_scaling' ? 200 : 50 // Example rates
          monthlyDBUs = fmapiQuantity * provisionedDbuPerHour
        } else {
          // Token-based: Cost = (quantity / 1M) × DBU per 1M tokens × DBU price
          // Default token pricing (would come from sync_product_fmapi_* tables)
          const tokenRate = item.fmapi_rate_type === 'output_token' ? 3.0 : 1.0 // DBU per million tokens
          monthlyDBUs = fmapiQuantity * tokenRate
        }
        break
      
      default:
        monthlyDBUs = 0
    }
    
    // ========================================
    // Step 4: Calculate final costs
    // ========================================
    const dbuCost = monthlyDBUs * dbuPrice
    const totalCost = dbuCost + vmCost
    
    return { monthlyDBUs, dbuCost, vmCost, totalCost }
  }
  
  // Calculate total costs
  const totalCosts = useMemo(() => {
    let totalDBUs = 0
    let totalDBUCost = 0
    let totalVMCost = 0
    let totalCost = 0
    
    lineItems.forEach(item => {
      const costs = calculateItemCost(item)
      totalDBUs += costs.monthlyDBUs
      totalDBUCost += costs.dbuCost
      totalVMCost += costs.vmCost
      totalCost += costs.totalCost
    })
    
    return { totalDBUs, totalDBUCost, totalVMCost, totalCost }
  }, [lineItems, formData.cloud, formData.region, workloadTypes, getVMPrice, workloadCosts, isCalculatingCost])
  
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
  
  const getWorkloadDisplay = (type: string) => {
    const wt = workloadTypes.find(w => w.workload_type === type)
    return wt?.display_name || type
  }
  
  const getSelectedSku = (item: LineItem) => {
    const wt = workloadTypes.find(w => w.workload_type === item.workload_type)
    if (!wt) return 'N/A'
    
    // Handle DLT workloads with edition-specific SKUs
    if (item.workload_type === 'DLT') {
      const edition = (item.dlt_edition || 'CORE').toUpperCase()
      if (item.serverless_enabled) {
        return 'DELTA_LIVE_TABLES_SERVERLESS'
      }
      if (item.photon_enabled) {
        return `DLT_${edition}_COMPUTE_(PHOTON)`
      }
      return `DLT_${edition}_COMPUTE`
    }
    
    if (item.serverless_enabled && wt.sku_product_type_serverless) {
      return wt.sku_product_type_serverless
    }
    if (item.photon_enabled && wt.sku_product_type_photon) {
      return wt.sku_product_type_photon
    }
    return wt.sku_product_type_standard || 'N/A'
  }
  
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount)
  }
  
  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('en-US', {
      maximumFractionDigits: 0
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
            {isSaving ? 'Saving...' : id ? 'Save' : 'Create'}
          </button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content - Left 2 columns */}
        <div className="lg:col-span-2 space-y-6">
          {/* Configuration Section */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="card p-5"
          >
            <h3 className="section-title flex items-center gap-2 mb-4">
              <CpuChipIcon className="w-4 h-4" />
              Configuration
            </h3>
            
            <div className="space-y-5">
              {/* Cloud Selection */}
              <div>
                <label className="block text-xs font-medium mb-2 text-[var(--text-secondary)]">Cloud Provider</label>
                <div className="grid grid-cols-3 gap-3">
                  {CLOUD_PROVIDERS.map(cloud => (
                    <button
                      key={cloud.id}
                      onClick={() => {
                        setFormData(prev => ({ 
                          ...prev, 
                          cloud: cloud.id, 
                          region: '',
                          // Reset tier if switching to Azure and current tier is 'enterprise' (not available on Azure)
                          tier: (cloud.id === 'azure' && prev.tier === 'enterprise') ? '' : prev.tier
                        }))
                        setSelectedCloud(cloud.id)
                        markAsChanged()
                      }}
                      className={clsx(
                        'relative p-4 rounded-xl border-2 transition-all text-center',
                        formData.cloud === cloud.id
                          ? 'border-orange-500 bg-orange-500/10'
                          : 'border-dashed border-[var(--border-secondary)] hover:border-orange-500/50 hover:bg-orange-500/5'
                      )}
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
                  ))}
                </div>
              </div>
              
              {/* Salesforce Selection */}
              <div className="border-t border-[var(--border-primary)] pt-5 mt-5">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-4 flex items-center gap-2">
                  <BuildingOfficeIcon className="w-4 h-4" />
                  Salesforce Context
                </h4>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Account Selection */}
                  <div>
                    <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">
                      Salesforce Account <span className="text-red-500">*</span>
                    </label>
                    <SearchableSelect
                      options={(() => {
                        // Show loading state if still loading
                        if (isLoadingSfAccounts && sfAccounts.length === 0) return []
                        // Build options from search results
                        const searchOptions = sfAccounts.map(a => ({
                          value: a.salesforce_account_id,
                          label: a.salesforce_account_name || a.salesforce_account_id
                        }))
                        // If we have a saved account that's not in search results, add it
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
                        setFormData(prev => ({ 
                          ...prev, 
                          opportunity_id: value
                        }))
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
              
              {/* Cloud & Region Config */}
              <div className="border-t border-[var(--border-primary)] pt-5 mt-5">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-4 flex items-center gap-2">
                  <CpuChipIcon className="w-4 h-4" />
                  Infrastructure
                </h4>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                      <option value="standard">Standard</option>
                      <option value="premium">Premium</option>
                      {formData.cloud !== 'azure' && (
                        <option value="enterprise">Enterprise</option>
                      )}
                    </select>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
          
          {/* Workloads List */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="space-y-4"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold flex items-center gap-2 text-[var(--text-primary)]">
                <ServerStackIcon className="w-5 h-5 text-orange-500" />
                Workloads
                <span className="ml-1 text-sm font-normal text-[var(--text-muted)]">
                  ({lineItems.length})
                </span>
              </h2>
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
                {/* Existing Workloads */}
                {lineItems.map((item, index) => {
                  const isItemLoading = calculatingCostIds.has(item.line_item_id)
                  const costs = calculateItemCost(item)
                  const isExpanded = expandedItems.has(item.line_item_id)
                  const sku = getSelectedSku(item)
                  const usageSummary = getUsageSummary(item)
                  
                  return (
                    <motion.div
                      key={item.line_item_id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.03 }}
                      className="card overflow-hidden"
                    >
                      {/* Workload Header - All details visible */}
                      <div 
                        className="p-4 cursor-pointer hover:bg-[var(--bg-hover)] transition-colors"
                        onClick={() => toggleExpand(item.line_item_id)}
                      >
                        {/* Top row: name, badges, cost, actions */}
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 rounded-lg bg-[var(--bg-tertiary)] flex items-center justify-center flex-shrink-0">
                            <CpuChipIcon className="w-5 h-5 text-orange-500" />
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <h4 className="font-semibold truncate text-[var(--text-primary)]">{item.workload_name}</h4>
                              {(item.serverless_enabled || (item.workload_type === 'DBSQL' && item.dbsql_warehouse_type === 'SERVERLESS')) && (
                                <span className="badge badge-teal">Serverless</span>
                              )}
                              {item.photon_enabled && (
                                <span className="badge badge-orange">
                                  <BoltIcon className="w-3 h-3 mr-0.5" />
                                  Photon
                                </span>
                              )}
                              {/* Show Spot Workers badge only for non-serverless compute workloads */}
                              {item.worker_pricing_tier === 'spot' && 
                               !item.serverless_enabled && 
                               ['JOBS', 'ALL_PURPOSE', 'DLT'].includes(item.workload_type || '') && (
                                <span className="badge badge-yellow">
                                  Spot Workers
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] mt-0.5">
                              <span>{getWorkloadDisplay(item.workload_type || '')}</span>
                              <span>•</span>
                              <span className="font-mono text-[var(--text-secondary)]">{sku}</span>
                            </div>
                          </div>
                          
                          {/* Cost */}
                          <div className="text-right min-w-[100px]">
                            {isItemLoading && !workloadCosts[item.line_item_id] ? (
                              <>
                                <div className="h-7 w-24 bg-[var(--bg-tertiary)] rounded animate-pulse mb-1 ml-auto" />
                                <div className="h-4 w-16 bg-[var(--bg-tertiary)] rounded animate-pulse ml-auto" />
                              </>
                            ) : (
                              <>
                                <p className="text-lg font-bold text-orange-500">{formatCurrency(costs.totalCost)}</p>
                                <p className="text-xs text-[var(--text-muted)]">{formatNumber(costs.monthlyDBUs)} DBUs/mo</p>
                              </>
                            )}
                          </div>
                          
                          {/* Actions */}
                          <div className="flex items-center gap-1">
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                handleDeleteLineItem(item)
                              }}
                              className="p-1.5 rounded-md text-[var(--text-muted)] hover:text-red-500 hover:bg-red-500/10"
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
                        
                        {/* Bottom row: Cost breakdown & config summary */}
                        <div className="mt-3 pt-3 border-t border-[var(--border-primary)] grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 text-xs">
                          <div>
                            <span className="text-[var(--text-muted)]">DBU Cost</span>
                            {isItemLoading && !workloadCosts[item.line_item_id] ? (
                              <div className="h-4 w-16 bg-[var(--bg-tertiary)] rounded animate-pulse mt-0.5" />
                            ) : (
                              <p className="font-semibold text-[var(--text-primary)]">{formatCurrency(costs.dbuCost)}</p>
                            )}
                          </div>
                          {/* Hide VM Cost for serverless workloads */}
                          {!['VECTOR_SEARCH', 'MODEL_SERVING', 'FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY', 'LAKEBASE'].includes(item.workload_type || '') && (
                            <div>
                              <span className="text-[var(--text-muted)]">VM Cost</span>
                              {isItemLoading && !workloadCosts[item.line_item_id] ? (
                                <div className="h-4 w-16 bg-[var(--bg-tertiary)] rounded animate-pulse mt-0.5" />
                              ) : (
                                <p className="font-semibold text-[var(--text-primary)]">{formatCurrency(costs.vmCost)}</p>
                              )}
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
                      </div>
                      
                      {/* Expanded: Edit Form */}
                      {isExpanded && (
                        <div className="border-t border-[var(--border-primary)] p-4 bg-[var(--bg-tertiary)]">
                          <WorkloadForm
                            estimateId={id}
                            lineItem={item}
                            onClose={() => setExpandedItems(new Set())}
                            onSave={markAsChanged}
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
        
        {/* Cost Summary Sidebar - Right column */}
        <div className="lg:col-span-1">
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.15 }}
            className="card p-5 sticky top-24"
          >
            <h3 className="section-title flex items-center gap-2 mb-5">
              <CurrencyDollarIcon className="w-4 h-4" />
              Cost Summary
              {(isCalculatingCost || (isLoadingLineItems && !lineItemsLoaded)) && (
                <div className="w-4 h-4 border-2 border-orange-500/30 border-t-orange-500 rounded-full animate-spin ml-auto" />
              )}
            </h3>
            
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
              <div className="space-y-4">
                {/* Progress indicator when calculating */}
                {isCalculatingCost && (
                  <div className="bg-[var(--bg-tertiary)] px-3 py-2 rounded-lg space-y-2">
                    <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
                      <div className="w-3 h-3 border-2 border-orange-500/30 border-t-orange-500 rounded-full animate-spin" />
                      <span>Calculating costs... ({lineItems.length - calculatingCostIds.size}/{lineItems.length} complete)</span>
                    </div>
                    {/* Progress bar */}
                    <div className="w-full h-1.5 bg-[var(--bg-secondary)] rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-orange-500 to-orange-400 transition-all duration-300 ease-out"
                        style={{ width: `${((lineItems.length - calculatingCostIds.size) / lineItems.length) * 100}%` }}
                      />
                    </div>
                  </div>
                )}
                
                {/* DBU Cost */}
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-orange-500" />
                    <span className="text-sm text-[var(--text-secondary)]">DBU Cost</span>
                  </div>
                  <span className={clsx(
                    "font-semibold",
                    isCalculatingCost ? "text-[var(--text-muted)]" : "text-[var(--text-primary)]"
                  )}>
                    {isCalculatingCost ? `~${formatCurrency(totalCosts.totalDBUCost)}` : formatCurrency(totalCosts.totalDBUCost)}
                  </span>
                </div>
                
                {/* VM Cost */}
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-orange-400" />
                    <span className="text-sm text-[var(--text-secondary)]">VM Cost</span>
                  </div>
                  <span className={clsx(
                    "font-semibold",
                    isCalculatingCost ? "text-[var(--text-muted)]" : "text-[var(--text-primary)]"
                  )}>
                    {isCalculatingCost ? `~${formatCurrency(totalCosts.totalVMCost)}` : formatCurrency(totalCosts.totalVMCost)}
                  </span>
                </div>
                
                {/* Divider */}
                <div className="border-t border-[var(--border-primary)] pt-4">
                  {/* Monthly Total */}
                  <div className="flex justify-between items-center mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-[var(--text-primary)]">Monthly Total</span>
                      {isCalculatingCost && (
                        <span className="text-xs text-orange-500 font-normal animate-pulse">
                          (calculating...)
                        </span>
                      )}
                    </div>
                    <div className="flex flex-col items-end">
                      <span className={clsx(
                        "text-2xl font-bold",
                        isCalculatingCost ? "text-orange-500/50" : "text-orange-500"
                      )}>
                        {isCalculatingCost ? `~${formatCurrency(totalCosts.totalCost)}` : formatCurrency(totalCosts.totalCost)}
                      </span>
                      {isCalculatingCost && (
                        <span className="text-[10px] text-[var(--text-muted)]">
                          {lineItems.length - calculatingCostIds.size}/{lineItems.length} calculated
                        </span>
                      )}
                    </div>
                  </div>
                  
                  {/* Annual Total */}
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-[var(--text-muted)]">Annual Total</span>
                    <span className={clsx(
                      "font-medium",
                      isCalculatingCost ? "text-[var(--text-muted)]" : "text-[var(--text-secondary)]"
                    )}>
                      {isCalculatingCost ? `~${formatCurrency(totalCosts.totalCost * 12)}` : formatCurrency(totalCosts.totalCost * 12)}
                    </span>
                  </div>
                </div>
                
                {/* DBU Summary */}
                <div className="pt-3 border-t border-[var(--border-primary)]">
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-[var(--text-muted)]">Total DBUs/month</span>
                    <span className={clsx(
                      "font-mono",
                      isCalculatingCost ? "text-[var(--text-muted)]" : "text-[var(--text-secondary)]"
                    )}>
                      {isCalculatingCost ? `~${formatNumber(totalCosts.totalDBUs)}` : formatNumber(totalCosts.totalDBUs)}
                    </span>
                  </div>
                </div>
                
                {/* Per Workload Breakdown */}
                {lineItems.length > 1 && (
                  <div className="pt-4 border-t border-[var(--border-primary)]">
                    <p className="text-xs font-medium uppercase tracking-wider mb-3 text-[var(--text-muted)]">By Workload</p>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {lineItems.map(item => {
                        const isThisItemLoading = calculatingCostIds.has(item.line_item_id)
                        const costs = calculateItemCost(item)
                        return (
                          <div key={item.line_item_id} className="flex justify-between text-sm">
                            <span className="text-[var(--text-secondary)] truncate pr-2 max-w-[140px]">{item.workload_name}</span>
                            {isThisItemLoading && !workloadCosts[item.line_item_id] ? (
                              <div className="h-4 w-16 bg-[var(--bg-tertiary)] rounded animate-pulse" />
                            ) : (
                              <span className="font-medium text-[var(--text-primary)]">{formatCurrency(costs.totalCost)}</span>
                            )}
                          </div>
                        )
                      })}
                    </div>
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
            <div className="mt-5 p-3 bg-[var(--bg-tertiary)] rounded-lg border border-[var(--border-primary)]">
              <p className="text-xs text-[var(--text-muted)]">
                <span className="font-medium text-[var(--text-secondary)]">Note:</span> Estimates based on published Databricks pricing. Actual costs may vary based on usage and negotiated discounts.
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  )
}
