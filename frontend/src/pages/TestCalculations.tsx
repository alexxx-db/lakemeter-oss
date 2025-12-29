import { useState, useMemo } from 'react'
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
  ExclamationTriangleIcon
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

// Test case definition
interface TestCase {
  id: string
  name: string
  category: string
  workloadType: string
  config: Partial<LineItem>
  description?: string
}

// Test result
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

// Comprehensive test cases for all workload types
const TEST_CASES: TestCase[] = [
  // ===== JOBS =====
  {
    id: 'jobs-classic-standard',
    name: 'Jobs Classic - No Photon',
    category: 'Jobs',
    workloadType: 'JOBS',
    config: {
      serverless_enabled: false,
      photon_enabled: false,
      driver_node_type: 'c5.4xlarge',
      worker_node_type: 'c5.4xlarge',
      num_workers: 2,
      driver_pricing_tier: 'on_demand',
      worker_pricing_tier: 'spot',
      runs_per_day: 1,
      avg_runtime_minutes: 30,
      days_per_month: 22
    }
  },
  {
    id: 'jobs-classic-photon',
    name: 'Jobs Classic - Photon Enabled',
    category: 'Jobs',
    workloadType: 'JOBS',
    config: {
      serverless_enabled: false,
      photon_enabled: true,
      driver_node_type: 'c5.4xlarge',
      worker_node_type: 'c5.4xlarge',
      num_workers: 4,
      driver_pricing_tier: 'on_demand',
      worker_pricing_tier: 'spot',
      runs_per_day: 2,
      avg_runtime_minutes: 60,
      days_per_month: 22
    }
  },
  {
    id: 'jobs-serverless-standard',
    name: 'Jobs Serverless - Standard Mode',
    category: 'Jobs',
    workloadType: 'JOBS',
    config: {
      serverless_enabled: true,
      serverless_mode: 'standard',
      driver_node_type: 'c5.4xlarge',
      worker_node_type: 'c5.4xlarge',
      num_workers: 2,
      runs_per_day: 1,
      avg_runtime_minutes: 30,
      days_per_month: 22
    }
  },
  {
    id: 'jobs-serverless-performance',
    name: 'Jobs Serverless - Performance Mode',
    category: 'Jobs',
    workloadType: 'JOBS',
    config: {
      serverless_enabled: true,
      serverless_mode: 'performance',
      driver_node_type: 'c5.4xlarge',
      worker_node_type: 'c5.4xlarge',
      num_workers: 2,
      runs_per_day: 1,
      avg_runtime_minutes: 30,
      days_per_month: 22
    }
  },
  
  // ===== ALL PURPOSE =====
  {
    id: 'ap-classic-standard',
    name: 'All Purpose Classic - No Photon',
    category: 'All Purpose',
    workloadType: 'ALL_PURPOSE',
    config: {
      serverless_enabled: false,
      photon_enabled: false,
      driver_node_type: 'm5.xlarge',
      worker_node_type: 'm5.xlarge',
      num_workers: 2,
      driver_pricing_tier: 'on_demand',
      worker_pricing_tier: 'on_demand',
      hours_per_month: 160
    }
  },
  {
    id: 'ap-serverless-standard',
    name: 'All Purpose Serverless - Standard',
    category: 'All Purpose',
    workloadType: 'ALL_PURPOSE',
    config: {
      serverless_enabled: true,
      serverless_mode: 'standard',
      driver_node_type: 'm5.xlarge',
      worker_node_type: 'm5.xlarge',
      num_workers: 2,
      hours_per_month: 160
    }
  },
  
  // ===== DLT =====
  {
    id: 'dlt-classic-core',
    name: 'DLT Classic - Core Edition',
    category: 'DLT',
    workloadType: 'DLT',
    config: {
      serverless_enabled: false,
      photon_enabled: false,
      dlt_edition: 'CORE',
      driver_node_type: 'c5.4xlarge',
      worker_node_type: 'c5.4xlarge',
      num_workers: 2,
      driver_pricing_tier: 'on_demand',
      worker_pricing_tier: 'spot',
      runs_per_day: 4,
      avg_runtime_minutes: 30,
      days_per_month: 30
    }
  },
  {
    id: 'dlt-classic-pro',
    name: 'DLT Classic - Pro Edition',
    category: 'DLT',
    workloadType: 'DLT',
    config: {
      serverless_enabled: false,
      photon_enabled: true,
      dlt_edition: 'PRO',
      driver_node_type: 'c5.4xlarge',
      worker_node_type: 'c5.4xlarge',
      num_workers: 4,
      driver_pricing_tier: 'on_demand',
      worker_pricing_tier: 'spot',
      runs_per_day: 6,
      avg_runtime_minutes: 45,
      days_per_month: 30
    }
  },
  {
    id: 'dlt-serverless',
    name: 'DLT Serverless',
    category: 'DLT',
    workloadType: 'DLT',
    config: {
      serverless_enabled: true,
      serverless_mode: 'standard',
      driver_node_type: 'c5.4xlarge',
      worker_node_type: 'c5.4xlarge',
      num_workers: 2,
      runs_per_day: 4,
      avg_runtime_minutes: 30,
      days_per_month: 30
    }
  },
  
  // ===== DBSQL =====
  {
    id: 'dbsql-serverless-small',
    name: 'DBSQL Serverless - Small',
    category: 'DBSQL',
    workloadType: 'DBSQL',
    config: {
      dbsql_warehouse_type: 'SERVERLESS',
      dbsql_warehouse_size: 'Small',
      dbsql_num_clusters: 1,
      hours_per_month: 160
    }
  },
  {
    id: 'dbsql-serverless-medium',
    name: 'DBSQL Serverless - Medium',
    category: 'DBSQL',
    workloadType: 'DBSQL',
    config: {
      dbsql_warehouse_type: 'SERVERLESS',
      dbsql_warehouse_size: 'Medium',
      dbsql_num_clusters: 2,
      hours_per_month: 200
    }
  },
  {
    id: 'dbsql-pro-small',
    name: 'DBSQL Pro - Small',
    category: 'DBSQL',
    workloadType: 'DBSQL',
    config: {
      dbsql_warehouse_type: 'PRO',
      dbsql_warehouse_size: 'Small',
      dbsql_num_clusters: 1,
      dbsql_driver_pricing_tier: 'on_demand',
      dbsql_worker_pricing_tier: 'spot',
      hours_per_month: 160
    }
  },
  {
    id: 'dbsql-classic-medium',
    name: 'DBSQL Classic - Medium',
    category: 'DBSQL',
    workloadType: 'DBSQL',
    config: {
      dbsql_warehouse_type: 'CLASSIC',
      dbsql_warehouse_size: 'Medium',
      dbsql_num_clusters: 1,
      dbsql_driver_pricing_tier: 'on_demand',
      dbsql_worker_pricing_tier: 'spot',
      hours_per_month: 100
    }
  },
  
  // ===== VECTOR SEARCH =====
  {
    id: 'vs-standard-1m',
    name: 'Vector Search Standard - 1M',
    category: 'Vector Search',
    workloadType: 'VECTOR_SEARCH',
    config: {
      vector_search_mode: 'standard',
      vector_capacity_millions: 1,
      hours_per_month: 730
    }
  },
  {
    id: 'vs-standard-5m',
    name: 'Vector Search Standard - 5M',
    category: 'Vector Search',
    workloadType: 'VECTOR_SEARCH',
    config: {
      vector_search_mode: 'standard',
      vector_capacity_millions: 5,
      hours_per_month: 730
    }
  },
  {
    id: 'vs-storage-optimized-64m',
    name: 'Vector Search Storage Optimized - 64M',
    category: 'Vector Search',
    workloadType: 'VECTOR_SEARCH',
    config: {
      vector_search_mode: 'storage_optimized',
      vector_capacity_millions: 64,
      hours_per_month: 730
    }
  },
  
  // ===== MODEL SERVING =====
  {
    id: 'ms-cpu',
    name: 'Model Serving - CPU',
    category: 'Model Serving',
    workloadType: 'MODEL_SERVING',
    config: {
      model_serving_gpu_type: 'cpu',
      hours_per_month: 730
    }
  },
  {
    id: 'ms-gpu-small',
    name: 'Model Serving - GPU Small (T4)',
    category: 'Model Serving',
    workloadType: 'MODEL_SERVING',
    config: {
      model_serving_gpu_type: 'gpu_small_t4',
      hours_per_month: 200
    }
  },
  
  // ===== LAKEBASE =====
  {
    id: 'lakebase-cu2-1node',
    name: 'Lakebase - 2 CU, 1 Node',
    category: 'Lakebase',
    workloadType: 'LAKEBASE',
    config: {
      lakebase_cu: 2,
      lakebase_ha_nodes: 1,
      hours_per_month: 730
    }
  },
  {
    id: 'lakebase-cu4-2nodes',
    name: 'Lakebase - 4 CU, 2 Nodes (HA)',
    category: 'Lakebase',
    workloadType: 'LAKEBASE',
    config: {
      lakebase_cu: 4,
      lakebase_ha_nodes: 2,
      hours_per_month: 730
    }
  },
  
  // ===== FMAPI DATABRICKS =====
  {
    id: 'fmapi-db-llama-input',
    name: 'FMAPI Databricks - Llama Input Tokens',
    category: 'FMAPI',
    workloadType: 'FMAPI_DATABRICKS',
    config: {
      fmapi_model: 'llama-3-1-70b',
      fmapi_rate_type: 'input_token',
      fmapi_quantity: 10 // 10M tokens
    }
  },
  
  // ===== FMAPI PROPRIETARY =====
  {
    id: 'fmapi-prop-gpt4o',
    name: 'FMAPI Proprietary - GPT-4o Input',
    category: 'FMAPI',
    workloadType: 'FMAPI_PROPRIETARY',
    config: {
      fmapi_provider: 'openai',
      fmapi_model: 'gpt-4o',
      fmapi_endpoint_type: 'global',
      fmapi_context_length: 'all',
      fmapi_rate_type: 'input_token',
      fmapi_quantity: 5 // 5M tokens
    }
  },
  {
    id: 'fmapi-prop-claude',
    name: 'FMAPI Proprietary - Claude Sonnet',
    category: 'FMAPI',
    workloadType: 'FMAPI_PROPRIETARY',
    config: {
      fmapi_provider: 'anthropic',
      fmapi_model: 'claude-sonnet-4',
      fmapi_endpoint_type: 'global',
      fmapi_context_length: 'long',
      fmapi_rate_type: 'input_token',
      fmapi_quantity: 5
    }
  }
]

// API endpoint mapping for different workload types
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
function buildAPIRequest(
  testCase: TestCase, 
  cloud: string, 
  region: string, 
  tier: string
): Record<string, unknown> {
  const { workloadType, config } = testCase
  const base = { cloud, region, tier }
  
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

// Compare two cost breakdowns
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

export default function TestCalculations() {
  const [results, setResults] = useState<TestResult[]>([])
  const [running, setRunning] = useState(false)
  const [currentTest, setCurrentTest] = useState<string | null>(null)
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set())
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [tolerancePercent, setTolerancePercent] = useState(1)
  
  const {
    selectedCloud,
    selectedRegion,
    selectedTier,
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
  
  // Build context for local calculations
  const context: CostCalculationContext = useMemo(() => ({
    cloud: selectedCloud || 'aws',
    region: selectedRegion || 'us-east-1',
    tier: selectedTier || 'PREMIUM',
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
        const cloud = (selectedCloud || 'aws').toLowerCase()
        const ep = endpointType || 'global'
        const ctx = contextLength || 'all'
        const key = `${cloud}:${provider.toLowerCase()}:${model.toLowerCase()}:${ep}:${ctx}:${rateType}`
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
      return getBundleInstanceDBURate(pricingBundle, selectedCloud || 'aws', instanceType)
    },
    getPhotonMultiplier: (skuType: string) => {
      if (!isPricingBundleLoaded) return null
      return getBundlePhotonMultiplier(pricingBundle, selectedCloud || 'aws', skuType)
    },
    getDBUPrice: (productType: string) => {
      if (!isPricingBundleLoaded) return null
      return getBundleDBUPrice(pricingBundle, selectedCloud || 'aws', selectedRegion || '', selectedTier || 'PREMIUM', productType)
    },
    getDBSQLWarehouseConfig: (warehouseType: string, warehouseSize: string) => {
      if (!isPricingBundleLoaded) return null
      return getDBSQLWarehouseConfig(pricingBundle, selectedCloud || 'aws', warehouseType, warehouseSize)
    }
  }), [selectedCloud, selectedRegion, selectedTier, dbuRatesMap, instanceTypes, dbsqlSizes, photonMultipliers, modelServingGPUTypes, vectorSearchModes, isPricingBundleLoaded, pricingBundle, getVMPrice, getFMAPIDatabricksRate, getFMAPIProprietaryRate, getVectorSearchRate])
  
  // Filter test cases by category
  const filteredTests = useMemo(() => {
    if (selectedCategory === 'all') return TEST_CASES
    return TEST_CASES.filter(t => t.category === selectedCategory)
  }, [selectedCategory])
  
  // Get unique categories
  const categories = useMemo(() => {
    const cats = new Set(TEST_CASES.map(t => t.category))
    return ['all', ...Array.from(cats)]
  }, [])
  
  // Run a single test
  const runSingleTest = async (testCase: TestCase): Promise<TestResult> => {
    const lineItem: Partial<LineItem> = {
      ...testCase.config,
      workload_type: testCase.workloadType
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
      const endpoint = getAPIEndpoint(testCase.workloadType, testCase.config)
      const body = buildAPIRequest(testCase, selectedCloud || 'aws', selectedRegion || 'us-east-1', selectedTier || 'PREMIUM')
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
      
      if (response.ok) {
        const data = await response.json()
        apiResult = {
          monthlyDBUs: data.dbu_per_month || data.dbu_per_hour * (testCase.config.hours_per_month || 730) || 0,
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
    
    // Compare results
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
    
    for (const testCase of filteredTests) {
      setCurrentTest(testCase.id)
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
    return { passed, failed, apiErrors, avgLocalTime, avgApiTime }
  }, [results])
  
  // Export results to CSV
  const exportCSV = () => {
    const headers = ['Test Name', 'Category', 'Status', 'Local Total', 'API Total', 'Diff %', 'Local Time (ms)', 'API Time (ms)', 'Error']
    const rows = results.map(r => [
      r.testCase.name,
      r.testCase.category,
      r.matches ? 'PASS' : 'FAIL',
      r.localResult.totalCost.toFixed(2),
      r.apiResult?.totalCost.toFixed(2) || 'N/A',
      r.discrepancies[0]?.diffPercent.toFixed(2) || '0',
      r.localTimeMs.toFixed(1),
      r.apiTimeMs.toFixed(1),
      r.apiError || ''
    ])
    
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
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
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">Calculation Tests</h1>
            <p className="text-sm text-[var(--text-muted)]">
              Compare local frontend calculations vs API results
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
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
            disabled={running || !selectedRegion}
            className="btn btn-primary flex items-center gap-2"
          >
            {running ? (
              <ArrowPathIcon className="w-4 h-4 animate-spin" />
            ) : (
              <PlayIcon className="w-4 h-4" />
            )}
            {running ? 'Running...' : 'Run All Tests'}
          </button>
        </div>
      </div>
      
      {/* Warning if no region selected */}
      {!selectedRegion && (
        <div className="mb-6 p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30 flex items-center gap-3">
          <ExclamationTriangleIcon className="w-5 h-5 text-yellow-500" />
          <p className="text-sm text-yellow-600 dark:text-yellow-400">
            Please select a region in the main calculator before running tests.
          </p>
        </div>
      )}
      
      {/* Config & Filters */}
      <div className="card p-4 mb-6">
        <div className="flex flex-wrap items-center gap-4">
          <div>
            <label className="block text-xs font-medium text-[var(--text-muted)] mb-1">Environment</label>
            <div className="text-sm font-mono text-[var(--text-primary)]">
              {selectedCloud?.toUpperCase() || 'AWS'} / {selectedRegion || 'us-east-1'} / {selectedTier || 'PREMIUM'}
            </div>
          </div>
          
          <div>
            <label className="block text-xs font-medium text-[var(--text-muted)] mb-1">Category Filter</label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="text-sm"
            >
              {categories.map(cat => (
                <option key={cat} value={cat}>
                  {cat === 'all' ? 'All Categories' : cat}
                </option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-xs font-medium text-[var(--text-muted)] mb-1">Tolerance %</label>
            <input
              type="number"
              value={tolerancePercent}
              onChange={(e) => setTolerancePercent(parseFloat(e.target.value) || 1)}
              min={0}
              max={100}
              step={0.5}
              className="w-20 text-sm"
            />
          </div>
          
          <div>
            <label className="block text-xs font-medium text-[var(--text-muted)] mb-1">Tests</label>
            <div className="text-sm text-[var(--text-primary)]">
              {filteredTests.length} test cases
            </div>
          </div>
          
          <div>
            <label className="block text-xs font-medium text-[var(--text-muted)] mb-1">Bundle Status</label>
            <div className={`text-sm ${isPricingBundleLoaded ? 'text-green-500' : 'text-yellow-500'}`}>
              {isPricingBundleLoaded ? '✓ Loaded' : '⚠ Not loaded'}
            </div>
          </div>
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
            <p className="text-xs text-[var(--text-muted)]">Avg Local Time</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-2xl font-bold text-purple-500">{stats.avgApiTime.toFixed(0)}ms</p>
            <p className="text-xs text-[var(--text-muted)]">Avg API Time</p>
          </div>
        </div>
      )}
      
      {/* Results Table */}
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[var(--bg-tertiary)]">
            <tr>
              <th className="text-left p-3 font-medium text-[var(--text-secondary)]">Test</th>
              <th className="text-left p-3 font-medium text-[var(--text-secondary)]">Category</th>
              <th className="text-right p-3 font-medium text-[var(--text-secondary)]">Local</th>
              <th className="text-right p-3 font-medium text-[var(--text-secondary)]">API</th>
              <th className="text-right p-3 font-medium text-[var(--text-secondary)]">Diff %</th>
              <th className="text-right p-3 font-medium text-[var(--text-secondary)]">Time</th>
              <th className="text-center p-3 font-medium text-[var(--text-secondary)]">Status</th>
            </tr>
          </thead>
          <tbody>
            {filteredTests.map((test) => {
              const result = results.find(r => r.testCase.id === test.id)
              const isExpanded = expandedResults.has(test.id)
              const isRunning = currentTest === test.id
              
              return (
                <motion.tr
                  key={test.id}
                  initial={false}
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
                      <span className="font-medium text-[var(--text-primary)]">{test.name}</span>
                    </div>
                  </td>
                  <td className="p-3 text-[var(--text-muted)]">{test.category}</td>
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
                  <td className="p-3 text-right font-mono text-[var(--text-muted)]">
                    {result ? `${result.localTimeMs.toFixed(0)}/${result.apiTimeMs.toFixed(0)}ms` : '-'}
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
                </motion.tr>
              )
            })}
            
            {/* Expanded details row */}
            {results.map((result) => {
              if (!expandedResults.has(result.testCase.id)) return null
              
              return (
                <tr key={`${result.testCase.id}-details`} className="bg-[var(--bg-tertiary)]">
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
                          {result.localResult.dbuPerHour && (
                            <div className="flex justify-between text-[10px]">
                              <span className="text-[var(--text-muted)]">DBU/hr:</span>
                              <span className="text-purple-500">{result.localResult.dbuPerHour.toFixed(2)}</span>
                            </div>
                          )}
                        </div>
                      </div>
                      
                      {/* API Result */}
                      <div>
                        <h4 className="font-semibold text-[var(--text-primary)] mb-2">API Calculation</h4>
                        {result.apiError ? (
                          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                            <p className="text-red-500 text-xs">{result.apiError}</p>
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
                        ) : (
                          <div className="bg-[var(--bg-primary)] rounded-lg p-3">
                            <p className="text-[var(--text-muted)] text-xs">No result</p>
                          </div>
                        )}
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
                        {JSON.stringify(result.testCase.config, null, 2)}
                      </pre>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

