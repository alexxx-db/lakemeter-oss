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
import type { CurrentUser } from '../api/client'

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
  instanceTypes: InstanceType[]
  dbsqlSizes: DBSQLSize[]
  dltEditions: DLTEdition[]
  fmapiProviders: FMAPIProvider[]
  selectedCloud: string
  selectedRegion: string
  
  // Model Serving & Foundation Models Reference Data
  modelServingGPUTypes: ModelServingGPUType[]
  fmapiDatabricksConfig: FMAPIDatabricksConfig | null
  fmapiProprietaryConfig: FMAPIProprietaryConfig | null
  
  // VM Pricing Data
  vmPricing: VMPricing[]
  vmPricingTiers: VMPricingTier[]
  vmPaymentOptions: VMPaymentOption[]
  vmPricingMap: Record<string, number> // Map of "cloud:region:instance:tier:payment" -> cost_per_hour
  
  // Actions - Auth
  fetchCurrentUser: () => Promise<void>
  clearAuthError: () => void
  
  // Actions - Estimates
  fetchEstimates: () => Promise<void>
  fetchEstimate: (id: string) => Promise<void>
  createEstimate: (estimate: Partial<Estimate>) => Promise<Estimate>
  updateEstimate: (id: string, estimate: Partial<Estimate>) => Promise<Estimate>
  deleteEstimate: (id: string) => Promise<void>
  duplicateEstimate: (id: string) => Promise<Estimate>
  setCurrentEstimate: (estimate: Estimate | null) => void
  
  // Actions - Line Items
  fetchLineItems: (estimateId: string) => Promise<void>
  createLineItem: (lineItem: Partial<LineItem> & { estimate_id: string }) => Promise<LineItem>
  updateLineItem: (id: string, lineItem: Partial<LineItem>) => Promise<LineItem>
  updateLineItemLocal: (id: string, lineItem: Partial<LineItem>) => void
  deleteLineItem: (id: string) => Promise<void>
  
  // Actions - Reference Data
  fetchReferenceData: () => Promise<void>
  fetchInstanceTypes: (cloud: string, region?: string) => Promise<void>
  fetchModelServingGPUTypes: (cloud: string) => Promise<void>
  setSelectedCloud: (cloud: string) => void
  setSelectedRegion: (region: string) => void
  
  // Actions - VM Pricing
  fetchVMPricing: (cloud: string, region?: string) => Promise<void>
  getVMPrice: (cloud: string, region: string, instanceType: string, pricingTier?: string, paymentOption?: string) => number
  
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
  
  workloadTypes: [],
  cloudProviders: [],
  instanceTypes: [],
  dbsqlSizes: [],
  dltEditions: [],
  fmapiProviders: [],
  selectedCloud: 'aws',
  selectedRegion: '',
  
  // Model Serving & Foundation Models
  modelServingGPUTypes: [],
  fmapiDatabricksConfig: null,
  fmapiProprietaryConfig: null,
  
  // VM Pricing
  vmPricing: [],
  vmPricingTiers: [],
  vmPaymentOptions: [],
  vmPricingMap: {},
  
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
  fetchEstimates: async () => {
    set({ isLoading: true, error: null })
    try {
      const estimates = await api.fetchEstimates()
      set({ estimates, isLoading: false })
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
  
  // Update line item locally without API call (for real-time cost preview)
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
        fmapiProprietaryConfig
      ] = await Promise.all([
        api.fetchWorkloadTypes(),
        api.fetchCloudProviders(),
        api.fetchDBSQLSizes(),
        api.fetchDLTEditions(),
        api.fetchFMAPIModels(),
        api.fetchVMPricingTiers(),
        api.fetchVMPaymentOptions(),
        api.fetchFMAPIDatabricksConfig(),
        api.fetchFMAPIProprietaryConfig()
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
        fmapiProprietaryConfig
      })
      
      // Fetch instance types and model serving GPU types for default cloud
      const [instanceTypes, modelServingGPUTypes] = await Promise.all([
        api.fetchInstanceTypes('aws'),
        api.fetchModelServingGPUTypes('aws')
      ])
      set({ instanceTypes, modelServingGPUTypes })
    } catch (error) {
      console.error('Failed to fetch reference data:', error)
      set({ error: 'Failed to load reference data from server' })
    }
  },
  
  fetchInstanceTypes: async (cloud, region) => {
    try {
      const instanceTypes = await api.fetchInstanceTypes(cloud, region)
      set({ instanceTypes, selectedCloud: cloud })
    } catch (error) {
      console.error('Failed to fetch instance types:', error)
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
  
  setSelectedCloud: (cloud) => {
    set({ selectedCloud: cloud })
    const region = get().selectedRegion
    get().fetchInstanceTypes(cloud, region || undefined)
    get().fetchModelServingGPUTypes(cloud)
    // Also fetch VM pricing for the new cloud
    get().fetchVMPricing(cloud, region || undefined)
  },
  
  setSelectedRegion: (region) => {
    set({ selectedRegion: region })
    const cloud = get().selectedCloud
    // Re-fetch instance types for the new region
    get().fetchInstanceTypes(cloud, region || undefined)
    // Fetch VM pricing for the selected region
    get().fetchVMPricing(cloud, region || undefined)
  },
  
  // VM Pricing
  fetchVMPricing: async (cloud, region) => {
    try {
      const vmPricing = await api.fetchVMPricing({ cloud, region })
      
      // Build a pricing map for quick lookups
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
    
    // Try exact match first
    const exactKey = `${cloud.toLowerCase()}:${region}:${instanceType}:${pricingTier}:${paymentOption}`
    if (vmPricingMap[exactKey] !== undefined) {
      return vmPricingMap[exactKey]
    }
    
    // Try without payment option
    const keyNoPayment = `${cloud.toLowerCase()}:${region}:${instanceType}:${pricingTier}:NA`
    if (vmPricingMap[keyNoPayment] !== undefined) {
      return vmPricingMap[keyNoPayment]
    }
    
    // Try any region with same cloud/instance/tier
    for (const key of Object.keys(vmPricingMap)) {
      const parts = key.split(':')
      if (parts[0] === cloud.toLowerCase() && parts[2] === instanceType && parts[3] === pricingTier) {
        return vmPricingMap[key]
      }
    }
    
    // No fallback - return 0 if not found in database
    console.warn(`VM price not found for ${cloud}/${region}/${instanceType}/${pricingTier}`)
    return 0
  },
  
  clearError: () => set({ error: null })
}))
