import axios from 'axios'
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
  VMInstanceType,
  SalesforceAccount,
  SalesforceOpportunity,
  SalesforceUseCase,
  User
} from '../types'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Response interceptor to handle authentication errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // User is not authenticated
      // When deployed to Databricks Apps, this shouldn't happen as auth is handled at the platform level
      // But for local development, we can show a helpful message
      console.error('Authentication required. Please access through Databricks Apps or set LOCAL_DEV_EMAIL.')
    }
    return Promise.reject(error)
  }
)

// Current User
export interface CurrentUser {
  user_id: string
  email: string
  full_name: string | null
  role: string | null
}

export const fetchCurrentUser = async (): Promise<CurrentUser> => {
  const { data } = await api.get('/estimates/me/info')
  return data
}

// Estimates
export const fetchEstimates = async (params?: { status?: string; cloud?: string }): Promise<EstimateListItem[]> => {
  const { data } = await api.get('/estimates/', { params })
  return data
}

export const fetchEstimate = async (id: string): Promise<Estimate> => {
  const { data } = await api.get(`/estimates/${id}`)
  return data
}

export const createEstimate = async (estimate: Partial<Estimate>): Promise<Estimate> => {
  const { data } = await api.post('/estimates/', estimate)
  return data
}

export const updateEstimate = async (id: string, estimate: Partial<Estimate>): Promise<Estimate> => {
  const { data } = await api.put(`/estimates/${id}`, estimate)
  return data
}

export const deleteEstimate = async (id: string): Promise<void> => {
  await api.delete(`/estimates/${id}`)
}

export const duplicateEstimate = async (id: string): Promise<Estimate> => {
  const { data } = await api.post(`/estimates/${id}/duplicate`)
  return data
}

// Line Items
export const fetchLineItems = async (estimateId: string): Promise<LineItem[]> => {
  const { data } = await api.get(`/line-items/estimate/${estimateId}`)
  return data
}

export const createLineItem = async (lineItem: Partial<LineItem> & { estimate_id: string }): Promise<LineItem> => {
  const { data } = await api.post('/line-items/', lineItem)
  return data
}

export const updateLineItem = async (id: string, lineItem: Partial<LineItem>): Promise<LineItem> => {
  const { data } = await api.put(`/line-items/${id}`, lineItem)
  return data
}

export const deleteLineItem = async (id: string): Promise<void> => {
  await api.delete(`/line-items/${id}`)
}

// Workload Types (from Lakebase database)
export const fetchWorkloadTypes = async (): Promise<WorkloadType[]> => {
  const { data } = await api.get('/workload-types')
  return data
}

// Reference Data
export const fetchCloudProviders = async (): Promise<CloudProvider[]> => {
  const { data } = await api.get('/reference/clouds')
  return data
}

export const fetchInstanceTypes = async (cloud: string): Promise<InstanceType[]> => {
  const { data } = await api.get(`/reference/instance-types/${cloud}`)
  return data
}

export const fetchDBSQLSizes = async (): Promise<DBSQLSize[]> => {
  const { data } = await api.get('/reference/dbsql-sizes')
  return data
}

export const fetchDLTEditions = async (): Promise<DLTEdition[]> => {
  const { data } = await api.get('/reference/dlt-editions')
  return data
}

export const fetchFMAPIModels = async (): Promise<FMAPIProvider[]> => {
  const { data } = await api.get('/reference/fmapi-models')
  return data
}

// VM Pricing (from Lakebase sync_pricing_vm_costs table)
export const fetchVMPricing = async (params: {
  cloud: string
  region?: string
  instance_type?: string
  pricing_tier?: string
}): Promise<VMPricing[]> => {
  const { data } = await api.get('/vm-pricing', { params })
  return data
}

export const fetchVMInstanceTypes = async (cloud: string, region?: string): Promise<VMInstanceType[]> => {
  const { data } = await api.get('/vm-pricing/instance-types', { params: { cloud, region } })
  return data
}

export const fetchVMPrice = async (params: {
  cloud: string
  region: string
  instance_type: string
  pricing_tier?: string
  payment_option?: string
}): Promise<{ cost_per_hour: number; currency: string; pricing_tier: string; payment_option: string; source: string }> => {
  const { data } = await api.get('/vm-pricing/price', { params })
  return data
}

export const fetchVMPricingTiers = async (): Promise<VMPricingTier[]> => {
  const { data } = await api.get('/vm-pricing/tiers')
  return data
}

export const fetchVMPaymentOptions = async (): Promise<VMPaymentOption[]> => {
  const { data } = await api.get('/vm-pricing/payment-options')
  return data
}

export const fetchVMRegions = async (cloud: string): Promise<{ region: string }[]> => {
  const { data } = await api.get('/vm-pricing/regions', { params: { cloud } })
  return data
}

// Export
export const exportEstimateToExcel = async (id: string): Promise<Blob> => {
  const { data } = await api.get(`/export/estimate/${id}/excel`, {
    responseType: 'blob'
  })
  return data
}

export const exportAllEstimatesToExcel = async (): Promise<Blob> => {
  const { data } = await api.get('/export/estimates/excel', {
    responseType: 'blob'
  })
  return data
}

// Salesforce Data
export const fetchSalesforceAccounts = async (params?: { search?: string; limit?: number }): Promise<SalesforceAccount[]> => {
  const { data } = await api.get('/salesforce/accounts', { params })
  return data
}

export const fetchSalesforceOpportunities = async (params?: { 
  account_id?: string
  search?: string
  limit?: number 
}): Promise<SalesforceOpportunity[]> => {
  const { data } = await api.get('/salesforce/opportunities', { params })
  return data
}

export const fetchSalesforceUseCases = async (params?: { 
  account_id?: string
  search?: string
  limit?: number 
}): Promise<SalesforceUseCase[]> => {
  const { data } = await api.get('/salesforce/use-cases', { params })
  return data
}

export default api
