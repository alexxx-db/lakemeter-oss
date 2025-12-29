import { useState, useMemo, useCallback } from 'react'
import { motion } from 'framer-motion'
import { 
  BeakerIcon, 
  PlayIcon, 
  CheckCircleIcon, 
  XCircleIcon,
  ArrowPathIcon,
  DocumentArrowDownIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ExclamationTriangleIcon,
  CogIcon,
  AdjustmentsHorizontalIcon
} from '@heroicons/react/24/outline'
import { useStore } from '../store/useStore'
import { calculateWorkloadCost, type CostBreakdown, type CostCalculationContext } from '../utils/costCalculation'
import { 
  getInstanceDBURate as getBundleInstanceDBURate,
  getPhotonMultiplier as getBundlePhotonMultiplier,
  getDBUPrice as getBundleDBUPrice,
  getDBSQLWarehouseConfig
} from '../utils/pricingBundle'
import type { LineItem } from '../types'

// ===== TEST CONFIGURATION =====

// Environments to test
const TEST_ENVIRONMENTS = {
  aws: {
    regions: ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1'],
    tiers: ['STANDARD', 'PREMIUM', 'ENTERPRISE'],
    vmTypes: [
      'c5.xlarge', 'c5.2xlarge', 'c5.4xlarge', 'c5.9xlarge',
      'm5.xlarge', 'm5.2xlarge', 'm5.4xlarge',
      'r5.xlarge', 'r5.2xlarge', 'r5.4xlarge',
      'i3.xlarge', 'i3.2xlarge',
      'g4dn.xlarge', 'g4dn.2xlarge', 'p3.2xlarge'
    ]
  },
  azure: {
    regions: ['eastus', 'westus2', 'westeurope', 'southeastasia'],
    tiers: ['STANDARD', 'PREMIUM'],
    vmTypes: [
      'Standard_D4s_v3', 'Standard_D8s_v3', 'Standard_D16s_v3',
      'Standard_E4s_v3', 'Standard_E8s_v3',
      'Standard_F4s_v2', 'Standard_F8s_v2',
      'Standard_L8s_v2', 'Standard_NC6s_v3'
    ]
  },
  gcp: {
    regions: ['us-central1', 'us-east1', 'europe-west1', 'asia-southeast1'],
    tiers: ['STANDARD', 'PREMIUM', 'ENTERPRISE'],
    vmTypes: [
      'n2-standard-4', 'n2-standard-8', 'n2-standard-16',
      'n2-highmem-4', 'n2-highmem-8',
      'c2-standard-4', 'c2-standard-8',
      'n1-standard-4', 'n1-standard-8'
    ]
  }
}

// FMAPI Databricks models
const FMAPI_DATABRICKS_MODELS = [
  'llama-3-1-70b', 'llama-3-1-8b', 'llama-3-3-70b',
  'mixtral-8x7b', 'dbrx-instruct',
  'bge-large', 'gte-large'
]

// FMAPI Proprietary configurations
const FMAPI_PROPRIETARY_CONFIGS = [
  { provider: 'openai', model: 'gpt-4o', contexts: ['all', 'short', 'long'] },
  { provider: 'openai', model: 'gpt-4o-mini', contexts: ['all'] },
  { provider: 'openai', model: 'gpt-4-turbo', contexts: ['all'] },
  { provider: 'anthropic', model: 'claude-sonnet-4', contexts: ['short', 'long'] },
  { provider: 'anthropic', model: 'claude-haiku-4', contexts: ['short', 'long'] },
  { provider: 'anthropic', model: 'claude-opus-4', contexts: ['short', 'long'] },
  { provider: 'google', model: 'gemini-2-0-flash', contexts: ['short', 'long'] },
  { provider: 'google', model: 'gemini-1-5-pro', contexts: ['short', 'long'] }
]

// DBSQL warehouse sizes
const DBSQL_SIZES = ['2X-Small', 'X-Small', 'Small', 'Medium', 'Large', 'X-Large', '2X-Large', '3X-Large', '4X-Large']

// Model serving GPU types
const GPU_TYPES = ['cpu', 'gpu_small_t4', 'gpu_medium_a10g_1x', 'gpu_large_a10g_4x']

// Vector search modes
const VECTOR_MODES = ['standard', 'storage_optimized']

// ===== INTERFACES =====

interface TestCase {
  id: string
  name: string
  category: string
  workloadType: string
  config: Partial<LineItem>
  environment: {
    cloud: string
    region: string
    tier: string
  }
}

interface TestResult {
  testCase: TestCase
  localResult: CostBreakdown
  apiResult: CostBreakdown | null
  apiError?: string
  localTimeMs: number
  apiTimeMs: number
  matches: boolean
  discrepancies: {
    field: string
    local: number
    api: number
    diff: number
    diffPercent: number
  }[]
}

interface TestConfig {
  clouds: string[]
  regionsPerCloud: number
  tiersPerCloud: number
  vmSamplesPerCloud: number
  includeJobs: boolean
  includeAllPurpose: boolean
  includeDLT: boolean
  includeDBSQL: boolean
  includeVectorSearch: boolean
  includeModelServing: boolean
  includeFMAPIDB: boolean
  includeFMAPIProp: boolean
  includeLakebase: boolean
}

// ===== HELPER FUNCTIONS =====

// Random sample from array
function sampleArray<T>(arr: T[], count: number): T[] {
  const shuffled = [...arr].sort(() => Math.random() - 0.5)
  return shuffled.slice(0, Math.min(count, arr.length))
}

// Generate all test cases based on config
function generateTestCases(config: TestConfig): TestCase[] {
  const testCases: TestCase[] = []
  let idCounter = 0
  
  for (const cloud of config.clouds) {
    const envConfig = TEST_ENVIRONMENTS[cloud as keyof typeof TEST_ENVIRONMENTS]
    if (!envConfig) continue
    
    const regions = sampleArray(envConfig.regions, config.regionsPerCloud)
    const tiers = sampleArray(envConfig.tiers, config.tiersPerCloud)
    const vmTypes = sampleArray(envConfig.vmTypes, config.vmSamplesPerCloud)
    
    for (const region of regions) {
      for (const tier of tiers) {
        const env = { cloud, region, tier }
        
        // Jobs tests
        if (config.includeJobs) {
          for (const vm of vmTypes.slice(0, 2)) {
            // Classic no photon
            testCases.push({
              id: `${++idCounter}`,
              name: `Jobs Classic - ${vm}`,
              category: 'Jobs',
              workloadType: 'JOBS',
              environment: env,
              config: {
                serverless_enabled: false,
                photon_enabled: false,
                driver_node_type: vm,
                worker_node_type: vm,
                num_workers: 2,
                driver_pricing_tier: 'on_demand',
                worker_pricing_tier: 'spot',
                runs_per_day: 1,
                avg_runtime_minutes: 30,
                days_per_month: 22
              }
            })
            
            // Classic with photon
            testCases.push({
              id: `${++idCounter}`,
              name: `Jobs Classic Photon - ${vm}`,
              category: 'Jobs',
              workloadType: 'JOBS',
              environment: env,
              config: {
                serverless_enabled: false,
                photon_enabled: true,
                driver_node_type: vm,
                worker_node_type: vm,
                num_workers: 4,
                driver_pricing_tier: 'on_demand',
                worker_pricing_tier: 'spot',
                runs_per_day: 2,
                avg_runtime_minutes: 45,
                days_per_month: 22
              }
            })
          }
          
          // Serverless modes
          for (const mode of ['standard', 'performance']) {
            testCases.push({
              id: `${++idCounter}`,
              name: `Jobs Serverless ${mode}`,
              category: 'Jobs',
              workloadType: 'JOBS',
              environment: env,
              config: {
                serverless_enabled: true,
                serverless_mode: mode,
                driver_node_type: vmTypes[0],
                worker_node_type: vmTypes[0],
                num_workers: 2,
                runs_per_day: 3,
                avg_runtime_minutes: 20,
                days_per_month: 22
              }
            })
          }
        }
        
        // All Purpose tests
        if (config.includeAllPurpose) {
          for (const vm of vmTypes.slice(0, 2)) {
            testCases.push({
              id: `${++idCounter}`,
              name: `All Purpose Classic - ${vm}`,
              category: 'All Purpose',
              workloadType: 'ALL_PURPOSE',
              environment: env,
              config: {
                serverless_enabled: false,
                photon_enabled: false,
                driver_node_type: vm,
                worker_node_type: vm,
                num_workers: 2,
                driver_pricing_tier: 'on_demand',
                worker_pricing_tier: 'on_demand',
                hours_per_month: 160
              }
            })
          }
          
          // Serverless
          testCases.push({
            id: `${++idCounter}`,
            name: 'All Purpose Serverless',
            category: 'All Purpose',
            workloadType: 'ALL_PURPOSE',
            environment: env,
            config: {
              serverless_enabled: true,
              serverless_mode: 'standard',
              driver_node_type: vmTypes[0],
              worker_node_type: vmTypes[0],
              num_workers: 2,
              hours_per_month: 100
            }
          })
        }
        
        // DLT tests
        if (config.includeDLT) {
          for (const edition of ['CORE', 'PRO', 'ADVANCED']) {
            testCases.push({
              id: `${++idCounter}`,
              name: `DLT Classic ${edition}`,
              category: 'DLT',
              workloadType: 'DLT',
              environment: env,
              config: {
                serverless_enabled: false,
                photon_enabled: edition !== 'CORE',
                dlt_edition: edition,
                driver_node_type: vmTypes[0],
                worker_node_type: vmTypes[0],
                num_workers: 2,
                driver_pricing_tier: 'on_demand',
                worker_pricing_tier: 'spot',
                runs_per_day: 4,
                avg_runtime_minutes: 30,
                days_per_month: 30
              }
            })
          }
          
          // DLT Serverless
          testCases.push({
            id: `${++idCounter}`,
            name: 'DLT Serverless',
            category: 'DLT',
            workloadType: 'DLT',
            environment: env,
            config: {
              serverless_enabled: true,
              serverless_mode: 'standard',
              driver_node_type: vmTypes[0],
              worker_node_type: vmTypes[0],
              num_workers: 2,
              runs_per_day: 6,
              avg_runtime_minutes: 20,
              days_per_month: 30
            }
          })
        }
        
        // DBSQL tests
        if (config.includeDBSQL) {
          // Serverless - different sizes
          for (const size of sampleArray(DBSQL_SIZES, 3)) {
            testCases.push({
              id: `${++idCounter}`,
              name: `DBSQL Serverless ${size}`,
              category: 'DBSQL',
              workloadType: 'DBSQL',
              environment: env,
              config: {
                dbsql_warehouse_type: 'SERVERLESS',
                dbsql_warehouse_size: size,
                dbsql_num_clusters: 1,
                hours_per_month: 160
              }
            })
          }
          
          // Pro - different sizes
          for (const size of sampleArray(DBSQL_SIZES, 2)) {
            testCases.push({
              id: `${++idCounter}`,
              name: `DBSQL Pro ${size}`,
              category: 'DBSQL',
              workloadType: 'DBSQL',
              environment: env,
              config: {
                dbsql_warehouse_type: 'PRO',
                dbsql_warehouse_size: size,
                dbsql_num_clusters: 1,
                dbsql_driver_pricing_tier: 'on_demand',
                dbsql_worker_pricing_tier: 'spot',
                hours_per_month: 100
              }
            })
          }
          
          // Classic
          testCases.push({
            id: `${++idCounter}`,
            name: 'DBSQL Classic Medium',
            category: 'DBSQL',
            workloadType: 'DBSQL',
            environment: env,
            config: {
              dbsql_warehouse_type: 'CLASSIC',
              dbsql_warehouse_size: 'Medium',
              dbsql_num_clusters: 1,
              dbsql_driver_pricing_tier: 'on_demand',
              dbsql_worker_pricing_tier: 'spot',
              hours_per_month: 80
            }
          })
        }
        
        // Vector Search tests
        if (config.includeVectorSearch) {
          for (const mode of VECTOR_MODES) {
            for (const capacity of [1, 5, 20]) {
              testCases.push({
                id: `${++idCounter}`,
                name: `Vector Search ${mode} ${capacity}M`,
                category: 'Vector Search',
                workloadType: 'VECTOR_SEARCH',
                environment: env,
                config: {
                  vector_search_mode: mode,
                  vector_capacity_millions: capacity,
                  hours_per_month: 730
                }
              })
            }
          }
        }
        
        // Model Serving tests
        if (config.includeModelServing) {
          for (const gpu of GPU_TYPES) {
            testCases.push({
              id: `${++idCounter}`,
              name: `Model Serving ${gpu}`,
              category: 'Model Serving',
              workloadType: 'MODEL_SERVING',
              environment: env,
              config: {
                model_serving_gpu_type: gpu,
                hours_per_month: 200
              }
            })
          }
        }
        
        // FMAPI Databricks tests
        if (config.includeFMAPIDB) {
          for (const model of sampleArray(FMAPI_DATABRICKS_MODELS, 3)) {
            for (const rateType of ['input_token', 'output_token']) {
              testCases.push({
                id: `${++idCounter}`,
                name: `FMAPI DB ${model} ${rateType}`,
                category: 'FMAPI Databricks',
                workloadType: 'FMAPI_DATABRICKS',
                environment: env,
                config: {
                  fmapi_model: model,
                  fmapi_rate_type: rateType,
                  fmapi_quantity: 10
                }
              })
            }
          }
        }
        
        // FMAPI Proprietary tests
        if (config.includeFMAPIProp) {
          for (const propConfig of sampleArray(FMAPI_PROPRIETARY_CONFIGS, 4)) {
            for (const context of propConfig.contexts.slice(0, 2)) {
              for (const rateType of ['input_token', 'output_token']) {
                testCases.push({
                  id: `${++idCounter}`,
                  name: `FMAPI ${propConfig.provider} ${propConfig.model} ${context} ${rateType}`,
                  category: 'FMAPI Proprietary',
                  workloadType: 'FMAPI_PROPRIETARY',
                  environment: env,
                  config: {
                    fmapi_provider: propConfig.provider,
                    fmapi_model: propConfig.model,
                    fmapi_endpoint_type: 'global',
                    fmapi_context_length: context,
                    fmapi_rate_type: rateType,
                    fmapi_quantity: 5
                  }
                })
              }
            }
          }
        }
        
        // Lakebase tests
        if (config.includeLakebase) {
          for (const cu of [1, 2, 4, 8]) {
            for (const nodes of [1, 2]) {
              testCases.push({
                id: `${++idCounter}`,
                name: `Lakebase ${cu}CU ${nodes}node`,
                category: 'Lakebase',
                workloadType: 'LAKEBASE',
                environment: env,
                config: {
                  lakebase_cu: cu,
                  lakebase_ha_nodes: nodes,
                  hours_per_month: 730
                }
              })
            }
          }
        }
      }
    }
  }
  
  return testCases
}

// API endpoint mapping
function getAPIEndpoint(workloadType: string, config: Partial<LineItem>): string {
  switch (workloadType) {
    case 'JOBS':
      return config.serverless_enabled 
        ? '/api/v1/calculate/jobs-serverless'
        : '/api/v1/calculate/jobs-classic'
    case 'ALL_PURPOSE':
      return config.serverless_enabled
        ? '/api/v1/calculate/all-purpose-serverless'
        : '/api/v1/calculate/all-purpose-classic'
    case 'DLT':
      return config.serverless_enabled
        ? '/api/v1/calculate/dlt-serverless'
        : '/api/v1/calculate/dlt-classic'
    case 'DBSQL':
      return config.dbsql_warehouse_type === 'SERVERLESS'
        ? '/api/v1/calculate/dbsql-serverless'
        : '/api/v1/calculate/dbsql-classic-pro'
    case 'VECTOR_SEARCH':
      return '/api/v1/calculate/vector-search'
    case 'MODEL_SERVING':
      return '/api/v1/calculate/model-serving'
    case 'LAKEBASE':
      return '/api/v1/calculate/lakebase'
    case 'FMAPI_DATABRICKS':
      return '/api/v1/calculate/fmapi-databricks'
    case 'FMAPI_PROPRIETARY':
      return '/api/v1/calculate/fmapi-proprietary'
    default:
      return '/api/v1/calculate/jobs-classic'
  }
}

// Build API request body
function buildAPIRequest(testCase: TestCase): Record<string, unknown> {
  const { workloadType, config, environment } = testCase
  const base = { cloud: environment.cloud, region: environment.region, tier: environment.tier }
  
  switch (workloadType) {
    case 'JOBS':
    case 'ALL_PURPOSE':
      if (config.serverless_enabled) {
        return {
          ...base,
          driver_node_type: config.driver_node_type,
          worker_node_type: config.worker_node_type,
          num_workers: config.num_workers,
          serverless_mode: config.serverless_mode || 'standard',
          runs_per_day: config.runs_per_day,
          avg_runtime_minutes: config.avg_runtime_minutes,
          days_per_month: config.days_per_month,
          hours_per_month: config.hours_per_month
        }
      }
      return {
        ...base,
        driver_node_type: config.driver_node_type,
        worker_node_type: config.worker_node_type,
        num_workers: config.num_workers,
        photon_enabled: config.photon_enabled || false,
        driver_pricing_tier: config.driver_pricing_tier || 'on_demand',
        worker_pricing_tier: config.worker_pricing_tier || 'spot',
        driver_payment_option: 'NA',
        worker_payment_option: 'NA',
        runs_per_day: config.runs_per_day,
        avg_runtime_minutes: config.avg_runtime_minutes,
        days_per_month: config.days_per_month,
        hours_per_month: config.hours_per_month
      }
      
    case 'DLT':
      if (config.serverless_enabled) {
        return {
          ...base,
          driver_node_type: config.driver_node_type,
          worker_node_type: config.worker_node_type,
          num_workers: config.num_workers,
          serverless_mode: config.serverless_mode || 'standard',
          runs_per_day: config.runs_per_day,
          avg_runtime_minutes: config.avg_runtime_minutes,
          days_per_month: config.days_per_month
        }
      }
      return {
        ...base,
        driver_node_type: config.driver_node_type,
        worker_node_type: config.worker_node_type,
        num_workers: config.num_workers,
        dlt_edition: config.dlt_edition || 'CORE',
        photon_enabled: config.photon_enabled || false,
        driver_pricing_tier: config.driver_pricing_tier || 'on_demand',
        worker_pricing_tier: config.worker_pricing_tier || 'spot',
        driver_payment_option: 'NA',
        worker_payment_option: 'NA',
        runs_per_day: config.runs_per_day,
        avg_runtime_minutes: config.avg_runtime_minutes,
        days_per_month: config.days_per_month
      }
      
    case 'DBSQL':
      if (config.dbsql_warehouse_type === 'SERVERLESS') {
        return {
          ...base,
          warehouse_size: config.dbsql_warehouse_size,
          num_clusters: config.dbsql_num_clusters || 1,
          hours_per_month: config.hours_per_month
        }
      }
      return {
        ...base,
        warehouse_type: config.dbsql_warehouse_type,
        warehouse_size: config.dbsql_warehouse_size,
        num_clusters: config.dbsql_num_clusters || 1,
        driver_pricing_tier: config.dbsql_driver_pricing_tier || 'on_demand',
        worker_pricing_tier: config.dbsql_worker_pricing_tier || 'spot',
        driver_payment_option: 'NA',
        worker_payment_option: 'NA',
        hours_per_month: config.hours_per_month
      }
      
    case 'VECTOR_SEARCH':
      return {
        ...base,
        mode: config.vector_search_mode,
        vector_capacity_millions: config.vector_capacity_millions,
        hours_per_month: config.hours_per_month
      }
      
    case 'MODEL_SERVING':
      return {
        ...base,
        gpu_type: config.model_serving_gpu_type,
        hours_per_month: config.hours_per_month
      }
      
    case 'LAKEBASE':
      return {
        ...base,
        cu_size: config.lakebase_cu,
        num_nodes: config.lakebase_ha_nodes,
        hours_per_month: config.hours_per_month
      }
      
    case 'FMAPI_DATABRICKS':
      return {
        ...base,
        model: config.fmapi_model,
        rate_type: config.fmapi_rate_type,
        quantity: config.fmapi_quantity
      }
      
    case 'FMAPI_PROPRIETARY':
      return {
        ...base,
        provider: config.fmapi_provider,
        model: config.fmapi_model,
        endpoint_type: config.fmapi_endpoint_type,
        context_length: config.fmapi_context_length,
        rate_type: config.fmapi_rate_type,
        quantity: config.fmapi_quantity
      }
      
    default:
      return base
  }
}

// Compare results
function compareResults(
  local: CostBreakdown, 
  api: CostBreakdown | null,
  tolerancePercent: number = 1
): { field: string; local: number; api: number; diff: number; diffPercent: number }[] {
  if (!api) return []
  
  const discrepancies: { field: string; local: number; api: number; diff: number; diffPercent: number }[] = []
  const fields: (keyof CostBreakdown)[] = ['monthlyDBUs', 'dbuCost', 'vmCost', 'totalCost']
  
  for (const field of fields) {
    const localVal = (local[field] as number) || 0
    const apiVal = (api[field] as number) || 0
    const diff = Math.abs(localVal - apiVal)
    const diffPercent = apiVal !== 0 ? (diff / apiVal) * 100 : (localVal !== 0 ? 100 : 0)
    
    if (diffPercent > tolerancePercent && diff > 0.01) {
      discrepancies.push({ field, local: localVal, api: apiVal, diff, diffPercent })
    }
  }
  
  return discrepancies
}

// ===== MAIN COMPONENT =====

export default function TestCalculations() {
  const [results, setResults] = useState<TestResult[]>([])
  const [running, setRunning] = useState(false)
  const [currentTest, setCurrentTest] = useState<string | null>(null)
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set())
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [tolerancePercent, setTolerancePercent] = useState(1)
  const [showConfig, setShowConfig] = useState(false)
  const [progress, setProgress] = useState({ current: 0, total: 0 })
  
  // Test configuration
  const [testConfig, setTestConfig] = useState<TestConfig>({
    clouds: ['aws'],
    regionsPerCloud: 2,
    tiersPerCloud: 2,
    vmSamplesPerCloud: 3,
    includeJobs: true,
    includeAllPurpose: true,
    includeDLT: true,
    includeDBSQL: true,
    includeVectorSearch: true,
    includeModelServing: true,
    includeFMAPIDB: true,
    includeFMAPIProp: true,
    includeLakebase: true
  })
  
  const {
    dbuRatesMap,
    instanceTypes,
    dbsqlSizes,
    photonMultipliers,
    modelServingGPUTypes,
    vectorSearchModes,
    pricingBundle,
    isPricingBundleLoaded,
    getVMPrice,
    getFMAPIDatabricksRate,
    getFMAPIProprietaryRate,
    getVectorSearchRate
  } = useStore()
  
  // Generate test cases based on config
  const testCases = useMemo(() => generateTestCases(testConfig), [testConfig])
  
  // Filter by category
  const filteredTests = useMemo(() => {
    if (selectedCategory === 'all') return testCases
    return testCases.filter(t => t.category === selectedCategory)
  }, [testCases, selectedCategory])
  
  // Get unique categories
  const categories = useMemo(() => {
    const cats = new Set(testCases.map(t => t.category))
    return ['all', ...Array.from(cats)]
  }, [testCases])
  
  // Build context for a specific environment
  const buildContext = useCallback((cloud: string, region: string, tier: string): CostCalculationContext => ({
    cloud,
    region,
    tier,
    dbuRatesMap,
    instanceTypes,
    dbsqlSizes,
    photonMultipliers,
    modelServingGPUTypes,
    vectorSearchModes,
    getVMPrice,
    getFMAPIDatabricksRate,
    getFMAPIProprietaryRate: (provider: string, model: string, rateType: string, endpointType?: string, contextLength?: string) => {
      if (isPricingBundleLoaded && pricingBundle.fmapiProprietaryRates) {
        const ep = endpointType || 'global'
        const ctx = contextLength || 'all'
        const key = `${cloud.toLowerCase()}:${provider.toLowerCase()}:${model.toLowerCase()}:${ep}:${ctx}:${rateType}`
        const data = pricingBundle.fmapiProprietaryRates[key]
        if (data) {
          return {
            dbu_per_1M_tokens: data.is_hourly ? undefined : data.dbu_rate,
            dbu_per_hour: data.is_hourly ? data.dbu_rate : undefined
          }
        }
      }
      return getFMAPIProprietaryRate(provider, model, rateType)
    },
    getVectorSearchRate,
    getInstanceDBURate: (instanceType: string) => {
      if (!isPricingBundleLoaded) return null
      return getBundleInstanceDBURate(pricingBundle, cloud, instanceType)
    },
    getPhotonMultiplier: (skuType: string) => {
      if (!isPricingBundleLoaded) return null
      return getBundlePhotonMultiplier(pricingBundle, cloud, skuType)
    },
    getDBUPrice: (productType: string) => {
      if (!isPricingBundleLoaded) return null
      return getBundleDBUPrice(pricingBundle, cloud, region, tier, productType)
    },
    getDBSQLWarehouseConfig: (warehouseType: string, warehouseSize: string) => {
      if (!isPricingBundleLoaded) return null
      return getDBSQLWarehouseConfig(pricingBundle, cloud, warehouseType, warehouseSize)
    }
  }), [dbuRatesMap, instanceTypes, dbsqlSizes, photonMultipliers, modelServingGPUTypes, vectorSearchModes, isPricingBundleLoaded, pricingBundle, getVMPrice, getFMAPIDatabricksRate, getFMAPIProprietaryRate, getVectorSearchRate])
  
  // Run a single test
  const runSingleTest = async (testCase: TestCase): Promise<TestResult> => {
    const { environment, workloadType, config } = testCase
    const context = buildContext(environment.cloud, environment.region, environment.tier)
    
    const lineItem: Partial<LineItem> = {
      ...config,
      workload_type: workloadType
    }
    
    // Local calculation
    const localStart = performance.now()
    const localResult = calculateWorkloadCost(lineItem, context)
    const localTimeMs = performance.now() - localStart
    
    // API calculation
    const apiStart = performance.now()
    let apiResult: CostBreakdown | null = null
    let apiError: string | undefined
    
    try {
      const endpoint = getAPIEndpoint(workloadType, config)
      const body = buildAPIRequest(testCase)
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
      
      if (response.ok) {
        const data = await response.json()
        apiResult = {
          monthlyDBUs: data.dbu_per_month || data.dbu_per_hour * (config.hours_per_month || 730) || 0,
          dbuCost: data.dbu_cost_per_month || data.total_cost || 0,
          vmCost: data.vm_cost_per_month || 0,
          totalCost: data.total_cost_per_month || data.total_cost || 0
        }
      } else {
        apiError = `HTTP ${response.status}: ${await response.text()}`
      }
    } catch (e) {
      apiError = e instanceof Error ? e.message : 'Unknown error'
    }
    const apiTimeMs = performance.now() - apiStart
    
    const discrepancies = compareResults(localResult, apiResult, tolerancePercent)
    
    return {
      testCase,
      localResult,
      apiResult,
      apiError,
      localTimeMs,
      apiTimeMs,
      matches: discrepancies.length === 0 && !apiError,
      discrepancies
    }
  }
  
  // Run all tests
  const runAllTests = async () => {
    setRunning(true)
    setResults([])
    setProgress({ current: 0, total: filteredTests.length })
    
    for (let i = 0; i < filteredTests.length; i++) {
      const testCase = filteredTests[i]
      setCurrentTest(testCase.id)
      setProgress({ current: i + 1, total: filteredTests.length })
      const result = await runSingleTest(testCase)
      setResults(prev => [...prev, result])
    }
    
    setCurrentTest(null)
    setRunning(false)
  }
  
  // Stats
  const stats = useMemo(() => {
    const passed = results.filter(r => r.matches).length
    const failed = results.filter(r => !r.matches).length
    const apiErrors = results.filter(r => r.apiError).length
    const avgLocalTime = results.length > 0 
      ? results.reduce((sum, r) => sum + r.localTimeMs, 0) / results.length 
      : 0
    const avgApiTime = results.length > 0
      ? results.reduce((sum, r) => sum + r.apiTimeMs, 0) / results.length
      : 0
    const byCategory: Record<string, { passed: number; failed: number }> = {}
    results.forEach(r => {
      const cat = r.testCase.category
      if (!byCategory[cat]) byCategory[cat] = { passed: 0, failed: 0 }
      if (r.matches) byCategory[cat].passed++
      else byCategory[cat].failed++
    })
    return { passed, failed, apiErrors, avgLocalTime, avgApiTime, byCategory }
  }, [results])
  
  // Export CSV
  const exportCSV = () => {
    const headers = ['Test ID', 'Test Name', 'Category', 'Cloud', 'Region', 'Tier', 'Status', 'Local Total', 'API Total', 'Diff %', 'Local Time (ms)', 'API Time (ms)', 'Error']
    const rows = results.map(r => [
      r.testCase.id,
      r.testCase.name,
      r.testCase.category,
      r.testCase.environment.cloud,
      r.testCase.environment.region,
      r.testCase.environment.tier,
      r.matches ? 'PASS' : 'FAIL',
      r.localResult.totalCost.toFixed(2),
      r.apiResult?.totalCost.toFixed(2) || 'N/A',
      r.discrepancies[0]?.diffPercent.toFixed(2) || '0',
      r.localTimeMs.toFixed(1),
      r.apiTimeMs.toFixed(1),
      r.apiError || ''
    ])
    
    const csv = [headers.join(','), ...rows.map(r => r.map(c => `"${c}"`).join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `calculation-tests-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
  }
  
  const toggleExpanded = (id: string) => {
    const newExpanded = new Set(expandedResults)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedResults(newExpanded)
  }
  
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value)
  }
  
  const formatNumber = (value: number) => {
    if (value >= 1000) {
      return `${(value / 1000).toFixed(2)}K`
    }
    return value.toFixed(2)
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center">
            <BeakerIcon className="w-6 h-6 text-purple-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">Calculation Test Suite</h1>
            <p className="text-sm text-[var(--text-muted)]">
              Bulk testing across clouds, regions, tiers, and workload types
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowConfig(!showConfig)}
            className="btn btn-secondary flex items-center gap-2"
          >
            <AdjustmentsHorizontalIcon className="w-4 h-4" />
            Configure
          </button>
          {results.length > 0 && (
            <button
              onClick={exportCSV}
              className="btn btn-secondary flex items-center gap-2"
            >
              <DocumentArrowDownIcon className="w-4 h-4" />
              Export CSV
            </button>
          )}
          <button
            onClick={runAllTests}
            disabled={running}
            className="btn btn-primary flex items-center gap-2"
          >
            {running ? (
              <ArrowPathIcon className="w-4 h-4 animate-spin" />
            ) : (
              <PlayIcon className="w-4 h-4" />
            )}
            {running ? `Running ${progress.current}/${progress.total}` : `Run ${filteredTests.length} Tests`}
          </button>
        </div>
      </div>
      
      {/* Configuration Panel */}
      {showConfig && (
        <motion.div 
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="card p-4 mb-6"
        >
          <div className="flex items-center gap-2 mb-4">
            <CogIcon className="w-5 h-5 text-[var(--text-muted)]" />
            <h3 className="font-semibold text-[var(--text-primary)]">Test Configuration</h3>
          </div>
          
          <div className="grid grid-cols-4 gap-6">
            {/* Cloud Selection */}
            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-2">Clouds</label>
              <div className="space-y-1">
                {['aws', 'azure', 'gcp'].map(cloud => (
                  <label key={cloud} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={testConfig.clouds.includes(cloud)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setTestConfig({ ...testConfig, clouds: [...testConfig.clouds, cloud] })
                        } else {
                          setTestConfig({ ...testConfig, clouds: testConfig.clouds.filter(c => c !== cloud) })
                        }
                      }}
                      className="rounded"
                    />
                    {cloud.toUpperCase()}
                  </label>
                ))}
              </div>
            </div>
            
            {/* Sampling */}
            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-2">Sampling</label>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <label className="text-xs text-[var(--text-muted)] w-24">Regions/Cloud:</label>
                  <input
                    type="number"
                    min={1}
                    max={4}
                    value={testConfig.regionsPerCloud}
                    onChange={(e) => setTestConfig({ ...testConfig, regionsPerCloud: parseInt(e.target.value) || 1 })}
                    className="w-16 text-sm"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-xs text-[var(--text-muted)] w-24">Tiers/Cloud:</label>
                  <input
                    type="number"
                    min={1}
                    max={3}
                    value={testConfig.tiersPerCloud}
                    onChange={(e) => setTestConfig({ ...testConfig, tiersPerCloud: parseInt(e.target.value) || 1 })}
                    className="w-16 text-sm"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-xs text-[var(--text-muted)] w-24">VM Samples:</label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={testConfig.vmSamplesPerCloud}
                    onChange={(e) => setTestConfig({ ...testConfig, vmSamplesPerCloud: parseInt(e.target.value) || 1 })}
                    className="w-16 text-sm"
                  />
                </div>
              </div>
            </div>
            
            {/* Workload Types - Column 1 */}
            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-2">Workloads (1)</label>
              <div className="space-y-1">
                {[
                  { key: 'includeJobs', label: 'Jobs' },
                  { key: 'includeAllPurpose', label: 'All Purpose' },
                  { key: 'includeDLT', label: 'DLT' },
                  { key: 'includeDBSQL', label: 'DBSQL' },
                  { key: 'includeVectorSearch', label: 'Vector Search' }
                ].map(({ key, label }) => (
                  <label key={key} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={testConfig[key as keyof TestConfig] as boolean}
                      onChange={(e) => setTestConfig({ ...testConfig, [key]: e.target.checked })}
                      className="rounded"
                    />
                    {label}
                  </label>
                ))}
              </div>
            </div>
            
            {/* Workload Types - Column 2 */}
            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-2">Workloads (2)</label>
              <div className="space-y-1">
                {[
                  { key: 'includeModelServing', label: 'Model Serving' },
                  { key: 'includeFMAPIDB', label: 'FMAPI Databricks' },
                  { key: 'includeFMAPIProp', label: 'FMAPI Proprietary' },
                  { key: 'includeLakebase', label: 'Lakebase' }
                ].map(({ key, label }) => (
                  <label key={key} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={testConfig[key as keyof TestConfig] as boolean}
                      onChange={(e) => setTestConfig({ ...testConfig, [key]: e.target.checked })}
                      className="rounded"
                    />
                    {label}
                  </label>
                ))}
              </div>
            </div>
          </div>
          
          <div className="mt-4 pt-4 border-t border-[var(--border-primary)] flex items-center justify-between">
            <p className="text-sm text-[var(--text-muted)]">
              <span className="font-semibold text-[var(--text-primary)]">{testCases.length}</span> test cases will be generated
            </p>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <label className="text-xs text-[var(--text-muted)]">Tolerance %:</label>
                <input
                  type="number"
                  value={tolerancePercent}
                  onChange={(e) => setTolerancePercent(parseFloat(e.target.value) || 1)}
                  min={0}
                  max={100}
                  step={0.5}
                  className="w-16 text-sm"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-xs text-[var(--text-muted)]">Category:</label>
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="text-sm"
                >
                  {categories.map(cat => (
                    <option key={cat} value={cat}>
                      {cat === 'all' ? `All (${testCases.length})` : cat}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </motion.div>
      )}
      
      {/* Bundle Status */}
      <div className="card p-3 mb-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className={`flex items-center gap-2 ${isPricingBundleLoaded ? 'text-green-500' : 'text-yellow-500'}`}>
            {isPricingBundleLoaded ? <CheckCircleIcon className="w-5 h-5" /> : <ExclamationTriangleIcon className="w-5 h-5" />}
            <span className="text-sm font-medium">
              Pricing Bundle: {isPricingBundleLoaded ? 'Loaded' : 'Not Loaded (using fallbacks)'}
            </span>
          </div>
        </div>
        <div className="text-sm text-[var(--text-muted)]">
          Testing: {testConfig.clouds.map(c => c.toUpperCase()).join(', ')} • 
          {testConfig.regionsPerCloud} regions × {testConfig.tiersPerCloud} tiers × {testConfig.vmSamplesPerCloud} VMs
        </div>
      </div>
      
      {/* Stats */}
      {results.length > 0 && (
        <div className="grid grid-cols-5 gap-4 mb-6">
          <div className="card p-4 text-center">
            <p className="text-2xl font-bold text-green-500">{stats.passed}</p>
            <p className="text-xs text-[var(--text-muted)]">Passed</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-2xl font-bold text-red-500">{stats.failed}</p>
            <p className="text-xs text-[var(--text-muted)]">Failed</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-2xl font-bold text-yellow-500">{stats.apiErrors}</p>
            <p className="text-xs text-[var(--text-muted)]">API Errors</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-2xl font-bold text-blue-500">{stats.avgLocalTime.toFixed(1)}ms</p>
            <p className="text-xs text-[var(--text-muted)]">Avg Local</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-2xl font-bold text-purple-500">{stats.avgApiTime.toFixed(0)}ms</p>
            <p className="text-xs text-[var(--text-muted)]">Avg API</p>
          </div>
        </div>
      )}
      
      {/* Category Breakdown */}
      {results.length > 0 && Object.keys(stats.byCategory).length > 0 && (
        <div className="card p-4 mb-6">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-3">Results by Category</h3>
          <div className="flex flex-wrap gap-3">
            {Object.entries(stats.byCategory).map(([cat, { passed, failed }]) => (
              <div key={cat} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--bg-tertiary)]">
                <span className="text-sm text-[var(--text-primary)]">{cat}</span>
                <span className="text-xs text-green-500">{passed} ✓</span>
                {failed > 0 && <span className="text-xs text-red-500">{failed} ✗</span>}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Progress bar */}
      {running && (
        <div className="mb-6">
          <div className="h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-orange-500"
              initial={{ width: 0 }}
              animate={{ width: `${(progress.current / progress.total) * 100}%` }}
            />
          </div>
          <p className="text-xs text-[var(--text-muted)] mt-1 text-center">
            {progress.current} / {progress.total} tests completed
          </p>
        </div>
      )}
      
      {/* Results Table */}
      <div className="card overflow-hidden">
        <div className="max-h-[600px] overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="bg-[var(--bg-tertiary)] sticky top-0">
              <tr>
                <th className="text-left p-3 font-medium text-[var(--text-secondary)]">Test</th>
                <th className="text-left p-3 font-medium text-[var(--text-secondary)]">Category</th>
                <th className="text-left p-3 font-medium text-[var(--text-secondary)]">Environment</th>
                <th className="text-right p-3 font-medium text-[var(--text-secondary)]">Local</th>
                <th className="text-right p-3 font-medium text-[var(--text-secondary)]">API</th>
                <th className="text-right p-3 font-medium text-[var(--text-secondary)]">Diff %</th>
                <th className="text-center p-3 font-medium text-[var(--text-secondary)]">Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredTests.map((test) => {
                const result = results.find(r => r.testCase.id === test.id)
                const isExpanded = expandedResults.has(test.id)
                const isRunning = currentTest === test.id
                
                return (
                  <>
                    <tr
                      key={test.id}
                      className={`
                        border-t border-[var(--border-primary)] 
                        ${result && !result.matches ? 'bg-red-500/5' : ''}
                        ${isRunning ? 'bg-blue-500/10' : ''}
                        hover:bg-[var(--bg-hover)] cursor-pointer
                      `}
                      onClick={() => result && toggleExpanded(test.id)}
                    >
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          {result && (
                            isExpanded 
                              ? <ChevronDownIcon className="w-4 h-4 text-[var(--text-muted)]" />
                              : <ChevronRightIcon className="w-4 h-4 text-[var(--text-muted)]" />
                          )}
                          <span className="font-medium text-[var(--text-primary)] truncate max-w-[200px]" title={test.name}>
                            {test.name}
                          </span>
                        </div>
                      </td>
                      <td className="p-3 text-[var(--text-muted)]">{test.category}</td>
                      <td className="p-3">
                        <div className="flex items-center gap-1">
                          <span className="px-1.5 py-0.5 text-xs rounded bg-blue-500/10 text-blue-500">{test.environment.cloud}</span>
                          <span className="text-xs text-[var(--text-muted)]">{test.environment.region}</span>
                          <span className="px-1.5 py-0.5 text-xs rounded bg-purple-500/10 text-purple-500">{test.environment.tier}</span>
                        </div>
                      </td>
                      <td className="p-3 text-right font-mono text-[var(--text-primary)]">
                        {result ? formatCurrency(result.localResult.totalCost) : '-'}
                      </td>
                      <td className="p-3 text-right font-mono text-[var(--text-primary)]">
                        {result?.apiResult ? formatCurrency(result.apiResult.totalCost) : result?.apiError ? 'Error' : '-'}
                      </td>
                      <td className="p-3 text-right font-mono">
                        {result && result.discrepancies.length > 0 ? (
                          <span className="text-red-500">
                            {result.discrepancies.find(d => d.field === 'totalCost')?.diffPercent.toFixed(1) || 
                             result.discrepancies[0]?.diffPercent.toFixed(1)}%
                          </span>
                        ) : result ? (
                          <span className="text-green-500">0%</span>
                        ) : '-'}
                      </td>
                      <td className="p-3 text-center">
                        {isRunning ? (
                          <ArrowPathIcon className="w-5 h-5 text-blue-500 animate-spin mx-auto" />
                        ) : result ? (
                          result.matches ? (
                            <CheckCircleIcon className="w-5 h-5 text-green-500 mx-auto" />
                          ) : (
                            <XCircleIcon className="w-5 h-5 text-red-500 mx-auto" />
                          )
                        ) : (
                          <span className="text-[var(--text-muted)]">-</span>
                        )}
                      </td>
                    </tr>
                    
                    {/* Expanded details */}
                    {result && isExpanded && (
                      <tr key={`${test.id}-details`} className="bg-[var(--bg-tertiary)]">
                        <td colSpan={7} className="p-4">
                          <div className="grid grid-cols-2 gap-6">
                            {/* Local Result */}
                            <div>
                              <h4 className="font-semibold text-[var(--text-primary)] mb-2">Local Calculation</h4>
                              <div className="bg-[var(--bg-primary)] rounded-lg p-3 space-y-1 font-mono text-xs">
                                <div className="flex justify-between">
                                  <span className="text-[var(--text-muted)]">Monthly DBUs:</span>
                                  <span className="text-[var(--text-primary)]">{formatNumber(result.localResult.monthlyDBUs)}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-[var(--text-muted)]">DBU Cost:</span>
                                  <span className="text-[var(--text-primary)]">{formatCurrency(result.localResult.dbuCost)}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-[var(--text-muted)]">VM Cost:</span>
                                  <span className="text-[var(--text-primary)]">{formatCurrency(result.localResult.vmCost)}</span>
                                </div>
                                <div className="flex justify-between border-t border-[var(--border-primary)] pt-1 mt-1">
                                  <span className="text-[var(--text-secondary)] font-semibold">Total:</span>
                                  <span className="text-orange-500 font-semibold">{formatCurrency(result.localResult.totalCost)}</span>
                                </div>
                                {result.localResult.dbuPrice && (
                                  <div className="flex justify-between text-[10px]">
                                    <span className="text-[var(--text-muted)]">$/DBU:</span>
                                    <span className="text-pink-500">${result.localResult.dbuPrice.toFixed(2)}</span>
                                  </div>
                                )}
                              </div>
                            </div>
                            
                            {/* API Result */}
                            <div>
                              <h4 className="font-semibold text-[var(--text-primary)] mb-2">API Calculation</h4>
                              {result.apiError ? (
                                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                                  <p className="text-red-500 text-xs break-all">{result.apiError}</p>
                                </div>
                              ) : result.apiResult ? (
                                <div className="bg-[var(--bg-primary)] rounded-lg p-3 space-y-1 font-mono text-xs">
                                  <div className="flex justify-between">
                                    <span className="text-[var(--text-muted)]">Monthly DBUs:</span>
                                    <span className={result.discrepancies.some(d => d.field === 'monthlyDBUs') ? 'text-red-500' : 'text-[var(--text-primary)]'}>
                                      {formatNumber(result.apiResult.monthlyDBUs)}
                                    </span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-[var(--text-muted)]">DBU Cost:</span>
                                    <span className={result.discrepancies.some(d => d.field === 'dbuCost') ? 'text-red-500' : 'text-[var(--text-primary)]'}>
                                      {formatCurrency(result.apiResult.dbuCost)}
                                    </span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-[var(--text-muted)]">VM Cost:</span>
                                    <span className={result.discrepancies.some(d => d.field === 'vmCost') ? 'text-red-500' : 'text-[var(--text-primary)]'}>
                                      {formatCurrency(result.apiResult.vmCost)}
                                    </span>
                                  </div>
                                  <div className="flex justify-between border-t border-[var(--border-primary)] pt-1 mt-1">
                                    <span className="text-[var(--text-secondary)] font-semibold">Total:</span>
                                    <span className={result.discrepancies.some(d => d.field === 'totalCost') ? 'text-red-500 font-semibold' : 'text-orange-500 font-semibold'}>
                                      {formatCurrency(result.apiResult.totalCost)}
                                    </span>
                                  </div>
                                </div>
                              ) : null}
                            </div>
                          </div>
                          
                          {/* Discrepancies */}
                          {result.discrepancies.length > 0 && (
                            <div className="mt-4">
                              <h4 className="font-semibold text-red-500 mb-2">Discrepancies</h4>
                              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                                <table className="w-full text-xs">
                                  <thead>
                                    <tr className="text-red-400">
                                      <th className="text-left pb-1">Field</th>
                                      <th className="text-right pb-1">Local</th>
                                      <th className="text-right pb-1">API</th>
                                      <th className="text-right pb-1">Diff</th>
                                      <th className="text-right pb-1">Diff %</th>
                                    </tr>
                                  </thead>
                                  <tbody className="font-mono">
                                    {result.discrepancies.map((d, i) => (
                                      <tr key={i} className="text-red-300">
                                        <td className="py-0.5">{d.field}</td>
                                        <td className="text-right">{d.local.toFixed(2)}</td>
                                        <td className="text-right">{d.api.toFixed(2)}</td>
                                        <td className="text-right">{d.diff.toFixed(2)}</td>
                                        <td className="text-right">{d.diffPercent.toFixed(2)}%</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}
                          
                          {/* Test Config */}
                          <div className="mt-4">
                            <h4 className="font-semibold text-[var(--text-secondary)] mb-2">Test Configuration</h4>
                            <pre className="bg-[var(--bg-primary)] rounded-lg p-3 text-xs overflow-x-auto">
                              {JSON.stringify({ environment: result.testCase.environment, config: result.testCase.config }, null, 2)}
                            </pre>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
