import { useState, useEffect } from 'react'
import { BoltIcon, CloudIcon, InformationCircleIcon, CurrencyDollarIcon } from '@heroicons/react/24/outline'
import clsx from 'clsx'
import toast from 'react-hot-toast'
import { useStore } from '../store/useStore'
import type { LineItem, WorkloadType } from '../types'

interface Props {
  estimateId: string
  lineItem: LineItem | null
  onClose: () => void
  onSave?: () => void
  inline?: boolean
}

export default function WorkloadForm({ estimateId, lineItem, onClose, onSave, inline = false }: Props) {
  const { 
    workloadTypes, 
    instanceTypes, 
    dbsqlSizes, 
    dltEditions, 
    fmapiProviders,
    vmPricingTiers,
    vmPaymentOptions,
    selectedCloud,
    createLineItem,
    updateLineItem,
    updateLineItemLocal,
    fetchLineItems
  } = useStore()
  
  const [isSaving, setIsSaving] = useState(false)
  const [form, setForm] = useState({
    workload_name: '',
    workload_type: 'JOBS',
    is_serverless: false,
    serverless_performance_mode: 'standard',
    driver_node_type: '',
    worker_node_type: '',
    num_workers: 2,
    autoscale_enabled: false,
    autoscale_min_workers: 1,
    autoscale_max_workers: 8,
    photon_enabled: false,
    spot_enabled: false,
    spot_percentage: 70,
    dlt_edition: 'pro',
    dlt_pipeline_mode: 'triggered',
    dbsql_warehouse_type: 'serverless',
    dbsql_warehouse_size: 'small',
    vector_search_mode: 'delta_sync',
    lakebase_instance_type: 'small',
    lakebase_storage_gb: 100,
    fmapi_provider: 'databricks',
    fmapi_model: '',
    fmapi_input_tokens_per_month: 0,
    fmapi_output_tokens_per_month: 0,
    hours_per_day: 8,
    days_per_month: 22,
    runs_per_day: 1,
    avg_runtime_minutes: 30,
    vm_pricing_tier: 'on_demand',
    vm_payment_option: 'no_upfront',
    notes: ''
  })
  
  useEffect(() => {
    if (lineItem) {
      setForm({
        workload_name: lineItem.workload_name || '',
        workload_type: lineItem.workload_type || 'JOBS',
        is_serverless: lineItem.is_serverless || false,
        serverless_performance_mode: lineItem.serverless_performance_mode || 'standard',
        driver_node_type: lineItem.driver_node_type || '',
        worker_node_type: lineItem.worker_node_type || '',
        num_workers: lineItem.num_workers || 2,
        autoscale_enabled: lineItem.autoscale_enabled || false,
        autoscale_min_workers: lineItem.autoscale_min_workers || 1,
        autoscale_max_workers: lineItem.autoscale_max_workers || 8,
        photon_enabled: lineItem.photon_enabled || false,
        spot_enabled: lineItem.spot_enabled || false,
        spot_percentage: lineItem.spot_percentage || 70,
        dlt_edition: lineItem.dlt_edition || 'pro',
        dlt_pipeline_mode: lineItem.dlt_pipeline_mode || 'triggered',
        dbsql_warehouse_type: lineItem.dbsql_warehouse_type || 'serverless',
        dbsql_warehouse_size: lineItem.dbsql_warehouse_size || 'small',
        vector_search_mode: lineItem.vector_search_mode || 'delta_sync',
        lakebase_instance_type: lineItem.lakebase_instance_type || 'small',
        lakebase_storage_gb: lineItem.lakebase_storage_gb || 100,
        fmapi_provider: lineItem.fmapi_provider || 'databricks',
        fmapi_model: lineItem.fmapi_model || '',
        fmapi_input_tokens_per_month: lineItem.fmapi_input_tokens_per_month || 0,
        fmapi_output_tokens_per_month: lineItem.fmapi_output_tokens_per_month || 0,
        hours_per_day: lineItem.hours_per_day || 8,
        days_per_month: lineItem.days_per_month || 22,
        runs_per_day: lineItem.runs_per_day || 1,
        avg_runtime_minutes: lineItem.avg_runtime_minutes || 30,
        vm_pricing_tier: lineItem.vm_pricing_tier || 'on_demand',
        vm_payment_option: lineItem.vm_payment_option || 'no_upfront',
        notes: lineItem.notes || ''
      })
    }
  }, [lineItem])
  
  // Update line item locally for real-time cost preview when pricing-related fields change
  useEffect(() => {
    if (lineItem) {
      updateLineItemLocal(lineItem.line_item_id, {
        vm_pricing_tier: form.vm_pricing_tier,
        vm_payment_option: form.vm_payment_option,
        spot_enabled: form.spot_enabled,
        driver_node_type: form.driver_node_type,
        worker_node_type: form.worker_node_type,
        num_workers: form.num_workers,
        hours_per_day: form.hours_per_day,
        days_per_month: form.days_per_month,
        runs_per_day: form.runs_per_day,
        avg_runtime_minutes: form.avg_runtime_minutes,
        is_serverless: form.is_serverless,
        photon_enabled: form.photon_enabled,
        dbsql_warehouse_size: form.dbsql_warehouse_size,
      })
      onSave?.() // Mark estimate as having unsaved changes
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    lineItem?.line_item_id,
    form.vm_pricing_tier,
    form.vm_payment_option,
    form.spot_enabled,
    form.driver_node_type,
    form.worker_node_type,
    form.num_workers,
    form.hours_per_day,
    form.days_per_month,
    form.runs_per_day,
    form.avg_runtime_minutes,
    form.is_serverless,
    form.photon_enabled,
    form.dbsql_warehouse_size,
    updateLineItemLocal,
  ])
  
  const selectedWorkloadType: WorkloadType | undefined = workloadTypes.find(w => w.workload_type === form.workload_type)
  const selectedFmapiProvider = fmapiProviders.find(p => p.provider === form.fmapi_provider)
  
  const computedSku = (): string | null => {
    if (!selectedWorkloadType) return null
    
    if (form.is_serverless && selectedWorkloadType.sku_product_type_serverless) {
      return selectedWorkloadType.sku_product_type_serverless
    }
    if (form.photon_enabled && selectedWorkloadType.sku_product_type_photon) {
      return selectedWorkloadType.sku_product_type_photon
    }
    return selectedWorkloadType.sku_product_type_standard || null
  }
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!form.workload_name.trim()) {
      toast.error('Enter a workload name')
      return
    }
    
    setIsSaving(true)
    try {
      const data = {
        ...form,
        selected_sku: computedSku()
      }
      
      if (lineItem) {
        await updateLineItem(lineItem.line_item_id, data)
        toast.success('Workload updated')
      } else {
        await createLineItem({ ...data, estimate_id: estimateId })
        toast.success('Workload added')
      }
      fetchLineItems(estimateId)
      onSave?.()
      onClose()
    } catch {
      toast.error('Failed to save')
    } finally {
      setIsSaving(false)
    }
  }
  
  // Show VM config for classic compute (not serverless)
  const showVMConfig = selectedWorkloadType?.show_compute_config && !form.is_serverless
  
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
            onChange={(e) => setForm(f => ({ ...f, workload_type: e.target.value, is_serverless: false, photon_enabled: false }))}
            className="w-full"
          >
            {workloadTypes.map(wt => (
              <option key={wt.workload_type} value={wt.workload_type}>
                {wt.display_name}
              </option>
            ))}
          </select>
        </div>
      </div>
      
      {/* SKU Preview */}
      {computedSku() && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border-primary)]">
          <InformationCircleIcon className="w-4 h-4 text-[var(--text-muted)] flex-shrink-0" />
          <div className="text-sm">
            <span className="text-[var(--text-muted)]">SKU: </span>
            <span className="font-mono text-orange-600 dark:text-orange-400">{computedSku()}</span>
          </div>
        </div>
      )}
      
      {/* Feature Toggles Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* Serverless Toggle - on the left */}
        {selectedWorkloadType?.show_serverless_toggle && (
          <div className="p-3 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border-primary)]">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CloudIcon className="w-4 h-4 text-teal-500 dark:text-teal-400" />
                <span className="text-sm text-[var(--text-secondary)]">Serverless</span>
              </div>
              <button
                type="button"
                onClick={() => setForm(f => ({ ...f, is_serverless: !f.is_serverless, spot_enabled: false }))}
                className={clsx('toggle', form.is_serverless ? 'toggle-checked' : 'toggle-unchecked')}
              >
                <span className={clsx('toggle-knob', form.is_serverless ? 'toggle-knob-checked' : 'toggle-knob-unchecked')} />
              </button>
            </div>
          </div>
        )}
        
        {/* Photon Toggle - on the right */}
        {selectedWorkloadType?.show_photon_toggle && !form.is_serverless && (
          <div className={clsx(
            "p-3 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border-primary)]",
            !selectedWorkloadType?.show_serverless_toggle && "sm:col-start-2"
          )}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <BoltIcon className="w-4 h-4 text-orange-600 dark:text-orange-500" />
                <span className="text-sm text-[var(--text-secondary)]">Photon</span>
              </div>
              <button
                type="button"
                onClick={() => setForm(f => ({ ...f, photon_enabled: !f.photon_enabled }))}
                className={clsx('toggle', form.photon_enabled ? 'toggle-checked' : 'toggle-unchecked')}
              >
                <span className={clsx('toggle-knob', form.photon_enabled ? 'toggle-knob-checked' : 'toggle-knob-unchecked')} />
              </button>
            </div>
          </div>
        )}
      </div>
      
      {/* Configuration Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Classic Compute Config */}
        {showVMConfig && (
          <>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Driver Node</label>
              <select
                value={form.driver_node_type}
                onChange={(e) => setForm(f => ({ ...f, driver_node_type: e.target.value }))}
                className="w-full text-sm"
              >
                <option value="">Select type</option>
                {instanceTypes.map(it => (
                  <option key={it.id} value={it.id}>
                    {it.name} ({it.vcpus}vCPU, {it.memory_gb}GB)
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Worker Node</label>
              <select
                value={form.worker_node_type}
                onChange={(e) => setForm(f => ({ ...f, worker_node_type: e.target.value }))}
                className="w-full text-sm"
              >
                <option value="">Select type</option>
                {instanceTypes.map(it => (
                  <option key={it.id} value={it.id}>
                    {it.name} ({it.vcpus}vCPU, {it.memory_gb}GB)
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Number of Workers</label>
              <input
                type="number"
                min={1}
                max={100}
                value={form.num_workers}
                onChange={(e) => setForm(f => ({ ...f, num_workers: parseInt(e.target.value) || 1 }))}
                className="w-full text-sm"
              />
            </div>
            
            {/* VM Pricing Tier */}
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">VM Pricing Tier</label>
              <select
                value={form.vm_pricing_tier}
                onChange={(e) => setForm(f => ({ ...f, vm_pricing_tier: e.target.value }))}
                className="w-full text-sm"
              >
                {vmPricingTiers.map(tier => (
                  <option key={tier.id} value={tier.id}>
                    {tier.name}
                  </option>
                ))}
              </select>
            </div>
            
            {/* Payment Option (AWS Reserved Instances only) */}
            {selectedCloud === 'aws' && form.vm_pricing_tier.startsWith('reserved') && (
              <div>
                <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Payment Option</label>
                <select
                  value={form.vm_payment_option}
                  onChange={(e) => setForm(f => ({ ...f, vm_payment_option: e.target.value }))}
                  className="w-full text-sm"
                >
                  {vmPaymentOptions.map(opt => (
                    <option key={opt.id} value={opt.id}>
                      {opt.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </>
        )}
        
        {/* DLT Config */}
        {selectedWorkloadType?.show_dlt_config && (
          <>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">DLT Edition</label>
              <select
                value={form.dlt_edition}
                onChange={(e) => setForm(f => ({ ...f, dlt_edition: e.target.value }))}
                className="w-full text-sm"
              >
                {dltEditions.map(ed => (
                  <option key={ed.id} value={ed.id}>{ed.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Pipeline Mode</label>
              <select
                value={form.dlt_pipeline_mode}
                onChange={(e) => setForm(f => ({ ...f, dlt_pipeline_mode: e.target.value }))}
                className="w-full text-sm"
              >
                <option value="triggered">Triggered</option>
                <option value="continuous">Continuous</option>
              </select>
            </div>
          </>
        )}
        
        {/* DBSQL Config */}
        {selectedWorkloadType?.show_dbsql_config && (
          <>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Warehouse Type</label>
              <select
                value={form.dbsql_warehouse_type}
                onChange={(e) => setForm(f => ({ ...f, dbsql_warehouse_type: e.target.value }))}
                className="w-full text-sm"
              >
                <option value="serverless">Serverless</option>
                <option value="pro">Pro</option>
                <option value="classic">Classic</option>
              </select>
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
          </>
        )}
        
        {/* FMAPI Config */}
        {selectedWorkloadType?.show_fmapi_config && (
          <>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Provider</label>
              <select
                value={form.fmapi_provider}
                onChange={(e) => setForm(f => ({ ...f, fmapi_provider: e.target.value, fmapi_model: '' }))}
                className="w-full text-sm"
              >
                {fmapiProviders.map(p => (
                  <option key={p.provider} value={p.provider}>
                    {p.provider.charAt(0).toUpperCase() + p.provider.slice(1)}
                  </option>
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
                {selectedFmapiProvider?.models.map(m => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
            </div>
          </>
        )}
        
        {/* Lakebase Config */}
        {selectedWorkloadType?.show_lakebase_config && (
          <>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Instance Type</label>
              <select
                value={form.lakebase_instance_type}
                onChange={(e) => setForm(f => ({ ...f, lakebase_instance_type: e.target.value }))}
                className="w-full text-sm"
              >
                <option value="small">Small (2 vCPU)</option>
                <option value="medium">Medium (4 vCPU)</option>
                <option value="large">Large (8 vCPU)</option>
                <option value="xlarge">X-Large (16 vCPU)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Storage (GB)</label>
              <input
                type="number"
                min={10}
                value={form.lakebase_storage_gb}
                onChange={(e) => setForm(f => ({ ...f, lakebase_storage_gb: parseInt(e.target.value) || 100 }))}
                className="w-full text-sm"
              />
            </div>
          </>
        )}
        
        {/* Usage - Hours */}
        {selectedWorkloadType?.show_usage_hours && (
          <>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Hours/Day</label>
              <input
                type="number"
                min={0}
                max={24}
                step={0.5}
                value={form.hours_per_day}
                onChange={(e) => setForm(f => ({ ...f, hours_per_day: parseFloat(e.target.value) || 0 }))}
                className="w-full text-sm"
              />
            </div>
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
            {/* Spot VMs Toggle - Only for classic compute */}
            {showVMConfig && (
              <div className="flex items-end">
                <div className="p-3 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border-primary)] w-full">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CurrencyDollarIcon className="w-4 h-4 text-yellow-500 dark:text-yellow-400" />
                      <div>
                        <span className="text-sm text-[var(--text-secondary)]">Spot Workers</span>
                        <p className="text-xs text-[var(--text-muted)]">Driver stays on-demand</p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setForm(f => ({ ...f, spot_enabled: !f.spot_enabled }))}
                      className={clsx('toggle', form.spot_enabled ? 'toggle-checked' : 'toggle-unchecked')}
                    >
                      <span className={clsx('toggle-knob', form.spot_enabled ? 'toggle-knob-checked' : 'toggle-knob-unchecked')} />
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        
        {/* Usage - Runs */}
        {selectedWorkloadType?.show_usage_runs && (
          <>
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
            {/* Spot VMs Toggle - Only for classic compute, beside Avg Runtime */}
            {showVMConfig && (
              <div className="flex items-end">
                <div className="p-3 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border-primary)] w-full">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CurrencyDollarIcon className="w-4 h-4 text-yellow-500 dark:text-yellow-400" />
                      <div>
                        <span className="text-sm text-[var(--text-secondary)]">Spot Workers</span>
                        <p className="text-xs text-[var(--text-muted)]">Driver stays on-demand</p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setForm(f => ({ ...f, spot_enabled: !f.spot_enabled }))}
                      className={clsx('toggle', form.spot_enabled ? 'toggle-checked' : 'toggle-unchecked')}
                    >
                      <span className={clsx('toggle-knob', form.spot_enabled ? 'toggle-knob-checked' : 'toggle-knob-unchecked')} />
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        
        {/* Usage - Tokens */}
        {selectedWorkloadType?.show_usage_tokens && (
          <>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Input Tokens/Mo (M)</label>
              <input
                type="number"
                min={0}
                step={0.1}
                value={form.fmapi_input_tokens_per_month / 1000000}
                onChange={(e) => setForm(f => ({ ...f, fmapi_input_tokens_per_month: (parseFloat(e.target.value) || 0) * 1000000 }))}
                className="w-full text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Output Tokens/Mo (M)</label>
              <input
                type="number"
                min={0}
                step={0.1}
                value={form.fmapi_output_tokens_per_month / 1000000}
                onChange={(e) => setForm(f => ({ ...f, fmapi_output_tokens_per_month: (parseFloat(e.target.value) || 0) * 1000000 }))}
                className="w-full text-sm"
              />
            </div>
          </>
        )}
      </div>
      
      {/* Notes */}
      <div>
        <label className="block text-xs font-medium mb-1.5 text-[var(--text-secondary)]">Notes</label>
        <input
          type="text"
          value={form.notes}
          onChange={(e) => setForm(f => ({ ...f, notes: e.target.value }))}
          placeholder="Optional notes..."
          className="w-full text-sm"
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
