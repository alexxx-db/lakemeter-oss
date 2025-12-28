/**
 * Static Pricing Bundle Loader
 * 
 * Loads pre-generated pricing data from static JSON files.
 * These files are generated from Lakebase reference tables at deploy time.
 * 
 * Benefits:
 * - Zero runtime API calls for pricing lookups
 * - Instant cost calculations (<1ms)
 * - Works offline after initial load
 * - Cached in memory for app lifetime
 */

// ============================================================================
// Types
// ============================================================================

export interface InstanceDBURate {
  dbu_rate: number
  vcpus: number | null
  memory_gb: number | null
  family: string | null
}

export interface DBUMultiplier {
  multiplier: number
  category: string | null
  feature: string  // 'photon', 'serverless_dlt', 'serverless_jobs', 'serverless_notebook', 'lakebase'
}

export interface DBSQLRate {
  dbu_per_hour: number
  sku_product_type: string
  includes_compute: boolean
}

export interface DBSQLWarehouseConfig {
  driver_count: number
  driver_instance_type: string
  worker_count: number
  worker_instance_type: string
}

export interface VectorSearchRate {
  dbu_rate: number
  input_divisor: number
  sku_product_type: string
  description: string | null
}

export interface ModelServingRate {
  dbu_rate: number
  sku_product_type: string
  description: string | null
}

export interface FMAPIRate {
  dbu_rate: number
  input_divisor: number
  is_hourly: boolean
  sku_product_type: string
}

export interface PricingBundle {
  instanceDBURates: Record<string, Record<string, InstanceDBURate>>  // cloud -> instance_type -> rate
  dbuMultipliers: Record<string, DBUMultiplier>                       // "cloud:sku_type:feature" -> multiplier (photon, serverless, lakebase)
  vmCosts: Record<string, number>                                     // "cloud:region:instance:tier:payment" -> cost
  dbuRates: Record<string, Record<string, number>>                   // "cloud:region:tier" -> product_type -> price
  dbsqlRates: Record<string, DBSQLRate>                              // "cloud:type:size" -> rate
  dbsqlWarehouseConfig: Record<string, DBSQLWarehouseConfig>         // "cloud:type:size" -> config
  vectorSearchRates: Record<string, VectorSearchRate>                // "cloud:mode" -> rate
  modelServingRates: Record<string, ModelServingRate>                // "cloud:gpu_type" -> rate
  fmapiDatabricksRates: Record<string, FMAPIRate>                    // "cloud:model:rate_type" -> rate
  fmapiProprietaryRates: Record<string, FMAPIRate>                   // "cloud:provider:model:endpoint:context:rate_type" -> rate
  loadedAt: Date | null
  isLoaded: boolean
}

// ============================================================================
// Loader
// ============================================================================

const PRICING_BASE_URL = '/static/pricing'

async function loadJSON<T>(filename: string): Promise<T> {
  const response = await fetch(`${PRICING_BASE_URL}/${filename}`)
  if (!response.ok) {
    throw new Error(`Failed to load ${filename}: ${response.status}`)
  }
  return response.json()
}

/**
 * Load all pricing bundle files.
 * Call this on app initialization.
 */
export async function loadPricingBundle(): Promise<PricingBundle> {
  console.log('📦 Loading pricing bundle...')
  const startTime = Date.now()
  
  try {
    const [
      instanceDBURates,
      dbuMultipliers,
      vmCosts,
      dbuRates,
      dbsqlRates,
      dbsqlWarehouseConfig,
      vectorSearchRates,
      modelServingRates,
      fmapiDatabricksRates,
      fmapiProprietaryRates
    ] = await Promise.all([
      loadJSON<Record<string, Record<string, InstanceDBURate>>>('instance-dbu-rates.json'),
      loadJSON<Record<string, DBUMultiplier>>('dbu-multipliers.json'),
      loadJSON<Record<string, number>>('vm-costs.json'),
      loadJSON<Record<string, Record<string, number>>>('dbu-rates.json'),
      loadJSON<Record<string, DBSQLRate>>('dbsql-rates.json'),
      loadJSON<Record<string, DBSQLWarehouseConfig>>('dbsql-warehouse-config.json'),
      loadJSON<Record<string, VectorSearchRate>>('vector-search-rates.json'),
      loadJSON<Record<string, ModelServingRate>>('model-serving-rates.json'),
      loadJSON<Record<string, FMAPIRate>>('fmapi-databricks-rates.json'),
      loadJSON<Record<string, FMAPIRate>>('fmapi-proprietary-rates.json')
    ])
    
    const loadTime = Date.now() - startTime
    console.log(`✅ Pricing bundle loaded in ${loadTime}ms`)
    
    return {
      instanceDBURates,
      dbuMultipliers,
      vmCosts,
      dbuRates,
      dbsqlRates,
      dbsqlWarehouseConfig,
      vectorSearchRates,
      modelServingRates,
      fmapiDatabricksRates,
      fmapiProprietaryRates,
      loadedAt: new Date(),
      isLoaded: true
    }
  } catch (error) {
    console.error('❌ Failed to load pricing bundle:', error)
    // Return empty bundle - calculations will use fallback values
    return createEmptyBundle()
  }
}

/**
 * Create an empty pricing bundle (for fallback/error cases).
 */
export function createEmptyBundle(): PricingBundle {
  return {
    instanceDBURates: {},
    dbuMultipliers: {},
    vmCosts: {},
    dbuRates: {},
    dbsqlRates: {},
    dbsqlWarehouseConfig: {},
    vectorSearchRates: {},
    modelServingRates: {},
    fmapiDatabricksRates: {},
    fmapiProprietaryRates: {},
    loadedAt: null,
    isLoaded: false
  }
}

// ============================================================================
// Lookup Helpers
// ============================================================================

/**
 * Get instance DBU rate.
 */
export function getInstanceDBURate(
  bundle: PricingBundle,
  cloud: string,
  instanceType: string
): number {
  const cloudData = bundle.instanceDBURates[cloud.toLowerCase()]
  if (!cloudData) return 0.5 // fallback
  
  const instance = cloudData[instanceType]
  return instance?.dbu_rate ?? 0.5 // fallback
}

/**
 * Get photon multiplier.
 * Key format in dbuMultipliers: "cloud:sku_type:feature"
 * For photon, feature = 'photon'
 */
export function getPhotonMultiplier(
  bundle: PricingBundle,
  cloud: string,
  skuType: string
): number {
  // Try exact match with photon feature
  const key = `${cloud.toLowerCase()}:${skuType}:photon`
  const data = bundle.dbuMultipliers[key]
  if (data?.multiplier) return data.multiplier
  
  // Try without feature (fallback for older data format)
  const keyNoFeature = `${cloud.toLowerCase()}:${skuType}`
  const dataNoFeature = bundle.dbuMultipliers[keyNoFeature]
  if (dataNoFeature?.multiplier) return dataNoFeature.multiplier
  
  return 2.0 // fallback
}

/**
 * Get serverless multiplier.
 * Key format in dbuMultipliers: "cloud:sku_type:feature"
 * For serverless, feature = 'serverless_dlt', 'serverless_jobs', or 'serverless_notebook'
 */
export function getServerlessMultiplier(
  bundle: PricingBundle,
  cloud: string,
  skuType: string,
  workloadType: string
): number {
  // Map workload type to feature name
  const featureMap: Record<string, string> = {
    'DLT': 'serverless_dlt',
    'JOBS': 'serverless_jobs',
    'ALL_PURPOSE': 'serverless_notebook'
  }
  const feature = featureMap[workloadType] || 'serverless_jobs'
  
  const key = `${cloud.toLowerCase()}:${skuType}:${feature}`
  const data = bundle.dbuMultipliers[key]
  return data?.multiplier ?? 1.0 // fallback (standard = 1x)
}

/**
 * Get VM cost per hour.
 */
export function getVMCost(
  bundle: PricingBundle,
  cloud: string,
  region: string,
  instanceType: string,
  pricingTier: string = 'on_demand',
  paymentOption: string = 'NA'
): number {
  if (!instanceType) return 0
  
  // Try exact match
  const exactKey = `${cloud.toLowerCase()}:${region}:${instanceType}:${pricingTier}:${paymentOption}`
  if (bundle.vmCosts[exactKey] !== undefined) {
    return bundle.vmCosts[exactKey]
  }
  
  // Try without payment option
  const keyNoPayment = `${cloud.toLowerCase()}:${region}:${instanceType}:${pricingTier}:NA`
  if (bundle.vmCosts[keyNoPayment] !== undefined) {
    return bundle.vmCosts[keyNoPayment]
  }
  
  // Try any pricing tier for this instance
  for (const key of Object.keys(bundle.vmCosts)) {
    if (key.startsWith(`${cloud.toLowerCase()}:${region}:${instanceType}:`)) {
      return bundle.vmCosts[key]
    }
  }
  
  return 0 // VM cost not found
}

/**
 * Get DBU price ($/DBU).
 */
export function getDBUPrice(
  bundle: PricingBundle,
  cloud: string,
  region: string,
  tier: string,
  productType: string
): number {
  // Normalize tier to uppercase (JSON keys use PREMIUM, STANDARD, etc.)
  const normalizedTier = tier.toUpperCase()
  const key = `${cloud.toLowerCase()}:${region}:${normalizedTier}`
  const tierData = bundle.dbuRates[key]
  
  if (tierData && tierData[productType] !== undefined) {
    return tierData[productType]
  }
  
  // Fallback: try global rates (for products without regional pricing)
  const globalKey = `${cloud.toLowerCase()}:global:${normalizedTier}`
  const globalData = bundle.dbuRates[globalKey]
  if (globalData && globalData[productType] !== undefined) {
    return globalData[productType]
  }
  
  // Fallback: try any region with this tier
  for (const k of Object.keys(bundle.dbuRates)) {
    if (k.startsWith(`${cloud.toLowerCase()}:`) && k.endsWith(`:${normalizedTier}`)) {
      const data = bundle.dbuRates[k]
      if (data && data[productType] !== undefined) {
        return data[productType]
      }
    }
  }
  
  // Hardcoded fallbacks by SKU type
  const fallbacks: Record<string, number> = {
    'JOBS_COMPUTE': 0.15,
    'JOBS_COMPUTE_(PHOTON)': 0.20,
    'ALL_PURPOSE_COMPUTE': 0.40,
    'ALL_PURPOSE_COMPUTE_(PHOTON)': 0.55,
    'SQL_COMPUTE': 0.22,
    'SQL_PRO_COMPUTE': 0.55,
    'SERVERLESS_SQL_COMPUTE': 0.70,
    'SERVERLESS_REAL_TIME_INFERENCE': 0.07,
  }
  
  return fallbacks[productType] ?? 0.15
}

/**
 * Get DBSQL warehouse rate.
 */
export function getDBSQLRate(
  bundle: PricingBundle,
  cloud: string,
  warehouseType: string,
  warehouseSize: string
): DBSQLRate | null {
  const key = `${cloud.toLowerCase()}:${warehouseType.toLowerCase()}:${warehouseSize}`
  return bundle.dbsqlRates[key] ?? null
}

/**
 * Get DBSQL warehouse config (for VM cost calculation).
 */
export function getDBSQLWarehouseConfig(
  bundle: PricingBundle,
  cloud: string,
  warehouseType: string,
  warehouseSize: string
): DBSQLWarehouseConfig | null {
  const key = `${cloud.toLowerCase()}:${warehouseType.toLowerCase()}:${warehouseSize}`
  return bundle.dbsqlWarehouseConfig[key] ?? null
}

/**
 * Get Vector Search rate.
 */
export function getVectorSearchRate(
  bundle: PricingBundle,
  cloud: string,
  mode: string
): VectorSearchRate | null {
  const key = `${cloud.toLowerCase()}:${mode}`
  return bundle.vectorSearchRates[key] ?? null
}

/**
 * Get Model Serving GPU rate.
 */
export function getModelServingRate(
  bundle: PricingBundle,
  cloud: string,
  gpuType: string
): ModelServingRate | null {
  const key = `${cloud.toLowerCase()}:${gpuType}`
  return bundle.modelServingRates[key] ?? null
}

/**
 * Get FMAPI Databricks rate.
 */
export function getFMAPIDatabricksRate(
  bundle: PricingBundle,
  cloud: string,
  model: string,
  rateType: string
): FMAPIRate | null {
  const key = `${cloud.toLowerCase()}:${model}:${rateType}`
  return bundle.fmapiDatabricksRates[key] ?? null
}

/**
 * Get FMAPI Proprietary rate.
 */
export function getFMAPIProprietaryRate(
  bundle: PricingBundle,
  cloud: string,
  provider: string,
  model: string,
  endpointType: string,
  contextLength: string,
  rateType: string
): FMAPIRate | null {
  const key = `${cloud.toLowerCase()}:${provider}:${model}:${endpointType}:${contextLength}:${rateType}`
  return bundle.fmapiProprietaryRates[key] ?? null
}

