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
  sfdc_account_id?: string  // Salesforce Account ID
  customer_name?: string
  opportunity_id?: string  // Salesforce Opportunity ID
  uco_id?: string  // Salesforce Use Case ID
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
  sfdc_account_id?: string
  opportunity_id?: string
  uco_id?: string
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
  cloud?: string
  
  // Serverless toggle
  serverless_enabled?: boolean
  serverless_mode?: string
  
  // Classic Compute Configuration
  photon_enabled?: boolean
  driver_node_type?: string
  worker_node_type?: string
  num_workers?: number
  
  // DLT Configuration
  dlt_edition?: string
  
  // DBSQL Configuration
  dbsql_warehouse_type?: string
  dbsql_warehouse_size?: string
  dbsql_num_clusters?: number
  dbsql_vm_pricing_tier?: string
  dbsql_vm_payment_option?: string
  
  // Vector Search Configuration
  vector_search_mode?: string
  vector_capacity_millions?: number
  
  // Model Serving Configuration
  model_serving_gpu_type?: string
  
  // Lakebase Configuration
  lakebase_cu?: number
  lakebase_storage_gb?: number
  lakebase_ha_nodes?: number
  lakebase_backup_retention_days?: number
  
  // Foundation Model API Configuration (Proprietary)
  fmapi_provider?: string
  fmapi_model?: string
  fmapi_endpoint_type?: string
  fmapi_context_length?: string
  fmapi_rate_type?: string  // input_token, output_token, cache_read, cache_write
  fmapi_quantity?: number   // quantity in millions (M)
  
  // Usage Configuration
  runs_per_day?: number
  avg_runtime_minutes?: number
  days_per_month?: number
  hours_per_month?: number
  
  // Pricing Configuration
  driver_pricing_tier?: string
  worker_pricing_tier?: string
  driver_payment_option?: string
  worker_payment_option?: string
  
  // Additional Configuration
  workload_config?: Record<string, unknown>
  notes?: string
  
  created_at: string
  updated_at: string
}

// FMAPI Rate Types for Foundation Model (Proprietary)
export interface FMAPIRateType {
  id: string
  name: string
  description?: string
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
  instance_family?: string
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
  input_price_per_million?: number
  output_price_per_million?: number
}

// Model Serving GPU Types
export interface ModelServingGPUType {
  id: string
  name: string
  dbu_per_hour: number
  description?: string
}

// Foundation Models (Databricks) Configuration
export interface FMAPIDatabricksConfig {
  model_types: FMAPIDatabricksModelType[]
  models: {
    llm: FMAPIModelOption[]
    embedding: FMAPIModelOption[]
  }
  inference_types: FMAPIInferenceType[]
}

export interface FMAPIDatabricksModelType {
  id: string
  name: string
  has_output_tokens: boolean
}

export interface FMAPIModelOption {
  id: string
  name: string
}

export interface FMAPIInferenceType {
  id: string
  name: string
  description?: string
}

// Foundation Models (Proprietary) Configuration
export interface FMAPIProprietaryConfig {
  providers: FMAPIProprietaryProvider[]
  endpoint_types: FMAPIEndpointType[]
  context_lengths: FMAPIContextLength[]
}

export interface FMAPIProprietaryProvider {
  id: string
  name: string
  models: FMAPIModelOption[]
}

export interface FMAPIEndpointType {
  id: string
  name: string
}

export interface FMAPIContextLength {
  id: string
  name: string
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
