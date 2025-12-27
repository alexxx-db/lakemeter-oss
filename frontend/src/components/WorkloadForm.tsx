import { useState, useEffect } from 'react'
import { BoltIcon, CloudIcon } from '@heroicons/react/24/outline'
import clsx from 'clsx'
import toast from 'react-hot-toast'
import { useStore } from '../store/useStore'
import SearchableSelect from './SearchableSelect'
import type { LineItem, WorkloadType } from '../types'

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
    fmapiDatabricksConfig,
    fmapiProprietaryConfig,
    selectedCloud,
    createLineItem,
    updateLineItem,
    fetchLineItems,
    clearSingleWorkloadCost,
    markItemCalculating
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
    dbsql_vm_pricing_tier: 'on_demand',
    dbsql_vm_payment_option: 'no_upfront',
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
    fmapi_context_length: 'all',
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
    dbsql_vm_pricing_tier: 'on_demand',
    dbsql_vm_payment_option: 'no_upfront',
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
    fmapi_context_length: 'all',
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
        dbsql_vm_pricing_tier: lineItem.dbsql_vm_pricing_tier || 'on_demand',
        dbsql_vm_payment_option: lineItem.dbsql_vm_payment_option || 'no_upfront',
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
        fmapi_context_length: lineItem.fmapi_context_length || 'all',
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
        data.dbsql_vm_pricing_tier = form.dbsql_vm_pricing_tier
        data.dbsql_vm_payment_option = form.dbsql_vm_payment_option
      } else {
        data.dbsql_warehouse_type = null
        data.dbsql_warehouse_size = null
        data.dbsql_num_clusters = null
        data.dbsql_vm_pricing_tier = null
        data.dbsql_vm_payment_option = null
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
            {workloadTypes.map(wt => (
              <option key={wt.workload_type} value={wt.workload_type}>
                {wt.display_name}
              </option>
            ))}
          </select>
          {isWorkloadTypeInvalid && (
            <p className="text-xs text-red-500 mt-1">Unknown workload type: {form.workload_type}</p>
          )}
        </div>
      </div>
      
      
      {/* Feature Toggles Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* Serverless Toggle - left */}
        {selectedWorkloadType?.show_serverless_toggle && (
          <div className={clsx(
            "p-3 rounded-lg border transition-all",
            form.serverless_enabled 
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
                  form.serverless_enabled ? "text-teal-700 dark:text-teal-300 font-medium" : "text-[var(--text-secondary)]"
                )}>Serverless</span>
              </div>
              <button
                type="button"
                onClick={() => setForm(f => ({ ...f, serverless_enabled: !f.serverless_enabled }))}
                className={clsx('toggle', form.serverless_enabled ? 'toggle-checked' : 'toggle-unchecked')}
              >
                <span className={clsx('toggle-knob', form.serverless_enabled ? 'toggle-knob-checked' : 'toggle-knob-unchecked')} />
              </button>
            </div>
            
            {/* Serverless Mode Dropdown - appears when serverless is enabled */}
            {form.serverless_enabled && (
              <div className="mt-3 pt-3 border-t border-teal-200 dark:border-teal-700">
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
              </div>
            )}
          </div>
        )}
        
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
                      <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Pricing Tier</label>
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
              <div className="flex items-center gap-2 mb-3">
                <div className="w-2 h-2 rounded-full bg-green-500"></div>
                <h4 className="text-sm font-semibold text-[var(--text-primary)]">Worker Nodes</h4>
                <span className="text-xs text-[var(--text-muted)]">({form.num_workers} node{form.num_workers !== 1 ? 's' : ''})</span>
              </div>
              
              <div className="space-y-3">
                {/* Instance Type & Count Row */}
                <div className="grid grid-cols-4 gap-3">
                  <div className="col-span-3">
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
                  <div>
                    <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Count</label>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={form.num_workers}
                      onChange={(e) => setForm(f => ({ ...f, num_workers: parseInt(e.target.value) || 1 }))}
                      className="w-full text-sm"
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
                      <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Pricing Tier</label>
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
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* Serverless Toggle */}
                <div className={clsx(
                  "p-3 rounded-lg border transition-all",
                  form.dbsql_warehouse_type === 'SERVERLESS'
                    ? "bg-teal-50 dark:bg-teal-900/20 border-teal-200 dark:border-teal-700" 
                    : "bg-[var(--bg-tertiary)] border-[var(--border-primary)]"
                )}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CloudIcon className={clsx(
                        "w-4 h-4",
                        form.dbsql_warehouse_type === 'SERVERLESS' ? "text-teal-600 dark:text-teal-400" : "text-teal-500 dark:text-teal-400"
                      )} />
                      <span className={clsx(
                        "text-sm",
                        form.dbsql_warehouse_type === 'SERVERLESS' ? "text-teal-700 dark:text-teal-300 font-medium" : "text-[var(--text-secondary)]"
                      )}>Serverless</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setForm(f => ({ 
                        ...f, 
                        dbsql_warehouse_type: f.dbsql_warehouse_type === 'SERVERLESS' ? 'PRO' : 'SERVERLESS' 
                      }))}
                      className={clsx('toggle', form.dbsql_warehouse_type === 'SERVERLESS' ? 'toggle-checked' : 'toggle-unchecked')}
                    >
                      <span className={clsx('toggle-knob', form.dbsql_warehouse_type === 'SERVERLESS' ? 'toggle-knob-checked' : 'toggle-knob-unchecked')} />
                    </button>
                  </div>
                  
                  {form.dbsql_warehouse_type === 'SERVERLESS' && (
                    <p className="text-xs text-teal-600 dark:text-teal-400 mt-2">
                      Fully managed SQL compute
                    </p>
                  )}
                </div>
                
                {/* Warehouse Type dropdown - only when not serverless */}
                {form.dbsql_warehouse_type !== 'SERVERLESS' && (
                  <div className="p-3 rounded-lg border bg-[var(--bg-tertiary)] border-[var(--border-primary)]">
                    <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Warehouse Type</label>
                    <select
                      value={form.dbsql_warehouse_type}
                      onChange={(e) => setForm(f => ({ ...f, dbsql_warehouse_type: e.target.value }))}
                      className="w-full text-sm"
                    >
                      <option value="PRO">Pro</option>
                      <option value="CLASSIC">Classic</option>
                    </select>
                  </div>
                )}
              </div>
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
            
            {/* Pricing Tier - only for Pro and Classic warehouse types (not Serverless) */}
            {(form.dbsql_warehouse_type === 'PRO' || form.dbsql_warehouse_type === 'CLASSIC') && (
              <div>
                <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Pricing Tier</label>
                <select
                  value={form.dbsql_vm_pricing_tier}
                  onChange={(e) => setForm(f => ({ ...f, dbsql_vm_pricing_tier: e.target.value }))}
                  className="w-full text-sm"
                >
                  <option value="on_demand">On-Demand</option>
                  <option value="reserved_1y">1-Year Reserved</option>
                  <option value="reserved_3y">3-Year Reserved</option>
                </select>
              </div>
            )}
            
            {/* Payment Option - only for AWS and reserved pricing tiers */}
            {(form.dbsql_warehouse_type === 'PRO' || form.dbsql_warehouse_type === 'CLASSIC') && 
             selectedCloud === 'aws' && 
             form.dbsql_vm_pricing_tier.startsWith('reserved') && (
              <div>
                <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Payment Option</label>
                <select
                  value={form.dbsql_vm_payment_option}
                  onChange={(e) => setForm(f => ({ ...f, dbsql_vm_payment_option: e.target.value }))}
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
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Capacity Units (Millions)</label>
              <input
                type="number"
                min={1}
                max={100}
                value={form.vector_capacity_millions}
                onChange={(e) => setForm(f => ({ ...f, vector_capacity_millions: parseInt(e.target.value) || 1 }))}
                className="w-full text-sm"
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
                  : 'e.g., 10 = 10M tokens'}
              />
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
                onChange={(e) => setForm(f => ({ ...f, fmapi_provider: e.target.value, fmapi_model: '' }))}
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
                onChange={(e) => setForm(f => ({ ...f, fmapi_model: e.target.value }))}
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
                {fmapiProprietaryModels.context_lengths.map(length => (
                  <option key={length.id} value={length.id}>{length.name}</option>
                ))}
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
                <option value="input_token">Input Token</option>
                <option value="output_token">Output Token</option>
                <option value="cache_read">Cache Read</option>
                <option value="cache_write">Cache Write</option>
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
                placeholder="e.g., 10 = 10M tokens"
              />
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
            {/* Usage - Runs */}
            {selectedWorkloadType?.show_usage_runs && (
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
      
      {/* Notes - Multi-line for detailed configuration rationale */}
      <div>
        <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">
          Notes
          <span className="ml-1 font-normal text-[var(--text-muted)]">(configuration rationale, assumptions, trade-offs)</span>
        </label>
        <textarea
          value={form.notes}
          onChange={(e) => setForm(f => ({ ...f, notes: e.target.value }))}
          placeholder="Configuration rationale and assumptions...&#10;• Why this configuration was chosen&#10;• Sizing assumptions (data volume, users, etc.)&#10;• Cost optimization choices&#10;• Trade-offs to be aware of"
          className="w-full text-sm min-h-[80px] resize-y"
          rows={3}
        />
      </div>
      
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
