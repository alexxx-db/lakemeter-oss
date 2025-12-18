import { create } from 'zustand'
import type { 
  Estimate, 
  EstimateListItem, 
  LineItem, 
  WorkloadType,
  CloudProvider,
  InstanceType,
  DBSQLSize,
  DLTEdition,
  FMAPIProvider,
  VMPricing,
  VMPricingTier,
  VMPaymentOption,
  ModelServingGPUType,
  FMAPIDatabricksConfig,
  FMAPIProprietaryConfig
} from '../types'
import * as api from '../api/client'
import type { 
  CurrentUser, 
  CostCalculationResponse,
  Region,
  Tier,
  DBURate,
  ServerlessMode,
  PhotonMultiplier
} from '../api/client'

interface Store {
  // Current User
  currentUser: CurrentUser | null
  isAuthenticated: boolean
  authError: string | null
  
  // Estimates
  estimates: EstimateListItem[]
  currentEstimate: Estimate | null
  lineItems: LineItem[]
  isLoading: boolean
  error: string | null
  
  // Reference Data
  workloadTypes: WorkloadType[]
  cloudProviders: CloudProvider[]
  regions: Region[]
  tiers: Tier[]
  instanceTypes: InstanceType[]
  instanceFamilies: string[]
  dbsqlSizes: DBSQLSize[]
  dbsqlWarehouseTypes: string[]
  dltEditions: DLTEdition[]
  fmapiProviders: FMAPIProvider[]
  fmapiDatabricksModels: string[]
  selectedCloud: string
  selectedRegion: string
  selectedTier: string
  
  // Model Serving & Foundation Models Reference Data
  modelServingGPUTypes: ModelServingGPUType[]
  fmapiDatabricksConfig: FMAPIDatabricksConfig | null
  fmapiProprietaryConfig: FMAPIProprietaryConfig | null
  
  // VM Pricing Data
  vmPricing: VMPricing[]
  vmPricingTiers: VMPricingTier[]
  vmPaymentOptions: VMPaymentOption[]
  vmPricingMap: Record<string, number>
  
  // DBU Rates & Pricing (NEW)
  dbuRates: DBURate[]
  dbuRatesMap: Record<string, number>  // Map of "product_type" -> dbu_price
  serverlessModes: ServerlessMode[]
  photonMultipliers: PhotonMultiplier[]
  
  // Cost Calculations (NEW)
  workloadCosts: Record<string, CostCalculationResponse>  // Map of line_item_id -> cost
  isCalculatingCost: boolean
  
  // Actions - Auth
  fetchCurrentUser: () => Promise<void>
  clearAuthError: () => void
  
  // Actions - Estimates
  fetchEstimates: (forceRefresh?: boolean) => Promise<void>
  fetchEstimate: (id: string) => Promise<void>
  createEstimate: (estimate: Partial<Estimate>) => Promise<Estimate>
  updateEstimate: (id: string, estimate: Partial<Estimate>) => Promise<Estimate>
  deleteEstimate: (id: string) => Promise<void>
  duplicateEstimate: (id: string) => Promise<Estimate>
  setCurrentEstimate: (estimate: Estimate | null) => void
  clearEstimateState: () => void
  
  // Actions - Line Items
  fetchLineItems: (estimateId: string) => Promise<void>
  createLineItem: (lineItem: Partial<LineItem> & { estimate_id: string }) => Promise<LineItem>
  updateLineItem: (id: string, lineItem: Partial<LineItem>) => Promise<LineItem>
  updateLineItemLocal: (id: string, lineItem: Partial<LineItem>) => void
  deleteLineItem: (id: string) => Promise<void>
  
  // Actions - Reference Data
  fetchReferenceData: () => Promise<void>
  fetchRegions: (cloud: string) => Promise<void>
  fetchTiers: (cloud?: string) => Promise<void>
  fetchInstanceTypes: (cloud: string, region?: string) => Promise<void>
  fetchInstanceFamilies: () => Promise<void>
  fetchModelServingGPUTypes: (cloud: string) => Promise<void>
  fetchDBSQLWarehouseTypes: () => Promise<void>
  fetchFMAPIDatabricksModels: () => Promise<void>
  setSelectedCloud: (cloud: string) => void
  setSelectedRegion: (region: string) => void
  setSelectedTier: (tier: string) => void
  
  // Actions - VM Pricing
  fetchVMPricing: (cloud: string, region?: string) => Promise<void>
  getVMPrice: (cloud: string, region: string, instanceType: string, pricingTier?: string, paymentOption?: string) => number
  
  // Actions - DBU Rates & Pricing (NEW)
  fetchDBURates: (cloud: string, region: string, tier: string) => Promise<void>
  getDBURate: (productType: string) => number
  fetchServerlessModes: () => Promise<void>
  fetchPhotonMultipliers: (cloud: string) => Promise<void>
  
  // Actions - Cost Calculation (NEW)
  calculateWorkloadCost: (lineItem: LineItem, estimateCloud: string, estimateRegion: string, estimateTier: string) => Promise<CostCalculationResponse | null>
  calculateAllWorkloadCosts: (estimateId: string) => Promise<void>
  clearWorkloadCosts: () => void
  
  // UI State
  clearError: () => void
}

export const useStore = create<Store>((set, get) => ({
  // Initial state
  currentUser: null,
  isAuthenticated: false,
  authError: null,
  
  estimates: [],
  currentEstimate: null,
  lineItems: [],
  isLoading: false,
  error: null,
  
  // Fallback workload types in case API fails
  workloadTypes: [
    { workload_type: 'JOBS', display_name: 'Jobs Compute', description: 'Batch job workloads', sku_product_type_standard: 'JOBS_COMPUTE', sku_product_type_photon: 'JOBS_COMPUTE_(PHOTON)', sku_product_type_serverless: 'JOBS_SERVERLESS_COMPUTE', show_compute_config: true, show_serverless_toggle: true, show_photon_toggle: true, show_usage_runs: true },
    { workload_type: 'ALL_PURPOSE', display_name: 'All Purpose Compute', description: 'Interactive compute', sku_product_type_standard: 'ALL_PURPOSE_COMPUTE', sku_product_type_photon: 'ALL_PURPOSE_COMPUTE_(PHOTON)', sku_product_type_serverless: 'INTERACTIVE_SERVERLESS_COMPUTE', show_compute_config: true, show_serverless_toggle: true, show_photon_toggle: true, show_usage_runs: true },
    { workload_type: 'DLT', display_name: 'Delta Live Tables', description: 'Data pipeline workloads', sku_product_type_standard: 'DLT_CORE_COMPUTE', sku_product_type_photon: 'DLT_CORE_COMPUTE_(PHOTON)', sku_product_type_serverless: 'DELTA_LIVE_TABLES_SERVERLESS', show_compute_config: true, show_serverless_toggle: true, show_photon_toggle: true, show_dlt_config: true, show_usage_runs: true },
    { workload_type: 'DBSQL', display_name: 'Databricks SQL', description: 'SQL warehouse workloads', sku_product_type_standard: 'SQL_COMPUTE', sku_product_type_photon: 'SQL_PRO_COMPUTE', sku_product_type_serverless: 'SERVERLESS_SQL_COMPUTE', show_dbsql_config: true, show_usage_runs: true },
    { workload_type: 'VECTOR_SEARCH', display_name: 'Vector Search', description: 'Vector search endpoints', sku_product_type_standard: 'VECTOR_SEARCH_ENDPOINT', show_vector_search_mode: true },
    { workload_type: 'MODEL_SERVING', display_name: 'Model Serving', description: 'Real-time ML inference', sku_product_type_standard: 'SERVERLESS_REAL_TIME_INFERENCE', show_model_serving_config: true },
    { workload_type: 'FMAPI_DATABRICKS', display_name: 'Foundation Models (Databricks)', description: 'Databricks foundation model APIs', sku_product_type_standard: 'FOUNDATION_MODEL_TRAINING', show_fmapi_config: true },
    { workload_type: 'FMAPI_PROPRIETARY', display_name: 'Foundation Models (Proprietary)', description: 'External foundation model APIs', sku_product_type_standard: 'FOUNDATION_MODEL_TRAINING', show_fmapi_config: true },
    { workload_type: 'LAKEBASE', display_name: 'Lakebase', description: 'Database workloads', sku_product_type_standard: 'DATABASE_SERVERLESS_COMPUTE', show_lakebase_config: true },
  ] as WorkloadType[],
  cloudProviders: [],
  regions: [],
  tiers: [],
  instanceTypes: [],
  instanceFamilies: [],
  dbsqlSizes: [],
  dbsqlWarehouseTypes: [],
  dltEditions: [],
  fmapiProviders: [],
  fmapiDatabricksModels: [],
  selectedCloud: 'aws',
  selectedRegion: '',
  selectedTier: 'PREMIUM',
  
  // Model Serving & Foundation Models
  modelServingGPUTypes: [],
  fmapiDatabricksConfig: null,
  fmapiProprietaryConfig: null,
  
  // VM Pricing
  vmPricing: [],
  vmPricingTiers: [],
  vmPaymentOptions: [],
  vmPricingMap: {},
  
  // DBU Rates & Pricing
  dbuRates: [],
  dbuRatesMap: {},
  serverlessModes: [],
  photonMultipliers: [],
  
  // Cost Calculations
  workloadCosts: {},
  isCalculatingCost: false,
  
  // Caching
  _regionsCache: {} as Record<string, { data: any[]; timestamp: number }>,
  _dbuRatesCache: {} as Record<string, { data: any; timestamp: number }>,
  _instanceTypesCache: {} as Record<string, { data: any[]; timestamp: number }>,
  _estimatesLastFetch: 0,
  
  // Auth Actions
  fetchCurrentUser: async () => {
    try {
      const user = await api.fetchCurrentUser()
      set({ currentUser: user, isAuthenticated: true, authError: null })
    } catch (error: unknown) {
      const errorMessage = error instanceof Error && 'response' in error 
        ? (error as { response?: { status?: number } }).response?.status === 401
          ? 'Please access through Databricks Apps or set LOCAL_DEV_EMAIL environment variable.'
          : 'Failed to authenticate'
        : 'Failed to authenticate'
      set({ currentUser: null, isAuthenticated: false, authError: errorMessage })
    }
  },
  
  clearAuthError: () => set({ authError: null }),
  
  // Estimates
  fetchEstimates: async (forceRefresh = false) => {
    const currentEstimates = get().estimates
    const lastFetchTime = (get() as any)._estimatesLastFetch || 0
    const STALE_TIME = 30 * 1000 // 30 seconds before considering stale
    
    // If we have cached data and not forcing refresh, show it immediately
    // and fetch in background if stale
    if (currentEstimates.length > 0 && !forceRefresh) {
      const isStale = Date.now() - lastFetchTime > STALE_TIME
      
      if (isStale) {
        // Background refresh - don't show loading spinner
        try {
          const estimates = await api.fetchEstimates()
          set((state: any) => ({ 
            estimates,
            _estimatesLastFetch: Date.now()
          }))
        } catch (error) {
          console.error('Background refresh failed:', error)
        }
      }
      return // Don't show loading - we have cached data
    }
    
    // No cached data or force refresh - show loading
    set({ isLoading: true, error: null })
    try {
      const estimates = await api.fetchEstimates()
      set((state: any) => ({ 
        estimates, 
        isLoading: false,
        _estimatesLastFetch: Date.now()
      }))
    } catch (error) {
      set({ error: 'Failed to fetch estimates', isLoading: false })
    }
  },
  
  fetchEstimate: async (id: string) => {
    set({ isLoading: true, error: null })
    try {
      const estimate = await api.fetchEstimate(id)
      set({ currentEstimate: estimate, isLoading: false })
    } catch (error) {
      set({ error: 'Failed to fetch estimate', isLoading: false })
    }
  },
  
  createEstimate: async (estimate) => {
    set({ isLoading: true, error: null })
    try {
      const newEstimate = await api.createEstimate(estimate)
      set((state) => ({
        estimates: [{ ...newEstimate, line_item_count: 0 } as EstimateListItem, ...state.estimates],
        currentEstimate: newEstimate,
        isLoading: false
      }))
      return newEstimate
    } catch (error) {
      set({ error: 'Failed to create estimate', isLoading: false })
      throw error
    }
  },
  
  updateEstimate: async (id, estimate) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await api.updateEstimate(id, estimate)
      set((state) => ({
        estimates: state.estimates.map((e) => 
          e.estimate_id === id ? { ...e, ...updated } : e
        ),
        currentEstimate: state.currentEstimate?.estimate_id === id 
          ? { ...state.currentEstimate, ...updated }
          : state.currentEstimate,
        isLoading: false
      }))
      return updated
    } catch (error) {
      set({ error: 'Failed to update estimate', isLoading: false })
      throw error
    }
  },
  
  deleteEstimate: async (id) => {
    set({ isLoading: true, error: null })
    try {
      await api.deleteEstimate(id)
      set((state) => ({
        estimates: state.estimates.filter((e) => e.estimate_id !== id),
        currentEstimate: state.currentEstimate?.estimate_id === id 
          ? null 
          : state.currentEstimate,
        isLoading: false
      }))
    } catch (error) {
      set({ error: 'Failed to delete estimate', isLoading: false })
      throw error
    }
  },
  
  duplicateEstimate: async (id) => {
    set({ isLoading: true, error: null })
    try {
      const newEstimate = await api.duplicateEstimate(id)
      set((state) => ({
        estimates: [{ ...newEstimate, line_item_count: state.estimates.find(e => e.estimate_id === id)?.line_item_count || 0 } as EstimateListItem, ...state.estimates],
        isLoading: false
      }))
      return newEstimate
    } catch (error) {
      set({ error: 'Failed to duplicate estimate', isLoading: false })
      throw error
    }
  },
  
  setCurrentEstimate: (estimate) => set({ currentEstimate: estimate }),
  
  clearEstimateState: () => set({ 
    currentEstimate: null, 
    lineItems: [], 
    workloadCosts: {}
  }),

  // Line Items
  fetchLineItems: async (estimateId) => {
    set({ isLoading: true, error: null })
    try {
      const lineItems = await api.fetchLineItems(estimateId)
      set({ lineItems, isLoading: false })
    } catch (error) {
      set({ error: 'Failed to fetch line items', isLoading: false })
    }
  },
  
  createLineItem: async (lineItem) => {
    set({ isLoading: true, error: null })
    try {
      const newItem = await api.createLineItem(lineItem)
      set((state) => ({
        lineItems: [...state.lineItems, newItem],
        isLoading: false
      }))
      return newItem
    } catch (error) {
      set({ error: 'Failed to create line item', isLoading: false })
      throw error
    }
  },
  
  updateLineItem: async (id, lineItem) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await api.updateLineItem(id, lineItem)
      set((state) => ({
        lineItems: state.lineItems.map((item) => 
          item.line_item_id === id ? { ...item, ...updated } : item
        ),
        isLoading: false
      }))
      return updated
    } catch (error) {
      set({ error: 'Failed to update line item', isLoading: false })
      throw error
    }
  },
  
  updateLineItemLocal: (id, lineItem) => {
    set((state) => ({
      lineItems: state.lineItems.map((item) => 
        item.line_item_id === id ? { ...item, ...lineItem } : item
      )
    }))
  },
  
  deleteLineItem: async (id) => {
    set({ isLoading: true, error: null })
    try {
      await api.deleteLineItem(id)
      set((state) => ({
        lineItems: state.lineItems.filter((item) => item.line_item_id !== id),
        workloadCosts: Object.fromEntries(
          Object.entries(state.workloadCosts).filter(([key]) => key !== id)
        ),
        isLoading: false
      }))
    } catch (error) {
      set({ error: 'Failed to delete line item', isLoading: false })
      throw error
    }
  },
  
  // Reference Data
  fetchReferenceData: async () => {
    try {
      const [
        workloadTypes, 
        cloudProviders, 
        dbsqlSizes, 
        dltEditions, 
        fmapiProviders, 
        vmPricingTiers, 
        vmPaymentOptions,
        fmapiDatabricksConfig,
        fmapiProprietaryConfig,
        serverlessModes
      ] = await Promise.all([
        api.fetchWorkloadTypes(),
        api.fetchCloudProviders(),
        api.fetchDBSQLSizes(),
        api.fetchDLTEditions(),
        api.fetchFMAPIModels(),
        api.fetchVMPricingTiers(),
        api.fetchVMPaymentOptions(),
        api.fetchFMAPIDatabricksConfig(),
        api.fetchFMAPIProprietaryConfig(),
        api.fetchServerlessModes()
      ])
      
      set({ 
        workloadTypes,
        cloudProviders, 
        dbsqlSizes, 
        dltEditions, 
        fmapiProviders,
        vmPricingTiers,
        vmPaymentOptions,
        fmapiDatabricksConfig,
        fmapiProprietaryConfig,
        serverlessModes
      })
      
      // Fetch cloud-specific data for default cloud (AWS)
      const defaultCloud = 'aws'
      const [instanceTypes, modelServingGPUTypes, regions, photonMultipliers] = await Promise.all([
        api.fetchInstanceTypes(defaultCloud),
        api.fetchModelServingGPUTypes(defaultCloud),
        api.fetchRegions(defaultCloud),
        api.fetchPhotonMultipliers(defaultCloud).catch(() => [])
      ])
      set({ instanceTypes, modelServingGPUTypes, regions, photonMultipliers })
      
      // Also try to fetch instance families and DBSQL warehouse types
      try {
        const [instanceFamilies, dbsqlWarehouseTypes, fmapiDatabricksModels] = await Promise.all([
          api.fetchInstanceFamilies(),
          api.fetchDBSQLWarehouseTypes(),
          api.fetchFMAPIDatabricksModelsList()
        ])
        set({ instanceFamilies, dbsqlWarehouseTypes, fmapiDatabricksModels })
      } catch (e) {
        console.warn('Some reference data endpoints not available:', e)
      }
    } catch (error) {
      console.error('Failed to fetch reference data:', error)
      set({ error: 'Failed to load reference data from server' })
    }
  },
  
  fetchRegions: async (cloud) => {
    const cacheKey = cloud.toLowerCase()
    const cache = (get() as any)._regionsCache?.[cacheKey]
    const CACHE_TTL = 5 * 60 * 1000 // 5 minutes
    
    // Return cached data if fresh
    if (cache && Date.now() - cache.timestamp < CACHE_TTL) {
      set({ regions: cache.data })
      return
    }
    
    try {
      const regions = await api.fetchRegions(cloud)
      set((state: any) => ({ 
        regions,
        _regionsCache: {
          ...state._regionsCache,
          [cacheKey]: { data: regions, timestamp: Date.now() }
        }
      }))
    } catch (error) {
      console.error('Failed to fetch regions:', error)
    }
  },
  
  fetchTiers: async (cloud) => {
    try {
      const tiers = await api.fetchTiers(cloud)
      set({ tiers })
    } catch (error) {
      console.error('Failed to fetch tiers:', error)
    }
  },
  
  fetchInstanceTypes: async (cloud, region) => {
    const cacheKey = `${cloud.toLowerCase()}-${region || 'all'}`
    const cache = (get() as any)._instanceTypesCache?.[cacheKey]
    const CACHE_TTL = 10 * 60 * 1000 // 10 minutes
    
    // Return cached data if fresh
    if (cache && Date.now() - cache.timestamp < CACHE_TTL) {
      set({ instanceTypes: cache.data, selectedCloud: cloud })
      return
    }
    
    try {
      const instanceTypes = await api.fetchInstanceTypes(cloud, region)
      set((state: any) => ({ 
        instanceTypes, 
        selectedCloud: cloud,
        _instanceTypesCache: {
          ...state._instanceTypesCache,
          [cacheKey]: { data: instanceTypes, timestamp: Date.now() }
        }
      }))
    } catch (error) {
      console.error('Failed to fetch instance types:', error)
    }
  },
  
  fetchInstanceFamilies: async () => {
    try {
      const instanceFamilies = await api.fetchInstanceFamilies()
      set({ instanceFamilies })
    } catch (error) {
      console.error('Failed to fetch instance families:', error)
    }
  },
  
  fetchModelServingGPUTypes: async (cloud) => {
    try {
      const modelServingGPUTypes = await api.fetchModelServingGPUTypes(cloud)
      set({ modelServingGPUTypes })
    } catch (error) {
      console.error('Failed to fetch model serving GPU types:', error)
    }
  },
  
  fetchDBSQLWarehouseTypes: async () => {
    try {
      const dbsqlWarehouseTypes = await api.fetchDBSQLWarehouseTypes()
      set({ dbsqlWarehouseTypes })
    } catch (error) {
      console.error('Failed to fetch DBSQL warehouse types:', error)
    }
  },
  
  fetchFMAPIDatabricksModels: async () => {
    try {
      const fmapiDatabricksModels = await api.fetchFMAPIDatabricksModelsList()
      set({ fmapiDatabricksModels })
    } catch (error) {
      console.error('Failed to fetch FMAPI Databricks models:', error)
    }
  },
  
  setSelectedCloud: (cloud) => {
    set({ selectedCloud: cloud })
    const region = get().selectedRegion
    get().fetchRegions(cloud)
    get().fetchInstanceTypes(cloud, region || undefined)
    get().fetchModelServingGPUTypes(cloud)
    get().fetchVMPricing(cloud, region || undefined)
    get().fetchPhotonMultipliers(cloud)
  },
  
  setSelectedRegion: (region) => {
    set({ selectedRegion: region })
    const cloud = get().selectedCloud
    const tier = get().selectedTier
    get().fetchInstanceTypes(cloud, region || undefined)
    get().fetchVMPricing(cloud, region || undefined)
    // Fetch DBU rates when region changes
    if (region) {
      get().fetchDBURates(cloud, region, tier)
    }
  },
  
  setSelectedTier: (tier) => {
    set({ selectedTier: tier })
    const cloud = get().selectedCloud
    const region = get().selectedRegion
    // Fetch DBU rates when tier changes
    if (region) {
      get().fetchDBURates(cloud, region, tier)
    }
  },
  
  // VM Pricing
  fetchVMPricing: async (cloud, region) => {
    try {
      const vmPricing = await api.fetchVMPricing({ cloud, region })
      
      const vmPricingMap: Record<string, number> = {}
      vmPricing.forEach(p => {
        const key = `${p.cloud.toLowerCase()}:${p.region}:${p.instance_type}:${p.pricing_tier}:${p.payment_option}`
        vmPricingMap[key] = p.cost_per_hour
      })
      
      set({ vmPricing, vmPricingMap })
    } catch (error) {
      console.error('Failed to fetch VM pricing:', error)
    }
  },
  
  getVMPrice: (cloud, region, instanceType, pricingTier = 'on_demand', paymentOption = 'NA') => {
    const { vmPricingMap } = get()
    
    const exactKey = `${cloud.toLowerCase()}:${region}:${instanceType}:${pricingTier}:${paymentOption}`
    if (vmPricingMap[exactKey] !== undefined) {
      return vmPricingMap[exactKey]
    }
    
    const keyNoPayment = `${cloud.toLowerCase()}:${region}:${instanceType}:${pricingTier}:NA`
    if (vmPricingMap[keyNoPayment] !== undefined) {
      return vmPricingMap[keyNoPayment]
    }
    
    for (const key of Object.keys(vmPricingMap)) {
      const parts = key.split(':')
      if (parts[0] === cloud.toLowerCase() && parts[2] === instanceType && parts[3] === pricingTier) {
        return vmPricingMap[key]
      }
    }
    
    console.warn(`VM price not found for ${cloud}/${region}/${instanceType}/${pricingTier}`)
    return 0
  },
  
  // DBU Rates & Pricing
  fetchDBURates: async (cloud, region, tier) => {
    const cacheKey = `${cloud}-${region}-${tier}`.toLowerCase()
    const cache = (get() as any)._dbuRatesCache?.[cacheKey]
    const CACHE_TTL = 10 * 60 * 1000 // 10 minutes
    
    // Return cached data if fresh
    if (cache && Date.now() - cache.timestamp < CACHE_TTL) {
      set({ dbuRates: cache.data.dbuRates, dbuRatesMap: cache.data.dbuRatesMap })
      return
    }
    
    try {
      const dbuRates = await api.fetchDBURates({ cloud, region, tier })
      
      const dbuRatesMap: Record<string, number> = {}
      dbuRates.forEach(rate => {
        dbuRatesMap[rate.product_type] = rate.dbu_price
      })
      
      set((state: any) => ({ 
        dbuRates, 
        dbuRatesMap,
        _dbuRatesCache: {
          ...state._dbuRatesCache,
          [cacheKey]: { data: { dbuRates, dbuRatesMap }, timestamp: Date.now() }
        }
      }))
    } catch (error) {
      console.error('Failed to fetch DBU rates:', error)
    }
  },
  
  getDBURate: (productType) => {
    const { dbuRatesMap } = get()
    return dbuRatesMap[productType] || 0
  },
  
  fetchServerlessModes: async () => {
    try {
      const serverlessModes = await api.fetchServerlessModes()
      set({ serverlessModes })
    } catch (error) {
      console.error('Failed to fetch serverless modes:', error)
    }
  },
  
  fetchPhotonMultipliers: async (cloud) => {
    try {
      const photonMultipliers = await api.fetchPhotonMultipliers(cloud)
      set({ photonMultipliers })
    } catch (error) {
      console.error('Failed to fetch photon multipliers:', error)
    }
  },
  
  // Cost Calculation
  calculateWorkloadCost: async (lineItem, estimateCloud, estimateRegion, estimateTier) => {
    if (!lineItem.workload_type || !estimateCloud || !estimateRegion || !estimateTier) {
      return null
    }
    
    set({ isCalculatingCost: true })
    
    try {
      // Build the request parameters based on workload type
      const baseParams = {
        cloud: estimateCloud.toUpperCase(),
        region: estimateRegion,
        tier: estimateTier.toUpperCase()
      }
      
      let result: CostCalculationResponse | null = null
      
      switch (lineItem.workload_type) {
        case 'JOBS':
        case 'ALL_PURPOSE':
          if (lineItem.serverless_enabled) {
            result = await api.calculateWorkloadCost(lineItem.workload_type, true, {
              ...baseParams,
              driver_node_type: lineItem.driver_node_type || 'm5.xlarge',
              worker_node_type: lineItem.worker_node_type || 'm5.xlarge',
              num_workers: lineItem.num_workers || 1,
              serverless_mode: lineItem.serverless_mode || 'standard',
              runs_per_day: lineItem.runs_per_day,
              avg_runtime_minutes: lineItem.avg_runtime_minutes,
              days_per_month: lineItem.days_per_month,
              hours_per_month: lineItem.hours_per_month
            })
          } else {
            const driverTier = lineItem.driver_pricing_tier || 'on_demand'
            const workerTier = lineItem.worker_pricing_tier || 'spot'
            
            // Payment option is "NA" for on_demand/spot, or the actual payment option for reserved
            const driverPayment = (driverTier === 'on_demand' || driverTier === 'spot') 
              ? 'NA' 
              : (lineItem.driver_payment_option || 'NA')
            const workerPayment = (workerTier === 'on_demand' || workerTier === 'spot')
              ? 'NA'
              : (lineItem.worker_payment_option || 'NA')
            
            result = await api.calculateWorkloadCost(lineItem.workload_type, false, {
              ...baseParams,
              driver_node_type: lineItem.driver_node_type || 'm5.xlarge',
              worker_node_type: lineItem.worker_node_type || 'm5.xlarge',
              num_workers: lineItem.num_workers || 1,
              photon_enabled: lineItem.photon_enabled || false,
              driver_pricing_tier: driverTier,
              worker_pricing_tier: workerTier,
              driver_payment_option: driverPayment,
              worker_payment_option: workerPayment,
              runs_per_day: lineItem.runs_per_day,
              avg_runtime_minutes: lineItem.avg_runtime_minutes,
              days_per_month: lineItem.days_per_month,
              hours_per_month: lineItem.hours_per_month
            })
          }
          break
          
        case 'DLT':
          if (lineItem.serverless_enabled) {
            result = await api.calculateDLTServerless({
              ...baseParams,
              driver_node_type: lineItem.driver_node_type || 'm5.xlarge',
              worker_node_type: lineItem.worker_node_type || 'm5.xlarge',
              num_workers: lineItem.num_workers || 1,
              serverless_mode: lineItem.serverless_mode || 'standard',
              runs_per_day: lineItem.runs_per_day,
              avg_runtime_minutes: lineItem.avg_runtime_minutes,
              days_per_month: lineItem.days_per_month,
              hours_per_month: lineItem.hours_per_month
            })
          } else {
            const dltDriverTier = lineItem.driver_pricing_tier || 'on_demand'
            const dltWorkerTier = lineItem.worker_pricing_tier || 'spot'
            const dltDriverPayment = (dltDriverTier === 'on_demand' || dltDriverTier === 'spot')
              ? 'NA'
              : (lineItem.driver_payment_option || 'NA')
            const dltWorkerPayment = (dltWorkerTier === 'on_demand' || dltWorkerTier === 'spot')
              ? 'NA'
              : (lineItem.worker_payment_option || 'NA')
            
            result = await api.calculateDLTClassic({
              ...baseParams,
              dlt_edition: lineItem.dlt_edition || 'CORE',
              photon_enabled: lineItem.photon_enabled || false,
              driver_node_type: lineItem.driver_node_type || 'm5.xlarge',
              worker_node_type: lineItem.worker_node_type || 'm5.xlarge',
              num_workers: lineItem.num_workers || 1,
              driver_pricing_tier: dltDriverTier,
              worker_pricing_tier: dltWorkerTier,
              driver_payment_option: dltDriverPayment,
              worker_payment_option: dltWorkerPayment,
              runs_per_day: lineItem.runs_per_day,
              avg_runtime_minutes: lineItem.avg_runtime_minutes,
              days_per_month: lineItem.days_per_month,
              hours_per_month: lineItem.hours_per_month
            })
          }
          break
          
        case 'DBSQL':
          const warehouseType = lineItem.dbsql_warehouse_type?.toUpperCase() || 'SERVERLESS'
          if (warehouseType === 'SERVERLESS') {
            result = await api.calculateDBSQLServerless({
              ...baseParams,
              warehouse_size: lineItem.dbsql_warehouse_size || 'Medium',
              num_clusters: lineItem.dbsql_num_clusters || 1,
              runs_per_day: lineItem.runs_per_day || 1,
              avg_runtime_minutes: lineItem.avg_runtime_minutes || 30,
              days_per_month: lineItem.days_per_month || 22,
              hours_per_month: lineItem.hours_per_month
            })
          } else {
            const dbsqlVMTier = lineItem.dbsql_vm_pricing_tier || 'on_demand'
            const dbsqlVMPayment = (dbsqlVMTier === 'on_demand' || dbsqlVMTier === 'spot')
              ? 'NA'
              : (lineItem.dbsql_vm_payment_option || 'NA')
            
            result = await api.calculateDBSQLClassicPro({
              ...baseParams,
              warehouse_type: warehouseType,
              warehouse_size: lineItem.dbsql_warehouse_size || 'Medium',
              num_clusters: lineItem.dbsql_num_clusters || 1,
              vm_pricing_tier: dbsqlVMTier,
              vm_payment_option: dbsqlVMPayment,
              runs_per_day: lineItem.runs_per_day || 1,
              avg_runtime_minutes: lineItem.avg_runtime_minutes || 30,
              days_per_month: lineItem.days_per_month || 22,
              hours_per_month: lineItem.hours_per_month
            })
          }
          break
          
        case 'VECTOR_SEARCH':
          result = await api.calculateVectorSearch({
            ...baseParams,
            mode: lineItem.vector_search_mode || 'standard',
            vector_capacity_millions: lineItem.vector_capacity_millions || 1,
            hours_per_month: lineItem.hours_per_month || 730
          })
          break
          
        case 'MODEL_SERVING':
          result = await api.calculateModelServing({
            ...baseParams,
            gpu_type: lineItem.model_serving_gpu_type || 'cpu',
            hours_per_month: lineItem.hours_per_month || 730
          })
          break
          
        case 'FMAPI_DATABRICKS':
          result = await api.calculateFMAPIDatabricks({
            ...baseParams,
            model: lineItem.fmapi_model || 'llama-3-3-70b',
            rate_type: lineItem.fmapi_rate_type || 'input_token',
            quantity: lineItem.fmapi_quantity || 1000000
          })
          break
          
        case 'FMAPI_PROPRIETARY':
          result = await api.calculateFMAPIProprietary({
            ...baseParams,
            provider: lineItem.fmapi_provider || 'anthropic',
            model: lineItem.fmapi_model || 'claude-sonnet-4-5',
            endpoint_type: lineItem.fmapi_endpoint_type || 'global',
            context_length: lineItem.fmapi_context_length || 'all',
            rate_type: lineItem.fmapi_rate_type || 'input_token',
            quantity: lineItem.fmapi_quantity || 1000000
          })
          break
          
        case 'LAKEBASE':
          result = await api.calculateLakebase({
            ...baseParams,
            cu_size: lineItem.lakebase_cu || 2,
            num_nodes: lineItem.lakebase_ha_nodes || 1,
            hours_per_month: lineItem.hours_per_month || 730
          })
          break
      }
      
      if (result) {
        set((state) => ({
          workloadCosts: {
            ...state.workloadCosts,
            [lineItem.line_item_id]: result
          },
          isCalculatingCost: false
        }))
      }
      
      return result
    } catch (error) {
      console.error('Failed to calculate workload cost:', error)
      set({ isCalculatingCost: false })
      return null
    }
  },
  
  calculateAllWorkloadCosts: async (estimateId) => {
    const { lineItems, currentEstimate } = get()
    
    if (!currentEstimate) return
    
    const estimateCloud = currentEstimate.cloud || 'AWS'
    const estimateRegion = currentEstimate.region || 'us-east-1'
    const estimateTier = currentEstimate.tier || 'PREMIUM'
    
    const estimateLineItems = lineItems.filter(li => li.estimate_id === estimateId)
    
    // Calculate costs for all line items in parallel
    await Promise.all(
      estimateLineItems.map(lineItem => 
        get().calculateWorkloadCost(lineItem, estimateCloud, estimateRegion, estimateTier)
      )
    )
  },
  
  clearWorkloadCosts: () => set({ workloadCosts: {} }),
  
  clearError: () => set({ error: null })
}))
