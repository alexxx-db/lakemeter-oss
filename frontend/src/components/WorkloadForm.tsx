import { useState, useEffect, useMemo } from 'react'
import { BoltIcon, CloudIcon, CurrencyDollarIcon, ArrowTrendingUpIcon, ArrowTrendingDownIcon, InformationCircleIcon, ChevronDownIcon, ChevronRightIcon } from '@heroicons/react/24/outline'
import clsx from 'clsx'
import toast from 'react-hot-toast'
import { useStore } from '../store/useStore'
import SearchableSelect from './SearchableSelect'
import type { LineItem, WorkloadType } from '../types'
import { calculateWorkloadCost, type CostCalculationContext } from '../utils/costCalculation'
import { 
  getDBSQLWarehouseConfig, 
  getInstanceDBURate as getBundleInstanceDBURate, 
  getPhotonMultiplier as getBundlePhotonMultiplier,
  getDBUPrice as getBundleDBUPrice,
  type PricingBundle 
} from '../utils/pricingBundle'

// Helper to get available context lengths for FMAPI Proprietary models from pricing bundle
function getAvailableContextLengths(
  bundle: PricingBundle,
  cloud: string,
  provider: string,
  model: string
): string[] {
  if (!bundle.isLoaded || !bundle.fmapiProprietaryRates) return ['all', 'short', 'long']
  
  const contextLengths = new Set<string>()
  const prefix = `${cloud.toLowerCase()}:${provider.toLowerCase()}:${model.toLowerCase()}:`
  
  Object.keys(bundle.fmapiProprietaryRates).forEach(key => {
    if (key.startsWith(prefix)) {
      // Key format: cloud:provider:model:endpoint:context:rate_type
      const parts = key.split(':')
      if (parts.length >= 5) {
        contextLengths.add(parts[4])
      }
    }
  })
  
  // Return sorted array, or default if none found
  const result = Array.from(contextLengths)
  return result.length > 0 ? result.sort() : ['all', 'short', 'long']
}

// Helper to get available rate types for FMAPI Proprietary models
function getAvailableRateTypes(
  bundle: PricingBundle,
  cloud: string,
  provider: string,
  model: string,
  endpointType: string,
  contextLength: string
): string[] {
  if (!bundle.isLoaded || !bundle.fmapiProprietaryRates) {
    return ['input_token', 'output_token', 'cache_read', 'cache_write']
  }
  
  const rateTypes = new Set<string>()
  const prefix = `${cloud.toLowerCase()}:${provider.toLowerCase()}:${model.toLowerCase()}:${endpointType}:${contextLength}:`
  
  Object.keys(bundle.fmapiProprietaryRates).forEach(key => {
    if (key.startsWith(prefix)) {
      const parts = key.split(':')
      if (parts.length >= 6) {
        rateTypes.add(parts[5])
      }
    }
  })
  
  const result = Array.from(rateTypes)
  return result.length > 0 ? result : ['input_token', 'output_token', 'cache_read', 'cache_write']
}

// ===== TIER-BASED WORKLOAD RESTRICTIONS =====
// STANDARD tier only supports classic (non-serverless) workloads:
// - JOBS_COMPUTE, JOBS_COMPUTE_(PHOTON)
// - ALL_PURPOSE_COMPUTE, ALL_PURPOSE_COMPUTE_(DLT)
// - DLT_CORE_COMPUTE, DLT_PRO_COMPUTE, DLT_ADVANCED_COMPUTE (+ PHOTON variants)
// - SQL_COMPUTE

// Workload types that are ONLY available on PREMIUM/ENTERPRISE tiers
// These workloads should be disabled/hidden when STANDARD tier is selected
const PREMIUM_ONLY_WORKLOAD_TYPES = new Set([
  'VECTOR_SEARCH',
  'MODEL_SERVING',
  'FMAPI_DATABRICKS',
  'FMAPI_PROPRIETARY',
  'LAKEBASE',
])

// Helper to check if a workload type is available for the selected tier
function isWorkloadAvailableForTier(
  workloadType: string,
  tier: string | null,
  serverlessEnabled: boolean = false,
  dbsqlWarehouseType?: string
): { available: boolean; reason?: string } {
  const tierUpper = tier?.toUpperCase() || 'PREMIUM'
  
  // PREMIUM and ENTERPRISE support everything
  if (tierUpper !== 'STANDARD') {
    return { available: true }
  }
  
  // STANDARD tier restrictions
  
  // Serverless is not available on STANDARD
  if (serverlessEnabled) {
    return { 
      available: false, 
      reason: 'Serverless workloads require Premium or Enterprise tier' 
    }
  }
  
  // DBSQL Serverless is not available on STANDARD
  if (workloadType === 'DBSQL' && dbsqlWarehouseType === 'SERVERLESS') {
    return { 
      available: false, 
      reason: 'DBSQL Serverless requires Premium or Enterprise tier' 
    }
  }
  
  // Premium-only workload types
  if (PREMIUM_ONLY_WORKLOAD_TYPES.has(workloadType)) {
    return { 
      available: false, 
      reason: `${workloadType.replace(/_/g, ' ')} requires Premium or Enterprise tier` 
    }
  }
  
  // Classic compute workloads are available on STANDARD
  return { available: true }
}

// Pricing tier tooltips
const PRICING_TIER_TOOLTIPS: Record<string, { title: string; description: string }> = {
  spot: {
    title: 'Spot Instances',
    description: 'Up to 90% cheaper than On-Demand, but can be interrupted with 2-minute notice. Best for fault-tolerant workloads.'
  },
  on_demand: {
    title: 'On-Demand',
    description: 'Standard pricing with guaranteed availability. No interruptions, pay by the hour.'
  },
  reserved_1y: {
    title: '1-Year Reserved',
    description: 'Commit to 1 year for 30-40% savings. Best for predictable, steady-state workloads.'
  },
  reserved_3y: {
    title: '3-Year Reserved',
    description: 'Commit to 3 years for 50-60% savings. Maximum savings for long-term workloads.'
  }
}

// Tooltip component
function PricingTierTooltip({ tier }: { tier: string }) {
  const [show, setShow] = useState(false)
  const info = PRICING_TIER_TOOLTIPS[tier]
  
  if (!info) return null
  
  return (
    <div className="relative inline-block ml-1">
      <button
        type="button"
        className="text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors"
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        onClick={(e) => { e.preventDefault(); setShow(!show) }}
      >
        <InformationCircleIcon className="w-3.5 h-3.5" />
      </button>
      {show && (
        <div className="absolute left-0 bottom-full mb-2 w-56 p-2.5 bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-lg shadow-lg z-50">
          <p className="text-xs font-semibold text-[var(--text-primary)] mb-1">{info.title}</p>
          <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">{info.description}</p>
          <div className="absolute left-3 bottom-0 translate-y-1/2 rotate-45 w-2 h-2 bg-[var(--bg-primary)] border-r border-b border-[var(--border-primary)]" />
        </div>
      )}
    </div>
  )
}

// Collapsible Notes component
function CollapsibleNotes({ notes, onChange }: { notes: string; onChange: (value: string) => void }) {
  const [isExpanded, setIsExpanded] = useState(!!notes) // Expand if has content
  
  return (
    <div className="border border-[var(--border-primary)] rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-center justify-between bg-[var(--bg-tertiary)] hover:bg-[var(--bg-hover)] transition-colors"
      >
        <span className="text-xs font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
          {isExpanded ? <ChevronDownIcon className="w-3.5 h-3.5" /> : <ChevronRightIcon className="w-3.5 h-3.5" />}
          Notes
          {notes && !isExpanded && (
            <span className="ml-1 text-[var(--text-muted)] font-normal truncate max-w-[200px]">
              — {notes.split('\n')[0].substring(0, 40)}{notes.length > 40 ? '...' : ''}
            </span>
          )}
        </span>
        <span className="text-[10px] text-[var(--text-muted)]">
          {isExpanded ? 'Click to collapse' : 'Click to expand'}
        </span>
      </button>
      {isExpanded && (
        <div className="p-3 bg-[var(--bg-primary)]">
          <textarea
            value={notes}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Configuration rationale and assumptions...&#10;• Why this configuration was chosen&#10;• Sizing assumptions (data volume, users, etc.)&#10;• Cost optimization choices"
            className="w-full text-sm min-h-[60px] resize-y border-0 bg-transparent p-0 focus:ring-0"
            rows={2}
          />
        </div>
      )}
    </div>
  )
}

interface Props {
  estimateId: string
  lineItem: LineItem | null
  onClose: () => void
  onSave?: () => void
  inline?: boolean
}

export default function WorkloadForm({ estimateId, lineItem, onClose, onSave, inline: _inline = false }: Props) {
  const { 
    workloadTypes, 
    instanceTypes, 
    dbsqlSizes: storeDbsqlSizes, 
    dltEditions, 
    vmPaymentOptions,
    modelServingGPUTypes,
    vectorSearchModes,
    fmapiDatabricksConfig,
    fmapiProprietaryConfig,
    selectedCloud,
    selectedRegion,
    selectedTier,
    dbuRatesMap,
    photonMultipliers,
    pricingBundle,
    isPricingBundleLoaded,
    createLineItem,
    updateLineItem,
    fetchLineItems,
    clearSingleWorkloadCost,
    markItemCalculating,
    getVMPrice,
    getFMAPIDatabricksRate,
    getFMAPIProprietaryRate,
    getVectorSearchRate
  } = useStore()
  
  // Fallback DBSQL sizes if store hasn't loaded yet
  const defaultDbsqlSizes = [
    { id: '2X-Small', name: '2X-Small', dbu_per_hour: 4 },
    { id: 'X-Small', name: 'X-Small', dbu_per_hour: 6 },
    { id: 'Small', name: 'Small', dbu_per_hour: 12 },
    { id: 'Medium', name: 'Medium', dbu_per_hour: 24 },
    { id: 'Large', name: 'Large', dbu_per_hour: 40 },
    { id: 'X-Large', name: 'X-Large', dbu_per_hour: 80 },
    { id: '2X-Large', name: '2X-Large', dbu_per_hour: 144 },
    { id: '3X-Large', name: '3X-Large', dbu_per_hour: 272 },
    { id: '4X-Large', name: '4X-Large', dbu_per_hour: 528 },
  ]
  const dbsqlSizes = storeDbsqlSizes.length > 0 ? storeDbsqlSizes : defaultDbsqlSizes
  
  // Fallback DLT editions if store hasn't loaded yet
  const defaultDltEditions = [
    { id: 'CORE', name: 'Core' },
    { id: 'PRO', name: 'Pro' },
    { id: 'ADVANCED', name: 'Advanced' },
  ]
  const dltEditionOptions = dltEditions.length > 0 ? dltEditions : defaultDltEditions
  
  // Fallback Serverless modes
  const serverlessModeOptions = [
    { id: 'standard', name: 'Standard', description: 'Cost-optimized for general workloads' },
    { id: 'performance', name: 'Performance', description: 'Optimized for faster execution' },
  ]
  
  // Fallback VM Payment Options for AWS Reserved instances
  const defaultVmPaymentOptions = [
    { id: 'no_upfront', name: 'No Upfront' },
    { id: 'partial_upfront', name: 'Partial Upfront' },
    { id: 'all_upfront', name: 'All Upfront' },
  ]
  const paymentOptions = vmPaymentOptions.length > 0 ? vmPaymentOptions : defaultVmPaymentOptions
  
  // Fallback FMAPI Databricks config if store hasn't loaded yet
  const defaultFmapiDatabricksConfig = {
    model_types: [
      { id: 'llm', name: 'LLMs', has_output_tokens: true },
      { id: 'embedding', name: 'Embedding Models', has_output_tokens: false },
    ],
    models: {
      llm: [
        { id: 'llama-4-maverick', name: 'Llama 4 Maverick' },
        { id: 'llama-3-3-70b', name: 'Llama 3.3 70B' },
        { id: 'llama-3-1-8b', name: 'Llama 3.1 8B' },
        { id: 'llama-3-2-3b', name: 'Llama 3.2 3B' },
        { id: 'llama-3-2-1b', name: 'Llama 3.2 1B' },
        { id: 'gpt-oss-120b', name: 'GPT-OSS 120B' },
        { id: 'gpt-oss-20b', name: 'GPT-OSS 20B' },
        { id: 'gemma-3-12b', name: 'Gemma 3 12B' },
      ],
      embedding: [
        { id: 'bge-large', name: 'BGE Large' },
        { id: 'gte', name: 'GTE' },
      ],
    },
    inference_types: [
      { id: 'pay_per_token', name: 'Pay-Per-Token' },
      { id: 'provisioned_throughput', name: 'Provisioned Throughput' },
      { id: 'batch_inference', name: 'Batch Inference' },
    ],
  }
  const fmapiDatabricksModels = fmapiDatabricksConfig || defaultFmapiDatabricksConfig
  
  // Fallback FMAPI Proprietary config if store hasn't loaded yet
  // Models from lakemeter.sync_product_fmapi_proprietary
  const defaultFmapiProprietaryConfig = {
    providers: [
      {
        id: 'anthropic',
        name: 'Anthropic',
        models: [
          { id: 'claude-sonnet-3-7', name: 'Claude Sonnet 3.7' },
          { id: 'claude-sonnet-4', name: 'Claude Sonnet 4' },
          { id: 'claude-sonnet-4-1', name: 'Claude Sonnet 4.1' },
          { id: 'claude-sonnet-4-5', name: 'Claude Sonnet 4.5' },
          { id: 'claude-opus-4', name: 'Claude Opus 4' },
          { id: 'claude-opus-4-1', name: 'Claude Opus 4.1' },
          { id: 'claude-opus-4-5', name: 'Claude Opus 4.5' },
          { id: 'claude-haiku-4-5', name: 'Claude Haiku 4.5' },
        ],
      },
      {
        id: 'openai',
        name: 'OpenAI',
        models: [
          { id: 'gpt-5', name: 'GPT-5' },
          { id: 'gpt-5-1', name: 'GPT-5.1' },
          { id: 'gpt-5-mini', name: 'GPT-5 Mini' },
          { id: 'gpt-5-nano', name: 'GPT-5 Nano' },
        ],
      },
      {
        id: 'google',
        name: 'Google',
        models: [
          { id: 'gemini-2-5-flash', name: 'Gemini 2.5 Flash' },
          { id: 'gemini-2-5-pro', name: 'Gemini 2.5 Pro' },
        ],
      },
    ],
    endpoint_types: [
      { id: 'global', name: 'Global' },
      { id: 'in_geo', name: 'In-Geo (Regional)' },
    ],
    context_lengths: [
      { id: 'all', name: 'All' },
      { id: 'short', name: 'Short' },
      { id: 'long', name: 'Long' },
    ],
  }
  const fmapiProprietaryModels = fmapiProprietaryConfig || defaultFmapiProprietaryConfig
  
  const [isSaving, setIsSaving] = useState(false)
  const [useDirectHours, setUseDirectHours] = useState(false)  // Toggle between run-based and hours-based input
  // Note: isFormInitialized state was removed as it was only used for auto-update which caused unnecessary recalculations
  const [form, setForm] = useState({
    workload_name: '',
    workload_type: 'JOBS',
    serverless_enabled: false,
    serverless_mode: 'standard',
    driver_node_type: '',
    worker_node_type: '',
    num_workers: 2,
    photon_enabled: false,
    dlt_edition: 'PRO',
    dbsql_warehouse_type: 'SERVERLESS',
    dbsql_warehouse_size: 'Small',
    dbsql_num_clusters: 1,
    // Separate driver and worker pricing for DBSQL Pro/Classic
    dbsql_driver_pricing_tier: 'on_demand',
    dbsql_driver_payment_option: 'no_upfront',
    dbsql_worker_pricing_tier: 'spot',
    dbsql_worker_payment_option: 'NA',
    vector_search_mode: 'standard',
    vector_capacity_millions: 1,
    model_serving_gpu_type: 'cpu',
    model_serving_num_endpoints: 1,
    lakebase_cu: 1,
    lakebase_storage_gb: 100,
    lakebase_ha_nodes: 1,
    lakebase_backup_retention_days: 7,
    fmapi_provider: 'anthropic',
    fmapi_model: 'llama-3-3-70b',
    fmapi_endpoint_type: 'global',  // global, in_geo (for proprietary)
    fmapi_context_length: 'long',  // 'long' is more commonly available than 'all'
    fmapi_rate_type: 'input_token',  // input_token, output_token, cache_read, cache_write
    fmapi_quantity: 0,  // quantity in millions (M)
    runs_per_day: 1,
    avg_runtime_minutes: 30,
    days_per_month: 22,
    hours_per_month: 0,
    driver_pricing_tier: 'on_demand',
    worker_pricing_tier: 'spot',
    driver_payment_option: 'no_upfront',
    worker_payment_option: 'no_upfront',
    notes: ''
  })
  
  // Default form values for new workloads
  const defaultFormValues = {
    workload_name: '',
    workload_type: 'JOBS',
    serverless_enabled: false,
    serverless_mode: 'standard',
    driver_node_type: '',
    worker_node_type: '',
    num_workers: 2,
    photon_enabled: false,
    dlt_edition: 'PRO',
    dbsql_warehouse_type: 'SERVERLESS',
    dbsql_warehouse_size: 'Small',
    dbsql_num_clusters: 1,
    // Separate driver and worker pricing for DBSQL Pro/Classic
    dbsql_driver_pricing_tier: 'on_demand',
    dbsql_driver_payment_option: 'no_upfront',
    dbsql_worker_pricing_tier: 'spot',
    dbsql_worker_payment_option: 'NA',
    vector_search_mode: 'standard',
    vector_capacity_millions: 1,
    model_serving_gpu_type: 'cpu',
    model_serving_num_endpoints: 1,
    lakebase_cu: 1,
    lakebase_storage_gb: 100,
    lakebase_ha_nodes: 1,
    lakebase_backup_retention_days: 7,
    fmapi_provider: 'anthropic',
    fmapi_model: 'llama-3-3-70b',
    fmapi_endpoint_type: 'global',
    fmapi_context_length: 'long',  // 'long' is more commonly available
    fmapi_rate_type: 'input_token',
    fmapi_quantity: 0,
    runs_per_day: 1,
    avg_runtime_minutes: 30,
    days_per_month: 22,
    hours_per_month: 0,
    driver_pricing_tier: 'on_demand',
    worker_pricing_tier: 'spot',
    driver_payment_option: 'no_upfront',
    worker_payment_option: 'no_upfront',
    notes: ''
  }

  useEffect(() => {
    if (lineItem) {
      // Editing existing line item - load saved values
      setForm({
        workload_name: lineItem.workload_name || '',
        workload_type: lineItem.workload_type || 'JOBS',
        serverless_enabled: lineItem.serverless_enabled || false,
        serverless_mode: lineItem.serverless_mode || 'standard',
        driver_node_type: lineItem.driver_node_type || '',
        worker_node_type: lineItem.worker_node_type || '',
        num_workers: lineItem.num_workers || 2,
        photon_enabled: lineItem.photon_enabled || false,
        dlt_edition: lineItem.dlt_edition || 'PRO',
        dbsql_warehouse_type: lineItem.dbsql_warehouse_type || 'SERVERLESS',
        dbsql_warehouse_size: lineItem.dbsql_warehouse_size || 'Small',
        dbsql_num_clusters: lineItem.dbsql_num_clusters || 1,
        // Separate driver and worker pricing for DBSQL Pro/Classic
        dbsql_driver_pricing_tier: lineItem.dbsql_driver_pricing_tier || lineItem.driver_pricing_tier || 'on_demand',
        dbsql_driver_payment_option: lineItem.dbsql_driver_payment_option || lineItem.driver_payment_option || 'no_upfront',
        dbsql_worker_pricing_tier: lineItem.dbsql_worker_pricing_tier || lineItem.worker_pricing_tier || 'spot',
        dbsql_worker_payment_option: lineItem.dbsql_worker_payment_option || lineItem.worker_payment_option || 'NA',
        vector_search_mode: lineItem.vector_search_mode || 'standard',
        vector_capacity_millions: lineItem.vector_capacity_millions || 1,
        model_serving_gpu_type: lineItem.model_serving_gpu_type || 'cpu',
        model_serving_num_endpoints: 1,
        lakebase_cu: lineItem.lakebase_cu || 1,
        lakebase_storage_gb: lineItem.lakebase_storage_gb || 100,
        lakebase_ha_nodes: lineItem.lakebase_ha_nodes || 1,
        lakebase_backup_retention_days: lineItem.lakebase_backup_retention_days || 7,
        fmapi_provider: lineItem.fmapi_provider || 'anthropic',
        fmapi_model: lineItem.fmapi_model || 'llama-3-3-70b',
        fmapi_endpoint_type: lineItem.fmapi_endpoint_type || 'global',
        fmapi_context_length: lineItem.fmapi_context_length || 'long',
        fmapi_rate_type: lineItem.fmapi_rate_type || 'input_token',
        fmapi_quantity: lineItem.fmapi_quantity || 0,
        runs_per_day: lineItem.runs_per_day || 1,
        avg_runtime_minutes: lineItem.avg_runtime_minutes || 30,
        days_per_month: lineItem.days_per_month || 22,
        hours_per_month: lineItem.hours_per_month || 0,
        driver_pricing_tier: lineItem.driver_pricing_tier || 'on_demand',
        worker_pricing_tier: lineItem.worker_pricing_tier || 'spot',
        driver_payment_option: lineItem.driver_payment_option || 'NA',
        worker_payment_option: lineItem.worker_payment_option || 'NA',
        notes: lineItem.notes || ''
      })
      
      // Determine if lineItem was saved with direct hours
      const hasDirectHours = Boolean(lineItem.hours_per_month && lineItem.hours_per_month > 0 && !lineItem.runs_per_day)
      setUseDirectHours(hasDirectHours)
      
    } else {
      // Creating new line item - reset to defaults
      setForm(defaultFormValues)
      setUseDirectHours(false)
    }
  }, [lineItem?.line_item_id]) // Use line_item_id to detect when switching between items
  
  // Auto-adjust form when tier changes to STANDARD (disable serverless options)
  useEffect(() => {
    if (selectedTier?.toUpperCase() === 'STANDARD') {
      // Disable serverless if it's currently enabled
      if (form.serverless_enabled) {
        setForm(f => ({ ...f, serverless_enabled: false }))
      }
      // Switch DBSQL from SERVERLESS to PRO if needed
      if (form.dbsql_warehouse_type === 'SERVERLESS') {
        setForm(f => ({ ...f, dbsql_warehouse_type: 'PRO' }))
      }
      // Switch workload type if it's a Premium-only workload
      if (PREMIUM_ONLY_WORKLOAD_TYPES.has(form.workload_type)) {
        setForm(f => ({ ...f, workload_type: 'JOBS' }))
      }
    }
  }, [selectedTier, form.serverless_enabled, form.dbsql_warehouse_type, form.workload_type])
  
  // NOTE: Removed auto-update useEffect that was calling updateLineItemLocal on every form change
  // This was causing full cost recalculations every time a field changed.
  // Now costs are only recalculated after the user clicks "Update Workload" which saves to DB
  
  const selectedWorkloadType: WorkloadType | undefined = workloadTypes.find(w => w.workload_type === form.workload_type)
  
  // If workloadTypes is empty or selectedWorkloadType is not found, show loading/error state
  const isWorkloadTypesLoading = workloadTypes.length === 0
  const isWorkloadTypeInvalid = !isWorkloadTypesLoading && !selectedWorkloadType && form.workload_type
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!form.workload_name.trim()) {
      toast.error('Enter a workload name')
      return
    }
    
    setIsSaving(true)
    try {
      // Build data object - only include fields relevant to the workload type
      // Set non-relevant fields to null to satisfy database constraints
      const data: Partial<LineItem> & { estimate_id?: string } = {
        workload_name: form.workload_name,
        workload_type: form.workload_type,
        notes: form.notes || null,
        cloud: selectedCloud?.toUpperCase() || null,
        days_per_month: form.days_per_month,
      }
      
      // Serverless fields
      if (selectedWorkloadType?.show_serverless_toggle) {
        data.serverless_enabled = form.serverless_enabled
        data.serverless_mode = form.serverless_enabled ? form.serverless_mode : null
      } else {
        data.serverless_enabled = false
        data.serverless_mode = null
      }
      
      // Compute config (both serverless and classic)
      if (selectedWorkloadType?.show_compute_config) {
        // Database constraint: when serverless_enabled is true, photon_enabled must be true
        // Serverless compute automatically includes Photon acceleration
        data.photon_enabled = form.serverless_enabled ? true : form.photon_enabled
        data.driver_node_type = form.driver_node_type || null
        data.worker_node_type = form.worker_node_type || null
        data.num_workers = form.num_workers
        data.driver_pricing_tier = form.driver_pricing_tier || 'on_demand'
        data.worker_pricing_tier = form.worker_pricing_tier || 'spot'
        data.driver_payment_option = form.driver_payment_option || 'NA'
        data.worker_payment_option = form.worker_payment_option || 'NA'
      } else {
        data.photon_enabled = false
        data.driver_node_type = null
        data.worker_node_type = null
        data.num_workers = null
        data.driver_pricing_tier = null
        data.worker_pricing_tier = null
        data.driver_payment_option = null
        data.worker_payment_option = null
      }
      
      // DLT config - only include edition for non-serverless DLT
      if (selectedWorkloadType?.show_dlt_config && !form.serverless_enabled) {
        data.dlt_edition = form.dlt_edition
      } else {
        data.dlt_edition = null
      }
      
      // DBSQL config
      if (selectedWorkloadType?.show_dbsql_config) {
        data.dbsql_warehouse_type = form.dbsql_warehouse_type
        data.dbsql_warehouse_size = form.dbsql_warehouse_size
        data.dbsql_num_clusters = form.dbsql_num_clusters
        // Separate driver and worker pricing for DBSQL Pro/Classic
        if (form.dbsql_warehouse_type === 'PRO' || form.dbsql_warehouse_type === 'CLASSIC') {
          data.dbsql_driver_pricing_tier = form.dbsql_driver_pricing_tier
          data.dbsql_driver_payment_option = form.dbsql_driver_payment_option
          data.dbsql_worker_pricing_tier = form.dbsql_worker_pricing_tier
          data.dbsql_worker_payment_option = form.dbsql_worker_payment_option
          // Also set generic driver/worker pricing for backwards compat with Calculator.tsx
          data.driver_pricing_tier = form.dbsql_driver_pricing_tier
          data.driver_payment_option = form.dbsql_driver_payment_option
          data.worker_pricing_tier = form.dbsql_worker_pricing_tier
          data.worker_payment_option = form.dbsql_worker_payment_option
        }
      } else {
        data.dbsql_warehouse_type = null
        data.dbsql_warehouse_size = null
        data.dbsql_num_clusters = null
        data.dbsql_driver_pricing_tier = null
        data.dbsql_driver_payment_option = null
        data.dbsql_worker_pricing_tier = null
        data.dbsql_worker_payment_option = null
      }
      
      // Vector Search config
      if (selectedWorkloadType?.show_vector_search_mode) {
        data.vector_search_mode = form.vector_search_mode
        data.vector_capacity_millions = form.vector_capacity_millions
      } else {
        data.vector_search_mode = null
        data.vector_capacity_millions = null
      }
      
      // Model Serving config
      if (form.workload_type === 'MODEL_SERVING') {
        data.model_serving_gpu_type = form.model_serving_gpu_type
      } else {
        data.model_serving_gpu_type = null
      }
      
      // Lakebase config
      if (selectedWorkloadType?.show_lakebase_config) {
        data.lakebase_cu = form.lakebase_cu
        data.lakebase_storage_gb = null  // Storage is not used for Lakebase pricing
        data.lakebase_ha_nodes = form.lakebase_ha_nodes
        data.lakebase_backup_retention_days = form.lakebase_backup_retention_days
      } else {
        data.lakebase_cu = null
        data.lakebase_storage_gb = null
        data.lakebase_ha_nodes = null
        data.lakebase_backup_retention_days = null
      }
      
      // FMAPI config
      if (selectedWorkloadType?.show_fmapi_config) {
        data.fmapi_provider = form.fmapi_provider
        data.fmapi_model = form.fmapi_model || null
        data.fmapi_endpoint_type = form.fmapi_endpoint_type
        data.fmapi_context_length = form.fmapi_context_length
        data.fmapi_rate_type = form.fmapi_rate_type
        data.fmapi_quantity = form.fmapi_quantity
      } else {
        data.fmapi_provider = null
        data.fmapi_model = null
        data.fmapi_endpoint_type = null
        data.fmapi_context_length = null
        data.fmapi_rate_type = null
        data.fmapi_quantity = null
      }
      
      // Hours per month vs Run-based usage
      // For compute workloads, check if using direct hours
      const isComputeWorkload = selectedWorkloadType?.show_compute_config || selectedWorkloadType?.show_dlt_config || selectedWorkloadType?.show_dbsql_config
      
      if (isComputeWorkload) {
        if (useDirectHours) {
          // Using direct hours - set hours_per_month and null out run-based fields
          data.hours_per_month = form.hours_per_month || 730
          data.runs_per_day = null
          data.avg_runtime_minutes = null
          data.days_per_month = null
        } else {
          // Using run-based - set run-based fields and null out hours_per_month
          data.hours_per_month = null
          data.runs_per_day = selectedWorkloadType?.show_usage_runs ? form.runs_per_day : null
          data.avg_runtime_minutes = form.avg_runtime_minutes
          data.days_per_month = form.days_per_month
        }
      } else if (selectedWorkloadType?.show_vector_search_mode || form.workload_type === 'MODEL_SERVING' || selectedWorkloadType?.show_lakebase_config) {
        // For Vector Search, Model Serving, Lakebase - always use hours_per_month
        data.hours_per_month = form.hours_per_month || 730
        data.runs_per_day = null
        data.avg_runtime_minutes = null
        data.days_per_month = null
      } else if (selectedWorkloadType?.show_fmapi_config) {
        // For FMAPI - use quantity-based, no hours
        data.hours_per_month = form.hours_per_month || null
        data.runs_per_day = null
        data.avg_runtime_minutes = null
        data.days_per_month = null
      } else {
        // Default - null everything
        data.hours_per_month = null
        data.runs_per_day = null
        data.avg_runtime_minutes = null
        data.days_per_month = null
      }
      
      if (lineItem) {
        // Clear cached cost and mark as calculating to show loading state
        clearSingleWorkloadCost(lineItem.line_item_id)
        markItemCalculating(lineItem.line_item_id)
        await updateLineItem(lineItem.line_item_id, data)
        toast.success('Workload updated')
      } else {
        data.estimate_id = estimateId
        const newItem = await createLineItem(data as LineItem)
        // Mark new item as calculating
        if (newItem?.line_item_id) {
          markItemCalculating(newItem.line_item_id)
        }
        toast.success('Workload added')
      }
      fetchLineItems(estimateId)
      onSave?.()
      onClose()
    } catch (err) {
      console.error('Failed to save workload:', err)
      toast.error('Failed to save')
    } finally {
      setIsSaving(false)
    }
  }
  
  // Show VM config for compute workloads (both serverless and classic)
  const showVMConfig = selectedWorkloadType?.show_compute_config
  
  // Show loading state while workload types are being fetched
  if (isWorkloadTypesLoading) {
    return (
      <div className="p-8 text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-orange-500 border-t-transparent mx-auto mb-4"></div>
        <p className="text-sm text-[var(--text-muted)]">Loading workload configuration...</p>
      </div>
    )
  }
  
  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Basic Info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>Workload Name *</label>
          <input
            type="text"
            value={form.workload_name}
            onChange={(e) => setForm(f => ({ ...f, workload_name: e.target.value }))}
            placeholder="e.g., Daily ETL Pipeline"
            className="w-full"
            autoFocus={!lineItem}
          />
        </div>
        
        <div>
          <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>Workload Type</label>
          <select
            value={form.workload_type}
            onChange={(e) => setForm(f => ({ ...f, workload_type: e.target.value, serverless_enabled: false, photon_enabled: false }))}
            className={clsx("w-full", isWorkloadTypeInvalid && "border-red-500")}
          >
            {workloadTypes.map(wt => {
              const availability = isWorkloadAvailableForTier(wt.workload_type, selectedTier, false)
              return (
                <option 
                  key={wt.workload_type} 
                  value={wt.workload_type}
                  disabled={!availability.available}
                >
                  {wt.display_name}{!availability.available ? ' (Premium+ only)' : ''}
                </option>
              )
            })}
          </select>
          {isWorkloadTypeInvalid && (
            <p className="text-xs text-red-500 mt-1">Unknown workload type: {form.workload_type}</p>
          )}
        </div>
      </div>
      
      
      {/* Feature Toggles Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* Serverless Toggle - left */}
        {selectedWorkloadType?.show_serverless_toggle && (() => {
          const serverlessAvailability = isWorkloadAvailableForTier(
            form.workload_type, 
            selectedTier, 
            true // check serverless availability
          )
          const isServerlessDisabled = !serverlessAvailability.available
          
          return (
          <div className={clsx(
            "p-3 rounded-lg border transition-all",
            isServerlessDisabled && "opacity-60",
            form.serverless_enabled && !isServerlessDisabled
              ? "bg-teal-50 dark:bg-teal-900/20 border-teal-200 dark:border-teal-700" 
              : "bg-[var(--bg-tertiary)] border-[var(--border-primary)]"
          )}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CloudIcon className={clsx(
                  "w-4 h-4",
                  form.serverless_enabled ? "text-teal-600 dark:text-teal-400" : "text-teal-500 dark:text-teal-400"
                )} />
                <span className={clsx(
                  "text-sm",
                  form.serverless_enabled && !isServerlessDisabled ? "text-teal-700 dark:text-teal-300 font-medium" : "text-[var(--text-secondary)]"
                )}>Serverless</span>
                {isServerlessDisabled && (
                  <span className="text-[10px] text-amber-600 dark:text-amber-400">(Premium+ only)</span>
                )}
              </div>
              <button
                type="button"
                onClick={() => !isServerlessDisabled && setForm(f => {
                  const newServerlessEnabled = !f.serverless_enabled
                  // All-Purpose Serverless only supports Performance mode
                  const newServerlessMode = (f.workload_type === 'ALL_PURPOSE' && newServerlessEnabled) 
                    ? 'performance' 
                    : f.serverless_mode
                  return { ...f, serverless_enabled: newServerlessEnabled, serverless_mode: newServerlessMode }
                })}
                disabled={isServerlessDisabled}
                className={clsx(
                  'toggle', 
                  form.serverless_enabled && !isServerlessDisabled ? 'toggle-checked' : 'toggle-unchecked',
                  isServerlessDisabled && 'cursor-not-allowed'
                )}
              >
                <span className={clsx('toggle-knob', form.serverless_enabled && !isServerlessDisabled ? 'toggle-knob-checked' : 'toggle-knob-unchecked')} />
              </button>
            </div>
            
            {/* Serverless Mode Dropdown - appears when serverless is enabled */}
            {/* Note: All-Purpose Serverless only supports Performance mode (no Standard option) */}
            {form.serverless_enabled && !isServerlessDisabled && (
              <div className="mt-3 pt-3 border-t border-teal-200 dark:border-teal-700">
                {form.workload_type === 'ALL_PURPOSE' ? (
                  // All-Purpose Serverless: Performance mode only (shown as info, not a selector)
                  <div className="flex items-center gap-2">
                    <div className="flex-1">
                      <span className="text-xs font-medium text-teal-700 dark:text-teal-300">Mode: </span>
                      <span className="text-sm font-semibold text-teal-800 dark:text-teal-200">Performance</span>
                    </div>
                    <span className="text-xs px-2 py-0.5 bg-teal-100 dark:bg-teal-800 text-teal-700 dark:text-teal-300 rounded">
                      Fixed
                    </span>
                  </div>
                ) : (
                  // Jobs/DLT Serverless: Allow mode selection
                  <>
                    <label className="block text-xs font-medium mb-1.5 text-teal-700 dark:text-teal-300">Serverless Mode</label>
                    <select
                      value={form.serverless_mode}
                      onChange={(e) => setForm(f => ({ ...f, serverless_mode: e.target.value }))}
                      className="w-full text-sm bg-white dark:bg-slate-800 border-teal-200 dark:border-teal-600"
                    >
                      {serverlessModeOptions.map(mode => (
                        <option key={mode.id} value={mode.id}>{mode.name}</option>
                      ))}
                    </select>
                    <p className="text-xs mt-1 text-teal-600 dark:text-teal-400">
                      {serverlessModeOptions.find(m => m.id === form.serverless_mode)?.description}
                    </p>
                  </>
                )}
              </div>
            )}
            
            {/* Warning for Standard tier */}
            {isServerlessDisabled && (
              <p className="text-xs mt-2 text-amber-600 dark:text-amber-400">
                Serverless requires Premium or Enterprise tier
              </p>
            )}
          </div>
          )
        })()}
        
        {/* Photon Toggle - right */}
        {selectedWorkloadType?.show_photon_toggle && (
          <div className={clsx(
            "p-3 rounded-lg border transition-all",
            (form.photon_enabled || form.serverless_enabled)
              ? "bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-700"
              : "bg-[var(--bg-tertiary)] border-[var(--border-primary)]"
          )}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <BoltIcon className={clsx(
                  "w-4 h-4",
                  (form.photon_enabled || form.serverless_enabled) ? "text-orange-600 dark:text-orange-400" : "text-orange-600 dark:text-orange-500"
                )} />
                <span className={clsx(
                  "text-sm",
                  (form.photon_enabled || form.serverless_enabled) ? "text-orange-700 dark:text-orange-300 font-medium" : "text-[var(--text-secondary)]"
                )}>Photon</span>
                {form.serverless_enabled && (
                  <span className="text-xs text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30 px-1.5 py-0.5 rounded">Auto</span>
                )}
              </div>
              <button
                type="button"
                onClick={() => !form.serverless_enabled && setForm(f => ({ ...f, photon_enabled: !f.photon_enabled }))}
                disabled={form.serverless_enabled}
                className={clsx(
                  'toggle', 
                  (form.photon_enabled || form.serverless_enabled) ? 'toggle-checked' : 'toggle-unchecked',
                  form.serverless_enabled && 'opacity-60 cursor-not-allowed'
                )}
              >
                <span className={clsx(
                  'toggle-knob', 
                  (form.photon_enabled || form.serverless_enabled) ? 'toggle-knob-checked' : 'toggle-knob-unchecked'
                )} />
              </button>
            </div>
            {(form.photon_enabled || form.serverless_enabled) && (
              <p className="text-xs mt-2 text-orange-600 dark:text-orange-400">
                Photon acceleration enabled for faster query execution
              </p>
            )}
          </div>
        )}
      </div>
      
      {/* VM Configuration - Driver & Worker Sections */}
      {showVMConfig && (
        <div className="space-y-3">
          {/* Serverless Note - explain VM nodes are for DBU estimation only */}
          {form.serverless_enabled && (
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
              <p className="text-xs text-blue-700 dark:text-blue-300">
                <span className="font-semibold">ℹ️ Serverless Mode:</span> VM node types are used to estimate DBU consumption only. 
                Actual VM costs are not included as serverless workloads are managed by Databricks.
              </p>
            </div>
          )}
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Driver Configuration Card */}
            <div className="bg-[var(--bg-secondary)] rounded-lg p-4 border border-[var(--border-primary)]">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                <h4 className="text-sm font-semibold text-[var(--text-primary)]">Driver Node</h4>
                <span className="text-xs text-[var(--text-muted)]">(1 node)</span>
              </div>
              
              <div className="space-y-3">
                {/* Instance Type */}
                <div>
                  <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Instance Type</label>
                  <SearchableSelect
                    options={instanceTypes.map(it => ({
                      value: it.id,
                      label: it.vcpus && it.memory_gb 
                        ? `${it.name} (${it.vcpus}vCPU, ${it.memory_gb}GB)` 
                        : it.name,
                      group: it.instance_family || 'General Purpose'
                    }))}
                    value={form.driver_node_type}
                    onChange={(value) => setForm(f => ({ ...f, driver_node_type: value }))}
                    placeholder="Select type..."
                    searchPlaceholder="Search instance types..."
                    grouped
                  />
                </div>
                
                {/* Pricing Tier & Payment Option Row - Hide for serverless */}
                {!form.serverless_enabled && (
                  <div className={clsx(
                    "grid gap-3",
                    selectedCloud === 'aws' && form.driver_pricing_tier.startsWith('reserved') 
                      ? "grid-cols-2" 
                      : "grid-cols-1"
                  )}>
                    <div>
                      <label className="flex items-center text-xs font-medium mb-1.5 text-[var(--text-secondary)]">
                        Pricing Tier
                        <PricingTierTooltip tier={form.driver_pricing_tier} />
                      </label>
                      <select
                        value={form.driver_pricing_tier}
                        onChange={(e) => setForm(f => ({ ...f, driver_pricing_tier: e.target.value }))}
                        className="w-full text-sm"
                      >
                        <option value="on_demand">On-Demand</option>
                        <option value="reserved_1y">1-Year Reserved</option>
                        <option value="reserved_3y">3-Year Reserved</option>
                      </select>
                    </div>
                    
                    {selectedCloud === 'aws' && form.driver_pricing_tier.startsWith('reserved') && (
                      <div>
                        <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Payment Option</label>
                        <select
                          value={form.driver_payment_option}
                          onChange={(e) => setForm(f => ({ ...f, driver_payment_option: e.target.value }))}
                          className="w-full text-sm"
                        >
                          {paymentOptions.map(opt => (
                            <option key={opt.id} value={opt.id}>
                              {opt.name}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
            
            {/* Worker Configuration Card */}
            <div className="bg-[var(--bg-secondary)] rounded-lg p-4 border border-[var(--border-primary)]">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500"></div>
                  <h4 className="text-sm font-semibold text-[var(--text-primary)]">Worker Nodes</h4>
                  <span className="text-xs text-[var(--text-muted)]">({form.num_workers} node{form.num_workers !== 1 ? 's' : ''})</span>
                </div>
                {/* Same as Driver checkbox */}
                <label className="flex items-center gap-1.5 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={form.driver_node_type === form.worker_node_type && form.driver_node_type !== ''}
                    onChange={(e) => {
                      if (e.target.checked && form.driver_node_type) {
                        setForm(f => ({ ...f, worker_node_type: f.driver_node_type }))
                      }
                    }}
                    disabled={!form.driver_node_type}
                    className="w-3.5 h-3.5 rounded border-[var(--border-primary)] text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
                  />
                  <span className={clsx(
                    "text-xs font-medium transition-colors",
                    form.driver_node_type === form.worker_node_type && form.driver_node_type !== ''
                      ? "text-blue-500"
                      : "text-[var(--text-muted)] group-hover:text-[var(--text-secondary)]"
                  )}>
                    Same as Driver
                  </span>
                </label>
              </div>
              
              <div className="space-y-3">
                {/* Instance Type & Count Row */}
                <div className="flex gap-2">
                  <div className="flex-1 min-w-0">
                    <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Instance Type</label>
                    <SearchableSelect
                      options={instanceTypes.map(it => ({
                        value: it.id,
                        label: it.vcpus && it.memory_gb 
                          ? `${it.name} (${it.vcpus}vCPU, ${it.memory_gb}GB)` 
                          : it.name,
                        group: it.instance_family || 'General Purpose'
                      }))}
                      value={form.worker_node_type}
                      onChange={(value) => setForm(f => ({ ...f, worker_node_type: value }))}
                      placeholder="Select type..."
                      searchPlaceholder="Search instance types..."
                      grouped
                    />
                  </div>
                  <div className="w-14 flex-shrink-0">
                    <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Count</label>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={form.num_workers}
                      onChange={(e) => setForm(f => ({ ...f, num_workers: parseInt(e.target.value) || 1 }))}
                      className="w-full text-sm text-center"
                    />
                  </div>
                </div>
                
                {/* Pricing Tier & Payment Option Row - Hide for serverless */}
                {!form.serverless_enabled && (
                  <div className={clsx(
                    "grid gap-3",
                    selectedCloud === 'aws' && form.worker_pricing_tier.startsWith('reserved') 
                      ? "grid-cols-2" 
                      : "grid-cols-1"
                  )}>
                    <div>
                      <label className="flex items-center text-xs font-medium mb-1.5 text-[var(--text-secondary)]">
                        Pricing Tier
                        <PricingTierTooltip tier={form.worker_pricing_tier} />
                      </label>
                      <select
                        value={form.worker_pricing_tier}
                        onChange={(e) => setForm(f => ({ ...f, worker_pricing_tier: e.target.value }))}
                        className="w-full text-sm"
                      >
                        <option value="spot">Spot Instances</option>
                        <option value="on_demand">On-Demand</option>
                        <option value="reserved_1y">1-Year Reserved</option>
                        <option value="reserved_3y">3-Year Reserved</option>
                      </select>
                    </div>
                    
                    {selectedCloud === 'aws' && form.worker_pricing_tier.startsWith('reserved') && (
                      <div>
                        <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Payment Option</label>
                        <select
                          value={form.worker_payment_option}
                          onChange={(e) => setForm(f => ({ ...f, worker_payment_option: e.target.value }))}
                          className="w-full text-sm"
                        >
                          {paymentOptions.map(opt => (
                            <option key={opt.id} value={opt.id}>
                              {opt.name}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Other Configuration Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Placeholder for grid alignment when VM config is shown */}
        {showVMConfig && (
          <></>
        )}
        
        {/* DLT Config - hide when serverless is enabled (serverless DLT doesn't have edition selection) */}
        {selectedWorkloadType?.show_dlt_config && !form.serverless_enabled && (
          <div>
            <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">DLT Edition</label>
            <select
              value={form.dlt_edition}
              onChange={(e) => setForm(f => ({ ...f, dlt_edition: e.target.value }))}
              className="w-full text-sm"
            >
              {dltEditionOptions.map(ed => (
                <option key={ed.id} value={ed.id}>{ed.name}</option>
              ))}
            </select>
          </div>
        )}
        
        {/* DBSQL Config */}
        {selectedWorkloadType?.show_dbsql_config && (
          <>
            {/* Serverless Toggle for DBSQL - similar to Jobs/All Purpose */}
            <div className="col-span-full">
              {(() => {
                const dbsqlServerlessAvailability = isWorkloadAvailableForTier('DBSQL', selectedTier, false, 'SERVERLESS')
                const isDBSQLServerlessDisabled = !dbsqlServerlessAvailability.available
                
                return (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* Serverless Toggle */}
                <div className={clsx(
                  "p-3 rounded-lg border transition-all",
                  isDBSQLServerlessDisabled && "opacity-60",
                  form.dbsql_warehouse_type === 'SERVERLESS' && !isDBSQLServerlessDisabled
                    ? "bg-teal-50 dark:bg-teal-900/20 border-teal-200 dark:border-teal-700" 
                    : "bg-[var(--bg-tertiary)] border-[var(--border-primary)]"
                )}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CloudIcon className={clsx(
                        "w-4 h-4",
                        form.dbsql_warehouse_type === 'SERVERLESS' && !isDBSQLServerlessDisabled ? "text-teal-600 dark:text-teal-400" : "text-teal-500 dark:text-teal-400"
                      )} />
                      <span className={clsx(
                        "text-sm",
                        form.dbsql_warehouse_type === 'SERVERLESS' && !isDBSQLServerlessDisabled ? "text-teal-700 dark:text-teal-300 font-medium" : "text-[var(--text-secondary)]"
                      )}>Serverless</span>
                      {isDBSQLServerlessDisabled && (
                        <span className="text-[10px] text-amber-600 dark:text-amber-400">(Premium+ only)</span>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => !isDBSQLServerlessDisabled && setForm(f => ({ 
                        ...f, 
                        dbsql_warehouse_type: f.dbsql_warehouse_type === 'SERVERLESS' ? 'PRO' : 'SERVERLESS' 
                      }))}
                      disabled={isDBSQLServerlessDisabled}
                      className={clsx(
                        'toggle', 
                        form.dbsql_warehouse_type === 'SERVERLESS' && !isDBSQLServerlessDisabled ? 'toggle-checked' : 'toggle-unchecked',
                        isDBSQLServerlessDisabled && 'cursor-not-allowed'
                      )}
                    >
                      <span className={clsx('toggle-knob', form.dbsql_warehouse_type === 'SERVERLESS' && !isDBSQLServerlessDisabled ? 'toggle-knob-checked' : 'toggle-knob-unchecked')} />
                    </button>
                  </div>
                  
                  {form.dbsql_warehouse_type === 'SERVERLESS' && !isDBSQLServerlessDisabled && (
                    <p className="text-xs text-teal-600 dark:text-teal-400 mt-2">
                      Fully managed SQL compute
                    </p>
                  )}
                  
                  {isDBSQLServerlessDisabled && (
                    <p className="text-xs text-amber-600 dark:text-amber-400 mt-2">
                      DBSQL Serverless requires Premium or Enterprise tier
                    </p>
                  )}
                </div>
                
                {/* Warehouse Type dropdown - only when not serverless */}
                {(form.dbsql_warehouse_type !== 'SERVERLESS' || isDBSQLServerlessDisabled) && (
                  <div className="p-3 rounded-lg border bg-[var(--bg-tertiary)] border-[var(--border-primary)]">
                    <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Warehouse Type</label>
                    <select
                      value={form.dbsql_warehouse_type === 'SERVERLESS' && isDBSQLServerlessDisabled ? 'PRO' : form.dbsql_warehouse_type}
                      onChange={(e) => setForm(f => ({ ...f, dbsql_warehouse_type: e.target.value }))}
                      className="w-full text-sm"
                    >
                      <option value="PRO">Pro</option>
                      <option value="CLASSIC">Classic</option>
                    </select>
                  </div>
                )}
              </div>
                )
              })()}
            </div>
            
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Size</label>
              <select
                value={form.dbsql_warehouse_size}
                onChange={(e) => setForm(f => ({ ...f, dbsql_warehouse_size: e.target.value }))}
                className="w-full text-sm"
              >
                {dbsqlSizes.map(size => (
                  <option key={size.id} value={size.id}>{size.name} ({size.dbu_per_hour} DBU/hr)</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Number of Clusters</label>
              <input
                type="number"
                min={1}
                max={100}
                value={form.dbsql_num_clusters}
                onChange={(e) => setForm(f => ({ ...f, dbsql_num_clusters: parseInt(e.target.value) || 1 }))}
                className="w-full text-sm"
              />
            </div>
            
            {/* VM Instance Types and Pricing - only for Pro and Classic warehouse types (not Serverless) */}
            {(form.dbsql_warehouse_type === 'PRO' || form.dbsql_warehouse_type === 'CLASSIC') && (() => {
              // Get warehouse config for display
              const warehouseConfig = isPricingBundleLoaded 
                ? getDBSQLWarehouseConfig(pricingBundle, selectedCloud || 'aws', form.dbsql_warehouse_type, form.dbsql_warehouse_size)
                : null
              
              return (
                <div className="col-span-2 grid grid-cols-2 gap-3">
                  {/* Driver Node - Compact */}
                  <div className="p-2.5 rounded-lg border bg-blue-50/50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                        <span className="text-xs font-semibold text-blue-700 dark:text-blue-300">Driver</span>
                      </div>
                      <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                        {warehouseConfig?.driver_instance_type || '—'}
                      </span>
                    </div>
                    <select
                      value={form.dbsql_driver_pricing_tier}
                      onChange={(e) => setForm(f => ({ ...f, dbsql_driver_pricing_tier: e.target.value }))}
                      className="w-full text-sm"
                    >
                      <option value="on_demand">On-Demand</option>
                      <option value="reserved_1y">1-Year Reserved</option>
                      <option value="reserved_3y">3-Year Reserved</option>
                    </select>
                    {selectedCloud === 'aws' && form.dbsql_driver_pricing_tier.startsWith('reserved') && (
                      <select
                        value={form.dbsql_driver_payment_option}
                        onChange={(e) => setForm(f => ({ ...f, dbsql_driver_payment_option: e.target.value }))}
                        className="w-full text-sm mt-2"
                      >
                        {paymentOptions.map(opt => (
                          <option key={opt.id} value={opt.id}>{opt.name}</option>
                        ))}
                      </select>
                    )}
                  </div>
                  
                  {/* Worker Nodes - Compact */}
                  <div className="p-2.5 rounded-lg border bg-green-50/50 dark:bg-green-950/20 border-green-200 dark:border-green-800">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                        <span className="text-xs font-semibold text-green-700 dark:text-green-300">
                          Workers ×{warehouseConfig?.worker_count || 4}
                        </span>
                      </div>
                      <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                        {warehouseConfig?.worker_instance_type || '—'}
                      </span>
                    </div>
                    <select
                      value={form.dbsql_worker_pricing_tier}
                      onChange={(e) => setForm(f => ({ ...f, dbsql_worker_pricing_tier: e.target.value }))}
                      className="w-full text-sm"
                    >
                      <option value="spot">Spot Instances</option>
                      <option value="on_demand">On-Demand</option>
                      <option value="reserved_1y">1-Year Reserved</option>
                      <option value="reserved_3y">3-Year Reserved</option>
                    </select>
                    {selectedCloud === 'aws' && form.dbsql_worker_pricing_tier.startsWith('reserved') && (
                      <select
                        value={form.dbsql_worker_payment_option}
                        onChange={(e) => setForm(f => ({ ...f, dbsql_worker_payment_option: e.target.value }))}
                        className="w-full text-sm mt-2"
                      >
                        {paymentOptions.map(opt => (
                          <option key={opt.id} value={opt.id}>{opt.name}</option>
                        ))}
                      </select>
                    )}
                  </div>
                </div>
              )
            })()}
          </>
        )}
        
        {/* Vector Search Config */}
        {selectedWorkloadType?.show_vector_search_mode && (
          <>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Vector Search Type</label>
              <select
                value={form.vector_search_mode}
                onChange={(e) => setForm(f => ({ ...f, vector_search_mode: e.target.value }))}
                className="w-full text-sm"
              >
                <option value="standard">Standard (4 DBU/hr per 2M vectors)</option>
                <option value="storage_optimized">Storage Optimized (18.29 DBU/hr per 64M vectors)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Capacity (M vectors)</label>
              <input
                type="number"
                min={0.1}
                max={1000}
                step={0.1}
                value={form.vector_capacity_millions}
                onChange={(e) => setForm(f => ({ ...f, vector_capacity_millions: parseFloat(e.target.value) || 1 }))}
                className="w-full text-sm"
                placeholder="e.g., 1.5"
              />
            </div>
          </>
        )}
        
        {/* Model Serving Config */}
        {form.workload_type === 'MODEL_SERVING' && (
          <>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Endpoint Type</label>
              <select
                value={form.model_serving_gpu_type}
                onChange={(e) => setForm(f => ({ ...f, model_serving_gpu_type: e.target.value }))}
                className="w-full text-sm"
              >
                {modelServingGPUTypes.map(gpu => (
                  <option key={gpu.id} value={gpu.id}>
                    {gpu.name} ({gpu.dbu_per_hour} DBU/hr)
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Number of Endpoints</label>
              <input
                type="number"
                min={1}
                max={100}
                value={form.model_serving_num_endpoints}
                onChange={(e) => setForm(f => ({ ...f, model_serving_num_endpoints: parseInt(e.target.value) || 1 }))}
                className="w-full text-sm"
              />
            </div>
          </>
        )}
        
        {/* FMAPI Config - Foundation Models (Databricks) */}
        {selectedWorkloadType?.show_fmapi_config && form.workload_type === 'FMAPI_DATABRICKS' && (
          <>
            {/* Row 1: Model | Rate Type */}
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Model</label>
              <select
                value={form.fmapi_model}
                onChange={(e) => setForm(f => ({ ...f, fmapi_model: e.target.value }))}
                className="w-full text-sm"
              >
                <optgroup label="LLMs">
                  {fmapiDatabricksModels.models.llm.map(model => (
                    <option key={model.id} value={model.id}>{model.name}</option>
                  ))}
                </optgroup>
                <optgroup label="Embedding Models">
                  {fmapiDatabricksModels.models.embedding.map(model => (
                    <option key={model.id} value={model.id}>{model.name}</option>
                  ))}
                </optgroup>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Rate Type</label>
              <select
                value={form.fmapi_rate_type}
                onChange={(e) => setForm(f => ({ ...f, fmapi_rate_type: e.target.value }))}
                className="w-full text-sm"
              >
                <optgroup label="Token-based">
                  <option value="input_token">Input Token</option>
                  {/* Only show output tokens for LLMs, not embedding models */}
                  {!['gte', 'bge-large'].includes(form.fmapi_model) && (
                    <option value="output_token">Output Token</option>
                  )}
                </optgroup>
                <optgroup label="Provisioned">
                  <option value="provisioned_scaling">Provisioned Scaling</option>
                  <option value="provisioned_entry">Provisioned Entry</option>
                </optgroup>
              </select>
            </div>
            
            {/* Row 2: Quantity - different label based on rate type */}
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">
                {['provisioned_scaling', 'provisioned_entry'].includes(form.fmapi_rate_type) 
                  ? 'Hours/Month' 
                  : 'Quantity (M tokens/month)'}
              </label>
              <input
                type="number"
                min={0}
                step={['provisioned_scaling', 'provisioned_entry'].includes(form.fmapi_rate_type) ? 1 : 0.1}
                value={form.fmapi_quantity}
                onChange={(e) => setForm(f => ({ ...f, fmapi_quantity: parseFloat(e.target.value) || 0 }))}
                className="w-full text-sm"
                placeholder={['provisioned_scaling', 'provisioned_entry'].includes(form.fmapi_rate_type) 
                  ? 'e.g., 730 = 24/7' 
                  : 'e.g., 10'}
              />
              {!['provisioned_scaling', 'provisioned_entry'].includes(form.fmapi_rate_type) && (
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  Enter in millions: 1 = 1M, 5 = 5M, 10 = 10M tokens
                </p>
              )}
            </div>
            
            {/* Info: Add multiple line items for complete endpoint cost */}
            <div className="col-span-full p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
              <p className="text-xs text-blue-700 dark:text-blue-300">
                {['provisioned_scaling', 'provisioned_entry'].includes(form.fmapi_rate_type) ? (
                  <><strong>Provisioned Throughput:</strong> Cost = hours × DBU/hour × DBU price</>
                ) : (
                  <><strong>Tip:</strong> Add separate workloads for Input Token and Output Token to calculate total cost.</>
                )}
              </p>
            </div>
          </>
        )}
        
        {/* FMAPI Config - Foundation Models (Proprietary) */}
        {selectedWorkloadType?.show_fmapi_config && form.workload_type === 'FMAPI_PROPRIETARY' && (
          <>
            {/* Row 1: Provider | Model */}
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Provider</label>
              <select
                value={form.fmapi_provider}
                onChange={(e) => setForm(f => ({ 
                  ...f, 
                  fmapi_provider: e.target.value, 
                  fmapi_model: '',
                  fmapi_context_length: 'long', // Reset to a common default
                  fmapi_rate_type: 'input_token' // Reset rate type
                }))}
                className="w-full text-sm"
              >
                {fmapiProprietaryModels.providers.map(provider => (
                  <option key={provider.id} value={provider.id}>{provider.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Model</label>
              <select
                value={form.fmapi_model}
                onChange={(e) => {
                  const newModel = e.target.value
                  // Reset context_length to first available option when model changes
                  const availableCtxLengths = getAvailableContextLengths(
                    pricingBundle, 
                    selectedCloud || 'aws', 
                    form.fmapi_provider, 
                    newModel
                  )
                  const newCtxLength = availableCtxLengths.includes(form.fmapi_context_length) 
                    ? form.fmapi_context_length 
                    : availableCtxLengths[0] || 'all'
                  setForm(f => ({ ...f, fmapi_model: newModel, fmapi_context_length: newCtxLength }))
                }}
                className="w-full text-sm"
              >
                <option value="">Select model</option>
                {fmapiProprietaryModels.providers
                  .find(p => p.id === form.fmapi_provider)
                  ?.models.map(model => (
                    <option key={model.id} value={model.id}>{model.name}</option>
                  ))
                }
              </select>
            </div>
            
            {/* Row 2: Endpoint Type | Context Length */}
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Endpoint Type</label>
              <select
                value={form.fmapi_endpoint_type}
                onChange={(e) => setForm(f => ({ ...f, fmapi_endpoint_type: e.target.value }))}
                className="w-full text-sm"
              >
                {fmapiProprietaryModels.endpoint_types.map(type => (
                  <option key={type.id} value={type.id}>{type.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Context Length</label>
              <select
                value={form.fmapi_context_length}
                onChange={(e) => setForm(f => ({ ...f, fmapi_context_length: e.target.value }))}
                className="w-full text-sm"
              >
                {(() => {
                  // Get available context lengths for the selected model
                  const availableCtxLengths = form.fmapi_model
                    ? getAvailableContextLengths(pricingBundle, selectedCloud || 'aws', form.fmapi_provider, form.fmapi_model)
                    : ['all', 'short', 'long']
                  
                  // Map to display names
                  const contextLengthNames: Record<string, string> = {
                    'all': 'All',
                    'short': 'Short',
                    'long': 'Long'
                  }
                  
                  return availableCtxLengths.map(length => (
                    <option key={length} value={length}>
                      {contextLengthNames[length] || length}
                    </option>
                  ))
                })()}
              </select>
            </div>
            
            {/* Row 3: Rate Type | Quantity */}
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Rate Type</label>
              <select
                value={form.fmapi_rate_type}
                onChange={(e) => setForm(f => ({ ...f, fmapi_rate_type: e.target.value }))}
                className="w-full text-sm"
              >
                {(() => {
                  // Get available rate types for the selected model/endpoint/context
                  const availableRateTypes = form.fmapi_model
                    ? getAvailableRateTypes(
                        pricingBundle, 
                        selectedCloud || 'aws', 
                        form.fmapi_provider, 
                        form.fmapi_model,
                        form.fmapi_endpoint_type,
                        form.fmapi_context_length
                      )
                    : ['input_token', 'output_token', 'cache_read', 'cache_write']
                  
                  // Map to display names
                  const rateTypeNames: Record<string, string> = {
                    'input_token': 'Input Token',
                    'output_token': 'Output Token',
                    'cache_read': 'Cache Read',
                    'cache_write': 'Cache Write',
                    'batch_inference': 'Batch Inference',
                    'provisioned_scaling': 'Provisioned Scaling'
                  }
                  
                  return availableRateTypes.map(type => (
                    <option key={type} value={type}>
                      {rateTypeNames[type] || type}
                    </option>
                  ))
                })()}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Quantity (M tokens/month)</label>
              <input
                type="number"
                min={0}
                step={0.1}
                value={form.fmapi_quantity}
                onChange={(e) => setForm(f => ({ ...f, fmapi_quantity: parseFloat(e.target.value) || 0 }))}
                className="w-full text-sm"
                placeholder="e.g., 10"
              />
              <p className="text-xs text-[var(--text-muted)] mt-1">
                Enter in millions: 1 = 1M, 5 = 5M, 10 = 10M tokens
              </p>
            </div>
            
            {/* Info: Add multiple line items for complete endpoint cost */}
            <div className="col-span-full p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
              <p className="text-xs text-blue-700 dark:text-blue-300">
                <strong>Tip:</strong> Add separate workloads for each rate type (Input Token, Output Token, Cache Read, Cache Write) 
                to calculate the total cost of your Foundation Model endpoint.
              </p>
            </div>
          </>
        )}
        
        {/* Lakebase Config */}
        {selectedWorkloadType?.show_lakebase_config && (
          <>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Capacity Units (CU)</label>
              <input
                type="number"
                min={1}
                max={8}
                value={form.lakebase_cu}
                onChange={(e) => setForm(f => ({ ...f, lakebase_cu: parseInt(e.target.value) || 1 }))}
                className="w-full text-sm"
              />
              <span className="text-xs text-[var(--text-muted)]">1, 2, 4, or 8</span>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Number of Nodes</label>
              <input
                type="number"
                min={1}
                max={3}
                value={form.lakebase_ha_nodes}
                onChange={(e) => setForm(f => ({ ...f, lakebase_ha_nodes: parseInt(e.target.value) || 1 }))}
                className="w-full text-sm"
              />
              <span className="text-xs text-[var(--text-muted)]">1-3 (HA requires 2+)</span>
            </div>
          </>
        )}
        
        {/* Usage Input Method Toggle - for compute workloads only */}
        {(selectedWorkloadType?.show_compute_config || selectedWorkloadType?.show_dlt_config || selectedWorkloadType?.show_dbsql_config) && (
          <div className="col-span-full">
            <div className="flex items-center gap-4 mb-3">
              <span className="text-xs font-medium text-[var(--text-secondary)]">Usage Input Method:</span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setUseDirectHours(false)}
                  className={clsx(
                    "px-3 py-1 text-xs rounded-l-md border transition-colors",
                    !useDirectHours 
                      ? "bg-orange-500 text-white border-orange-500" 
                      : "bg-[var(--bg-secondary)] text-[var(--text-secondary)] border-[var(--border-primary)] hover:bg-[var(--bg-tertiary)]"
                  )}
                >
                  Run-Based
                </button>
                <button
                  type="button"
                  onClick={() => setUseDirectHours(true)}
                  className={clsx(
                    "px-3 py-1 text-xs rounded-r-md border-y border-r transition-colors",
                    useDirectHours 
                      ? "bg-orange-500 text-white border-orange-500" 
                      : "bg-[var(--bg-secondary)] text-[var(--text-secondary)] border-[var(--border-primary)] hover:bg-[var(--bg-tertiary)]"
                  )}
                >
                  Direct Hours
                </button>
              </div>
            </div>
          </div>
        )}
        
        {/* Run-based usage inputs */}
        {!useDirectHours && (
          <>
            {/* Usage - Runs (not for Lakebase, Vector Search, Model Serving, FMAPI which use hours_per_month directly) */}
            {selectedWorkloadType?.show_usage_runs && !selectedWorkloadType?.show_lakebase_config && !selectedWorkloadType?.show_vector_search_mode && !selectedWorkloadType?.show_fmapi_config && form.workload_type !== 'MODEL_SERVING' && (
              <div>
                <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Runs/Day</label>
                <input
                  type="number"
                  min={0}
                  value={form.runs_per_day}
                  onChange={(e) => setForm(f => ({ ...f, runs_per_day: parseInt(e.target.value) || 0 }))}
                  className="w-full text-sm"
                />
              </div>
            )}
            
            {/* Avg Runtime - for Jobs, All Purpose, DLT, and SQL Warehouse */}
            {(selectedWorkloadType?.show_compute_config || selectedWorkloadType?.show_dlt_config || selectedWorkloadType?.show_dbsql_config) && (
              <div>
                <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Avg Runtime (min)</label>
                <input
                  type="number"
                  min={0}
                  value={form.avg_runtime_minutes}
                  onChange={(e) => setForm(f => ({ ...f, avg_runtime_minutes: parseInt(e.target.value) || 0 }))}
                  className="w-full text-sm"
                />
              </div>
            )}
            
            {/* Days per month - hide for FMAPI, Vector Search, Model Serving, Lakebase (they use hours_per_month directly) */}
            {!selectedWorkloadType?.show_fmapi_config && !selectedWorkloadType?.show_vector_search_mode && !selectedWorkloadType?.show_lakebase_config && form.workload_type !== 'MODEL_SERVING' && (
              <div>
                <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Days/Month</label>
                <input
                  type="number"
                  min={1}
                  max={31}
                  value={form.days_per_month}
                  onChange={(e) => setForm(f => ({ ...f, days_per_month: parseInt(e.target.value) || 22 }))}
                  className="w-full text-sm"
                />
              </div>
            )}
          </>
        )}
        
        {/* Direct hours input */}
        {useDirectHours && (selectedWorkloadType?.show_compute_config || selectedWorkloadType?.show_dlt_config || selectedWorkloadType?.show_dbsql_config) && (
          <div className="col-span-full md:col-span-1">
            <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Hours/Month</label>
            <input
              type="number"
              min={0}
              max={744}
              value={form.hours_per_month || 730}
              onChange={(e) => setForm(f => ({ ...f, hours_per_month: parseFloat(e.target.value) || 0 }))}
              className="w-full text-sm"
              placeholder="730 = 24/7"
            />
            <p className="text-xs text-[var(--text-muted)] mt-1">730 = 24/7 monthly operation</p>
          </div>
        )}
        
        {/* For Vector Search, Model Serving, and Lakebase - always show direct hours */}
        {(selectedWorkloadType?.show_vector_search_mode || form.workload_type === 'MODEL_SERVING' || selectedWorkloadType?.show_lakebase_config) && (
          <div>
            <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Hours/Month</label>
            <input
              type="number"
              min={0}
              max={744}
              value={form.hours_per_month || 730}
              onChange={(e) => setForm(f => ({ ...f, hours_per_month: parseFloat(e.target.value) || 0 }))}
              className="w-full text-sm"
              placeholder="730 = 24/7"
            />
          </div>
        )}
        
      </div>
      
      {/* Notes - Collapsible by default */}
      <CollapsibleNotes 
        notes={form.notes} 
        onChange={(value) => setForm(f => ({ ...f, notes: value }))} 
      />
      
      {/* Live Cost Preview */}
      <LiveCostPreview 
        form={form}
        originalItem={lineItem}
        context={{
          cloud: selectedCloud,
          region: selectedRegion,
          tier: selectedTier,
          dbuRatesMap,
          instanceTypes,
          dbsqlSizes,
          photonMultipliers,
          modelServingGPUTypes,
          vectorSearchModes,
          getVMPrice,
          getFMAPIDatabricksRate,
          // Pricing bundle lookup functions for consistency with Calculator.tsx
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
          getFMAPIProprietaryRate: (provider: string, model: string, rateType: string, endpointType?: string, contextLength?: string) => {
            // Try pricing bundle first (with full key: cloud:provider:model:endpoint:context:rate)
            if (isPricingBundleLoaded && pricingBundle.fmapiProprietaryRates) {
              const cloud = (selectedCloud || 'aws').toLowerCase()
              const ep = endpointType || 'global'
              const ctx = contextLength || 'all'
              // Try exact match first
              let key = `${cloud}:${provider.toLowerCase()}:${model.toLowerCase()}:${ep}:${ctx}:${rateType}`
              let data = pricingBundle.fmapiProprietaryRates[key]
              // If not found, try with 'all' context length (some models use 'all')
              if (!data && ctx !== 'all') {
                key = `${cloud}:${provider.toLowerCase()}:${model.toLowerCase()}:${ep}:all:${rateType}`
                data = pricingBundle.fmapiProprietaryRates[key]
              }
              if (data) {
                return {
                  dbu_per_1M_tokens: data.is_hourly ? undefined : data.dbu_rate,
                  dbu_per_hour: data.is_hourly ? data.dbu_rate : undefined
                }
              }
            }
            // Fallback to store function
            return getFMAPIProprietaryRate(provider, model, rateType)
          },
          getVectorSearchRate,
          getDBSQLWarehouseConfig: (warehouseType: string, warehouseSize: string) => {
            if (!isPricingBundleLoaded) return null
            return getDBSQLWarehouseConfig(pricingBundle, selectedCloud || 'aws', warehouseType, warehouseSize)
          }
        }}
      />
      
      {/* Actions */}
      <div className="flex items-center justify-end gap-2 pt-2">
        <button type="button" onClick={onClose} className="btn btn-secondary">
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSaving || !form.workload_name.trim()}
          className="btn btn-primary"
        >
          {isSaving ? 'Saving...' : lineItem ? 'Update Workload' : 'Add Workload'}
        </button>
      </div>
    </form>
  )
}

// Helper to format currency
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount)
}

// Helper to format numbers - show 2 decimal places for DBUs
function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(2) + 'M'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(2) + 'K'
  }
  return num.toFixed(2)
}

// Live Cost Preview Component
interface LiveCostPreviewProps {
  form: {
    workload_type: string
    serverless_enabled: boolean
    serverless_mode: string
    driver_node_type: string
    worker_node_type: string
    num_workers: number
    photon_enabled: boolean
    dlt_edition: string
    dbsql_warehouse_type: string
    dbsql_warehouse_size: string
    dbsql_num_clusters: number
    // DBSQL driver/worker pricing tiers
    dbsql_driver_pricing_tier: string
    dbsql_driver_payment_option: string
    dbsql_worker_pricing_tier: string
    dbsql_worker_payment_option: string
    vector_search_mode: string
    vector_capacity_millions: number
    model_serving_gpu_type: string
    lakebase_cu: number
    lakebase_ha_nodes: number
    fmapi_provider: string
    fmapi_model: string
    fmapi_endpoint_type: string
    fmapi_context_length: string
    fmapi_rate_type: string
    fmapi_quantity: number
    runs_per_day: number
    avg_runtime_minutes: number
    days_per_month: number
    hours_per_month: number
    driver_pricing_tier: string
    worker_pricing_tier: string
    driver_payment_option: string
    worker_payment_option: string
  }
  originalItem: LineItem | null
  context: CostCalculationContext
}

function LiveCostPreview({ form, originalItem, context }: LiveCostPreviewProps) {
  // Calculate current cost based on form values
  const currentCost = useMemo(() => {
    // Determine if this is an hours-based workload type
    const isHoursBasedWorkload = ['LAKEBASE', 'VECTOR_SEARCH', 'MODEL_SERVING'].includes(form.workload_type) ||
      form.vector_search_mode !== undefined && form.workload_type === 'VECTOR_SEARCH'
    
    // For hours-based workloads, use 730 as default if hours_per_month is 0 or undefined
    const effectiveHoursPerMonth = isHoursBasedWorkload
      ? (form.hours_per_month || 730)
      : form.hours_per_month
    
    const formAsItem: Partial<LineItem> = {
      workload_type: form.workload_type,
      serverless_enabled: form.serverless_enabled,
      serverless_mode: form.serverless_mode,
      driver_node_type: form.driver_node_type || undefined,
      worker_node_type: form.worker_node_type || undefined,
      num_workers: form.num_workers,
      photon_enabled: form.photon_enabled,
      dlt_edition: form.dlt_edition,
      dbsql_warehouse_type: form.dbsql_warehouse_type,
      dbsql_warehouse_size: form.dbsql_warehouse_size,
      dbsql_num_clusters: form.dbsql_num_clusters,
      // DBSQL driver/worker pricing tiers
      dbsql_driver_pricing_tier: form.dbsql_driver_pricing_tier,
      dbsql_driver_payment_option: form.dbsql_driver_payment_option,
      dbsql_worker_pricing_tier: form.dbsql_worker_pricing_tier,
      dbsql_worker_payment_option: form.dbsql_worker_payment_option,
      vector_search_mode: form.vector_search_mode,
      vector_capacity_millions: form.vector_capacity_millions,
      model_serving_gpu_type: form.model_serving_gpu_type,
      lakebase_cu: form.lakebase_cu,
      lakebase_ha_nodes: form.lakebase_ha_nodes,
      fmapi_provider: form.fmapi_provider,
      fmapi_model: form.fmapi_model,
      fmapi_endpoint_type: form.fmapi_endpoint_type,
      fmapi_context_length: form.fmapi_context_length,
      fmapi_rate_type: form.fmapi_rate_type,
      fmapi_quantity: form.fmapi_quantity,
      runs_per_day: form.runs_per_day,
      avg_runtime_minutes: form.avg_runtime_minutes,
      days_per_month: form.days_per_month,
      hours_per_month: effectiveHoursPerMonth || undefined,
      driver_pricing_tier: form.driver_pricing_tier,
      worker_pricing_tier: form.worker_pricing_tier,
      driver_payment_option: form.driver_payment_option,
      worker_payment_option: form.worker_payment_option
    }
    
    return calculateWorkloadCost(formAsItem, context)
  }, [form, context])
  
  // Calculate original cost for comparison (only for existing items)
  const originalCost = useMemo(() => {
    if (!originalItem) return null
    return calculateWorkloadCost(originalItem, context)
  }, [originalItem, context])
  
  // Calculate delta
  const costDelta = originalCost ? currentCost.totalCost - originalCost.totalCost : 0
  const hasCostChange = Math.abs(costDelta) > 0.01
  
  // Don't show if no region is selected
  if (!context.region) {
    return (
      <div className="mt-4 p-3 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border-primary)]">
        <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
          <CurrencyDollarIcon className="w-4 h-4" />
          <span>Select a region to see cost estimate</span>
        </div>
      </div>
    )
  }
  
  return (
    <div className="mt-4 p-3 rounded-lg bg-gradient-to-r from-orange-500/10 to-amber-500/10 border border-orange-500/20">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <CurrencyDollarIcon className="w-5 h-5 text-orange-500" />
            <span className="text-sm font-medium text-[var(--text-secondary)]">Live Estimate:</span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-bold text-orange-500">{formatCurrency(currentCost.totalCost)}</span>
            <span className="text-xs text-[var(--text-muted)]">/mo</span>
          </div>
        </div>
        
        <div className="flex items-center gap-4 text-xs text-[var(--text-muted)]">
          <span>{formatNumber(currentCost.monthlyDBUs)} DBUs</span>
          {/* Show units used for Vector Search */}
          {currentCost.unitsUsed !== undefined && (
            <span className="text-blue-500 font-medium">{currentCost.unitsUsed} unit{currentCost.unitsUsed !== 1 ? 's' : ''}</span>
          )}
          {currentCost.vmCost > 0 && (
            <span>VM: {formatCurrency(currentCost.vmCost)}</span>
          )}
          
          {/* Show delta for existing items */}
          {originalItem && hasCostChange && (
            <div className={clsx(
              "flex items-center gap-1 px-2 py-0.5 rounded-full font-medium",
              costDelta > 0 
                ? "bg-red-500/10 text-red-600 dark:text-red-400"
                : "bg-green-500/10 text-green-600 dark:text-green-400"
            )}>
              {costDelta > 0 ? (
                <ArrowTrendingUpIcon className="w-3 h-3" />
              ) : (
                <ArrowTrendingDownIcon className="w-3 h-3" />
              )}
              <span>{costDelta > 0 ? '+' : ''}{formatCurrency(costDelta)}</span>
            </div>
          )}
        </div>
      </div>
      
      {/* Calculation Formula */}
      <div className="mt-2 pt-2 border-t border-orange-500/20">
        <div className="flex items-center gap-1 text-[10px] font-mono text-[var(--text-muted)] flex-wrap">
          {(() => {
            const hoursPerMonth = form.hours_per_month || 
              (form.runs_per_day && form.avg_runtime_minutes 
                ? form.runs_per_day * (form.avg_runtime_minutes / 60) * (form.days_per_month || 30)
                : 730)
            const dbuPriceDisplay = currentCost.dbuPrice?.toFixed(2) || '0.00'
            
            // Vector Search
            if (form.workload_type === 'VECTOR_SEARCH') {
              return (
                <>
                  <span className="text-blue-500">{currentCost.unitsUsed || 1} units</span>
                  <span>×</span>
                  <span className="text-purple-500">{currentCost.dbuPerHour?.toFixed(2) || '4.00'} DBU/hr</span>
                  <span>×</span>
                  <span className="text-green-500">{hoursPerMonth.toFixed(0)}h</span>
                  <span>=</span>
                  <span className="text-orange-500">{formatNumber(currentCost.monthlyDBUs)} DBUs</span>
                  <span>×</span>
                  <span className="text-pink-500">${dbuPriceDisplay}/DBU</span>
                  <span>=</span>
                  <span className="text-orange-600 font-semibold">{formatCurrency(currentCost.totalCost)}</span>
                </>
              )
            }
            
            // FMAPI (token-based)
            if (form.workload_type === 'FMAPI_DATABRICKS' || form.workload_type === 'FMAPI_PROPRIETARY') {
              const dbuPerMToken = form.fmapi_quantity > 0 ? (currentCost.monthlyDBUs / form.fmapi_quantity).toFixed(2) : '0'
              return (
                <>
                  <span className="text-blue-500">{form.fmapi_quantity || 0}M tokens</span>
                  <span>×</span>
                  <span className="text-purple-500">{dbuPerMToken} DBU/M</span>
                  <span>=</span>
                  <span className="text-orange-500">{formatNumber(currentCost.monthlyDBUs)} DBUs</span>
                  <span>×</span>
                  <span className="text-pink-500">${dbuPriceDisplay}/DBU</span>
                  <span>=</span>
                  <span className="text-orange-600 font-semibold">{formatCurrency(currentCost.totalCost)}</span>
                </>
              )
            }
            
            // Lakebase
            if (form.workload_type === 'LAKEBASE') {
              return (
                <>
                  <span className="text-blue-500">{form.lakebase_cu || 1} CU</span>
                  <span>×</span>
                  <span className="text-purple-500">{form.lakebase_ha_nodes || 1} nodes</span>
                  <span>×</span>
                  <span className="text-green-500">{hoursPerMonth.toFixed(0)}h</span>
                  <span>=</span>
                  <span className="text-orange-500">{formatNumber(currentCost.monthlyDBUs)} DBUs</span>
                  <span>×</span>
                  <span className="text-pink-500">${dbuPriceDisplay}/DBU</span>
                  <span>=</span>
                  <span className="text-orange-600 font-semibold">{formatCurrency(currentCost.totalCost)}</span>
                </>
              )
            }
            
            // Model Serving
            if (form.workload_type === 'MODEL_SERVING') {
              return (
                <>
                  <span className="text-purple-500">{currentCost.dbuPerHour?.toFixed(2) || '2.00'} DBU/hr</span>
                  <span>×</span>
                  <span className="text-green-500">{hoursPerMonth.toFixed(0)}h</span>
                  <span>=</span>
                  <span className="text-orange-500">{formatNumber(currentCost.monthlyDBUs)} DBUs</span>
                  <span>×</span>
                  <span className="text-pink-500">${dbuPriceDisplay}/DBU</span>
                  <span>=</span>
                  <span className="text-orange-600 font-semibold">{formatCurrency(currentCost.totalCost)}</span>
                </>
              )
            }
            
            // Compute workloads (JOBS, ALL_PURPOSE, DLT, DBSQL)
            const hasVMCost = currentCost.vmCost > 0
            return (
              <>
                {currentCost.dbuPerHour && currentCost.dbuPerHour > 0 && (
                  <>
                    <span className="text-purple-500">{currentCost.dbuPerHour.toFixed(2)} DBU/hr</span>
                    <span>×</span>
                  </>
                )}
                <span className="text-green-500">{hoursPerMonth.toFixed(0)}h</span>
                <span>=</span>
                <span className="text-orange-500">{formatNumber(currentCost.monthlyDBUs)} DBUs</span>
                <span>×</span>
                <span className="text-pink-500">${dbuPriceDisplay}/DBU</span>
                {hasVMCost ? (
                  <>
                    <span className="mx-1">|</span>
                    <span className="text-blue-500">{formatCurrency(currentCost.dbuCost)}</span>
                    <span>+</span>
                    <span className="text-teal-500">VM: {formatCurrency(currentCost.vmCost)}</span>
                    <span>=</span>
                  </>
                ) : (
                  <span>=</span>
                )}
                <span className="text-orange-600 font-semibold">{formatCurrency(currentCost.totalCost)}</span>
              </>
            )
          })()}
        </div>
      </div>
    </div>
  )
}
