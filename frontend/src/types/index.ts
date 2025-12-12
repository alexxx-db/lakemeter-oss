// API Types
export interface User {
  user_id: string
  email: string
  full_name?: string
  role?: string
  is_active: boolean
  last_login_at?: string
  created_at: string
  updated_at: string
}

export interface Estimate {
  estimate_id: string
  estimate_name: string
  owner_user_id?: string
  customer_sfdc_id?: string
  customer_name?: string
  uco_opportunity_id?: string
  cloud?: string
  region?: string
  tier?: string
  status?: string
  version: number
  template_id?: string
  original_prompt?: string
  is_deleted: boolean
  created_at: string
  updated_at: string
  updated_by?: string
  line_items: LineItemSummary[]
}

export interface LineItemSummary {
  line_item_id: string
  workload_name: string
  workload_type?: string
  display_order: number
}

export interface EstimateListItem {
  estimate_id: string
  estimate_name: string
  customer_name?: string
  cloud?: string
  region?: string
  tier?: string
  status?: string
  version: number
  line_item_count: number
  created_at: string
  updated_at: string
}

export interface LineItem {
  line_item_id: string
  estimate_id: string
  display_order: number
  workload_name: string
  workload_type?: string
  
  // Serverless toggle
  is_serverless?: boolean
  serverless_performance_mode?: string
  
  // Classic Compute Configuration
  driver_node_type?: string
  worker_node_type?: string
  num_workers?: number
  autoscale_enabled?: boolean
  autoscale_min_workers?: number
  autoscale_max_workers?: number
  photon_enabled?: boolean
  
  // DLT Configuration
  dlt_edition?: string
  dlt_pipeline_mode?: string
  
  // DBSQL Configuration
  dbsql_warehouse_type?: string
  dbsql_warehouse_size?: string
  dbsql_num_clusters?: number
  
  // Serverless Products Configuration
  serverless_product?: string
  serverless_size?: string
  
  // Vector Search Configuration
  vector_search_endpoint_type?: string
  vector_search_mode?: string
  
  // Lakebase Configuration
  lakebase_instance_type?: string
  lakebase_storage_gb?: number
  lakebase_cu?: number
  lakebase_ha_enabled?: boolean
  lakebase_backup_retention_days?: number
  
  // Foundation Model API Configuration
  fmapi_provider?: string
  fmapi_model?: string
  fmapi_endpoint_type?: string
  fmapi_context_length?: string
  fmapi_input_tokens_per_month?: number
  fmapi_output_tokens_per_month?: number
  
  // Usage Configuration
  hours_per_day?: number
  days_per_month?: number
  runs_per_day?: number
  avg_runtime_minutes?: number
  
  // Pricing Configuration
  vm_pricing_tier?: string
  vm_payment_option?: string
  spot_enabled?: boolean
  spot_percentage?: number
  
  // Selected SKU
  selected_sku?: string
  
  // Additional Configuration
  workload_config?: Record<string, unknown>
  notes?: string
  
  created_at: string
  updated_at: string
}

export interface WorkloadType {
  workload_type: string
  display_name: string
  description?: string
  
  // Configuration visibility flags
  show_compute_config: boolean
  show_serverless_toggle: boolean
  show_serverless_performance_mode: boolean
  show_photon_toggle: boolean
  show_dlt_config: boolean
  show_dbsql_config: boolean
  show_serverless_product: boolean
  show_fmapi_config: boolean
  show_lakebase_config: boolean
  show_vector_search_mode: boolean
  show_vm_pricing: boolean
  show_usage_hours: boolean
  show_usage_runs: boolean
  show_usage_tokens: boolean
  
  // SKU product types
  sku_product_type_standard?: string
  sku_product_type_photon?: string
  sku_product_type_serverless?: string
  
  display_order: number
}

export interface CloudProvider {
  id: string
  name: string
  regions: Region[]
}

export interface Region {
  id: string
  name: string
}

export interface InstanceType {
  id: string
  name: string
  vcpus: number
  memory_gb: number
  dbu_rate: number
  gpu?: boolean
}

export interface DBSQLSize {
  id: string
  name: string
  dbu_per_hour: number
}

export interface DLTEdition {
  id: string
  name: string
  dbu_multiplier: number
}

export interface FMAPIProvider {
  provider: string
  models: FMAPIModel[]
}

export interface FMAPIModel {
  id: string
  name: string
  input_price_per_million: number
  output_price_per_million: number
}

// VM Pricing types
export interface VMPricing {
  cloud: string
  region: string
  instance_type: string
  pricing_tier: string
  payment_option: string
  cost_per_hour: number
  currency: string
  source?: string
  fetched_at?: string
  updated_at?: string
}

export interface VMPricingTier {
  id: string
  name: string
  description: string
}

export interface VMPaymentOption {
  id: string
  name: string
  description: string
}

export interface VMInstanceType {
  instance_type: string
}

// Salesforce types
export interface SalesforceAccount {
  salesforce_account_id: string
  salesforce_account_name: string | null
  dim_salesforce_account_region: string | null
}

export interface SalesforceOpportunity {
  id: string
  name: string | null
  accountid: string | null
}

export interface SalesforceUseCase {
  salesforce_use_case_id: string
  salesforce_use_case_name: string | null
  customer_id: string | null
  dim_canonical_customer_name: string | null
  dim_business_unit_latest: string | null
}
