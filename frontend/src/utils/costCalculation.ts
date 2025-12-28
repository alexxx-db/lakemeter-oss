/**
 * Cost Calculation Utilities
 * Shared logic for calculating workload costs locally (no API calls)
 * Used for instant feedback in both Calculator.tsx and WorkloadForm.tsx
 */

import type { LineItem, InstanceType, DBSQLSize, ModelServingGPUType } from '../types'
import type { VectorSearchMode, PhotonMultiplier } from '../api/client'

// Fallback DBU rates if fetched data not available ($/DBU)
// These should match the actual Databricks pricing
export const DEFAULT_DBU_PRICING: Record<string, Record<string, number>> = {
  aws: {
    'JOBS_COMPUTE': 0.15,
    'JOBS_COMPUTE_(PHOTON)': 0.15,  // Photon doesn't change $/DBU, only DBU consumption
    'JOBS_SERVERLESS_COMPUTE': 0.39,  // Serverless has higher $/DBU
    'ALL_PURPOSE_COMPUTE': 0.40,
    'ALL_PURPOSE_COMPUTE_(PHOTON)': 0.40,
    'INTERACTIVE_SERVERLESS_COMPUTE': 0.70,
    'DLT_CORE_COMPUTE': 0.20,
    'DLT_CORE_COMPUTE_(PHOTON)': 0.20,
    'DLT_PRO_COMPUTE': 0.25,
    'DLT_PRO_COMPUTE_(PHOTON)': 0.25,
    'DLT_ADVANCED_COMPUTE': 0.36,
    'DLT_ADVANCED_COMPUTE_(PHOTON)': 0.36,
    'DELTA_LIVE_TABLES_SERVERLESS': 0.30,
    'SQL_COMPUTE': 0.22,
    'SQL_PRO_COMPUTE': 0.55,
    'SERVERLESS_SQL_COMPUTE': 0.70,
    'VECTOR_SEARCH_ENDPOINT': 0.40,
    'SERVERLESS_REAL_TIME_INFERENCE': 0.07,
    'OPENAI_MODEL_SERVING': 0.07,
    'ANTHROPIC_MODEL_SERVING': 0.07,
    'GOOGLE_MODEL_SERVING': 0.07,
    'DATABASE_SERVERLESS_COMPUTE': 0.15,
  }
}

// Fallback DBSQL DBU rates by size
export const DBSQL_DBU_RATES: Record<string, number> = {
  '2X-Small': 4,
  'X-Small': 6,
  'Small': 12,
  'Medium': 24,
  'Large': 40,
  'X-Large': 80,
  '2X-Large': 144,
  '3X-Large': 272,
  '4X-Large': 528,
}

export interface CostBreakdown {
  monthlyDBUs: number
  dbuCost: number
  vmCost: number
  totalCost: number
}

export interface CostCalculationContext {
  cloud: string
  region: string
  dbuRatesMap: Record<string, number>
  instanceTypes: InstanceType[]
  dbsqlSizes: DBSQLSize[]
  photonMultipliers: PhotonMultiplier[]
  modelServingGPUTypes: ModelServingGPUType[]
  vectorSearchModes: VectorSearchMode[]
  getVMPrice: (cloud: string, region: string, instanceType: string, pricingTier: string, paymentOption: string) => number
  getFMAPIDatabricksRate: (model: string, rateType: string) => { dbu_per_1M_tokens?: number, dbu_per_hour?: number } | null
  getFMAPIProprietaryRate: (provider: string, model: string, rateType: string) => { dbu_per_1M_tokens?: number, dbu_per_hour?: number } | null
  getVectorSearchRate: (mode: string) => { dbu_per_hour?: number, input_divisor?: number } | null
}

/**
 * Calculate cost for a workload item locally
 * This is the same logic used in Calculator.tsx for consistency
 */
export function calculateWorkloadCost(
  item: Partial<LineItem>,
  context: CostCalculationContext
): CostBreakdown {
  const { cloud, region, dbuRatesMap, instanceTypes, dbsqlSizes, photonMultipliers, modelServingGPUTypes, getVMPrice, getFMAPIDatabricksRate, getFMAPIProprietaryRate, getVectorSearchRate } = context
  
  // If no region selected, return zero costs
  if (!region) {
    return { monthlyDBUs: 0, dbuCost: 0, vmCost: 0, totalCost: 0 }
  }
  
  // Try to use dynamic DBU rates first, fall back to hardcoded
  const pricing = Object.keys(dbuRatesMap).length > 0 ? dbuRatesMap : (DEFAULT_DBU_PRICING[cloud] || DEFAULT_DBU_PRICING.aws)
  const numWorkers = item.num_workers || 0
  
  // ========================================
  // Step 1: Calculate hours per month
  // ========================================
  let hoursPerMonth = 0
  if (item.workload_type !== 'FMAPI_DATABRICKS' && item.workload_type !== 'FMAPI_PROPRIETARY') {
    if (item.hours_per_month) {
      hoursPerMonth = item.hours_per_month
    } else if (item.runs_per_day && item.avg_runtime_minutes) {
      hoursPerMonth = (item.runs_per_day * (item.avg_runtime_minutes / 60)) * (item.days_per_month || 30)
    }
  }
  
  // ========================================
  // Step 2: Determine product_type_for_pricing (SKU)
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
  console.log(`[LiveEstimate] productType=${productType}, dbuPrice=${dbuPrice}, serverless=${item.serverless_enabled}, photon=${item.photon_enabled}`)
  
  // ========================================
  // Step 3: Calculate DBU per hour based on workload type
  // ========================================
  let dbuPerHour = 0
  let monthlyDBUs = 0
  let vmCost = 0
  
  // Get instance DBU rates from fetched instanceTypes
  const driverInstance = instanceTypes.find(it => it.id === item.driver_node_type || it.name === item.driver_node_type)
  const workerInstance = instanceTypes.find(it => it.id === item.worker_node_type || it.name === item.worker_node_type)
  const driverDBURate = driverInstance?.dbu_rate || 0.5
  const workerDBURate = workerInstance?.dbu_rate || 0.5
  
  // Get photon multiplier from fetched photonMultipliers
  // NOTE: For serverless workloads, photon is ALWAYS enabled (built-in)
  const getPhotonMultiplier = () => {
    // For serverless, photon is always enabled - use multiplier
    // For classic, only apply if photon is explicitly enabled
    if (!item.serverless_enabled && !item.photon_enabled) return 1.0
    
    // Try to get from fetched data
    const baseSKUType = productType.replace('_(PHOTON)', '').replace('_SERVERLESS', '')
    const multiplierEntry = photonMultipliers.find(pm => 
      pm.sku_type === baseSKUType || 
      pm.sku_type === productType ||
      pm.sku_type?.includes(item.workload_type || '')
    )
    return multiplierEntry?.multiplier || 2.0  // Default to 2.0 (standard photon multiplier)
  }
  const photonMultiplier = getPhotonMultiplier()
  
  // Serverless mode multiplier
  const serverlessMultiplier = (item.serverless_enabled && item.serverless_mode === 'performance') ? 2 : 1
  
  switch (item.workload_type) {
    case 'ALL_PURPOSE':
    case 'JOBS':
      if (item.serverless_enabled) {
        // Serverless: DBU/Hour = base_dbu_rate × photon_multiplier (always on) × serverless_multiplier
        // Photon is ALWAYS enabled in serverless (built-in)
        dbuPerHour = (driverDBURate + (workerDBURate * numWorkers)) * photonMultiplier * serverlessMultiplier
      } else {
        // Classic: DBU/Hour = (driver_dbu_rate + worker_dbu_rate × num_workers) × photon_multiplier
        dbuPerHour = (driverDBURate + (workerDBURate * numWorkers)) * photonMultiplier
        
        // VM costs for classic compute
        const driverPricingTier = item.driver_pricing_tier || 'on_demand'
        const driverPaymentOption = item.driver_payment_option || 'NA'
        const workerPricingTier = item.worker_pricing_tier || 'spot'
        const workerPaymentOption = item.worker_payment_option || 'NA'
        
        const driverVMCostPerHour = getVMPrice(cloud, region, item.driver_node_type || '', driverPricingTier, driverPaymentOption)
        const workerVMCostPerHour = getVMPrice(cloud, region, item.worker_node_type || '', workerPricingTier, workerPaymentOption)
        
        const totalVMCostPerHour = driverVMCostPerHour + (workerVMCostPerHour * numWorkers)
        vmCost = totalVMCostPerHour * hoursPerMonth
      }
      monthlyDBUs = dbuPerHour * hoursPerMonth
      break
    
    case 'DLT':
      if (item.serverless_enabled) {
        // DLT Serverless: DBU/Hour = base_dbu_rate × photon_multiplier (always on) × serverless_multiplier
        // Photon is ALWAYS enabled in serverless (built-in)
        dbuPerHour = (driverDBURate + (workerDBURate * numWorkers)) * photonMultiplier * serverlessMultiplier
      } else {
        // DLT Classic: DBU/Hour = (driver_dbu + worker_dbu × workers) × photon_multiplier
        dbuPerHour = (driverDBURate + (workerDBURate * numWorkers)) * photonMultiplier
        
        const driverPricingTier = item.driver_pricing_tier || 'on_demand'
        const driverPaymentOption = item.driver_payment_option || 'NA'
        const workerPricingTier = item.worker_pricing_tier || 'spot'
        const workerPaymentOption = item.worker_payment_option || 'NA'
        
        const driverVMCostPerHour = getVMPrice(cloud, region, item.driver_node_type || '', driverPricingTier, driverPaymentOption)
        const workerVMCostPerHour = getVMPrice(cloud, region, item.worker_node_type || '', workerPricingTier, workerPaymentOption)
        
        const totalVMCostPerHour = driverVMCostPerHour + (workerVMCostPerHour * numWorkers)
        vmCost = totalVMCostPerHour * hoursPerMonth
      }
      monthlyDBUs = dbuPerHour * hoursPerMonth
      break
    
    case 'DBSQL':
      const dbsqlSize = dbsqlSizes.find(s => s.id === item.dbsql_warehouse_size || s.name === item.dbsql_warehouse_size)
      const warehouseDBUs = dbsqlSize?.dbu_per_hour || DBSQL_DBU_RATES[item.dbsql_warehouse_size || 'Small'] || 12
      const numClusters = item.dbsql_num_clusters || 1
      
      dbuPerHour = warehouseDBUs * numClusters
      monthlyDBUs = dbuPerHour * hoursPerMonth
      
      const dbsqlWarehouseType = item.dbsql_warehouse_type || 'SERVERLESS'
      if (dbsqlWarehouseType !== 'SERVERLESS') {
        // DBSQL has separate driver and worker pricing tier selections
        const dbsqlDriverPricingTier = item.dbsql_driver_pricing_tier || item.driver_pricing_tier || 'on_demand'
        const dbsqlDriverPaymentOption = item.dbsql_driver_payment_option || item.driver_payment_option || 'NA'
        const dbsqlWorkerPricingTier = item.dbsql_worker_pricing_tier || item.worker_pricing_tier || 'spot'
        const dbsqlWorkerPaymentOption = item.dbsql_worker_payment_option || item.worker_payment_option || 'NA'
        
        if (item.driver_node_type) {
          const dbsqlDriverVMCost = getVMPrice(cloud, region, item.driver_node_type, dbsqlDriverPricingTier, dbsqlDriverPaymentOption)
          const dbsqlWorkerVMCost = item.worker_node_type 
            ? getVMPrice(cloud, region, item.worker_node_type, dbsqlWorkerPricingTier, dbsqlWorkerPaymentOption)
            : 0
          const dbsqlNumWorkers = item.num_workers || 0
          
          const dbsqlVMCostPerHour = (dbsqlDriverVMCost + (dbsqlWorkerVMCost * dbsqlNumWorkers)) * numClusters
          vmCost = dbsqlVMCostPerHour * hoursPerMonth
        }
      }
      break
    
    case 'VECTOR_SEARCH':
      const vectorMode = item.vector_search_mode || 'standard'
      const vectorCapacity = item.vector_capacity_millions || 1
      
      const vectorRateData = getVectorSearchRate(vectorMode)
      const divisor = vectorRateData?.input_divisor || (vectorMode === 'storage_optimized' ? 64 : 2)
      const unitsUsed = Math.ceil(vectorCapacity / divisor)
      
      const vectorModeDBURate = vectorRateData?.dbu_per_hour || (vectorMode === 'storage_optimized' ? 0.5 : 2.0)
      dbuPerHour = unitsUsed * vectorModeDBURate
      monthlyDBUs = dbuPerHour * hoursPerMonth
      break
    
    case 'MODEL_SERVING':
      const gpuType = item.model_serving_gpu_type || 'cpu'
      const gpuTypeData = modelServingGPUTypes.find(g => g.id === gpuType || g.name === gpuType)
      const gpuDBURate = gpuTypeData?.dbu_per_hour || 2
      
      dbuPerHour = gpuDBURate
      monthlyDBUs = dbuPerHour * hoursPerMonth
      break
    
    case 'LAKEBASE':
      const lakebaseCU = item.lakebase_cu || 1
      const lakebaseNodes = item.lakebase_ha_nodes || 1
      
      dbuPerHour = lakebaseCU * lakebaseNodes
      monthlyDBUs = dbuPerHour * hoursPerMonth
      break
    
    case 'FMAPI_DATABRICKS':
      const fmapiDbxQuantity = item.fmapi_quantity || 0
      const fmapiDbxRateType = item.fmapi_rate_type || 'input_token'
      const fmapiDbxIsProvisioned = ['provisioned_scaling', 'provisioned_entry'].includes(fmapiDbxRateType)
      
      const dbxRateData = item.fmapi_model 
        ? getFMAPIDatabricksRate(item.fmapi_model, fmapiDbxRateType) 
        : null
      
      if (fmapiDbxIsProvisioned) {
        const provisionedDbxDbuPerHour = dbxRateData?.dbu_per_hour || 
          (fmapiDbxRateType === 'provisioned_scaling' ? 200 : 50)
        monthlyDBUs = fmapiDbxQuantity * provisionedDbxDbuPerHour
      } else {
        const tokenDbxRate = dbxRateData?.dbu_per_1M_tokens || 
          (fmapiDbxRateType === 'output_token' ? 3.0 : 1.0)
        monthlyDBUs = fmapiDbxQuantity * tokenDbxRate
      }
      break
    
    case 'FMAPI_PROPRIETARY':
      const fmapiPropQuantity = item.fmapi_quantity || 0
      const fmapiPropRateType = item.fmapi_rate_type || 'input_token'
      const fmapiPropIsProvisioned = fmapiPropRateType === 'provisioned_scaling'
      
      const propRateData = (item.fmapi_provider && item.fmapi_model)
        ? getFMAPIProprietaryRate(item.fmapi_provider, item.fmapi_model, fmapiPropRateType)
        : null
      
      if (fmapiPropIsProvisioned) {
        const provisionedPropDbuPerHour = propRateData?.dbu_per_hour || 150
        monthlyDBUs = fmapiPropQuantity * provisionedPropDbuPerHour
      } else {
        let tokenPropRate = propRateData?.dbu_per_1M_tokens
        if (!tokenPropRate) {
          switch (fmapiPropRateType) {
            case 'output_token': tokenPropRate = 6.0; break
            case 'cache_read': tokenPropRate = 0.5; break
            case 'cache_write': tokenPropRate = 1.0; break
            default: tokenPropRate = 2.0
          }
        }
        monthlyDBUs = fmapiPropQuantity * tokenPropRate
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

