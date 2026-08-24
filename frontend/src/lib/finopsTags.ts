/** FinOps tagging helpers — keep keys in sync with etl/finops/TAGGING.md */

export const FINOPS_TAG_ESTIMATE_ID = 'lakemeter_estimate_id'
export const FINOPS_TAG_WORKLOAD_TYPE = 'lakemeter_workload_type'
export const FINOPS_TAG_LINE_ITEM_ID = 'lakemeter_line_item_id'

export type FinOpsTagMap = Record<string, string>

export interface FinOpsLineItemTagSource {
  line_item_id: string
  workload_name?: string
  workload_type?: string | null
}

export function estimateTags(estimateId: string): FinOpsTagMap {
  return { [FINOPS_TAG_ESTIMATE_ID]: estimateId }
}

export function lineItemTags(
  estimateId: string,
  item: FinOpsLineItemTagSource
): FinOpsTagMap {
  const tags: FinOpsTagMap = {
    [FINOPS_TAG_ESTIMATE_ID]: estimateId,
  }
  if (item.workload_type) {
    tags[FINOPS_TAG_WORKLOAD_TYPE] = String(item.workload_type).toUpperCase()
  }
  if (item.line_item_id) {
    tags[FINOPS_TAG_LINE_ITEM_ID] = item.line_item_id
  }
  return tags
}

/** Databricks custom tag UI / CLI friendly key=value lines */
export function formatTagsKeyValue(tags: FinOpsTagMap): string {
  return Object.entries(tags)
    .map(([k, v]) => `${k}=${v}`)
    .join('\n')
}

/** JSON object suitable for serverless usage policies / automation */
export function formatTagsJson(tags: FinOpsTagMap): string {
  return JSON.stringify(tags, null, 2)
}

export function buildEstimateTagPack(
  estimateId: string,
  lineItems: FinOpsLineItemTagSource[]
): {
  estimate: FinOpsTagMap
  line_items: Array<{
    line_item_id: string
    workload_name?: string
    workload_type?: string | null
    tags: FinOpsTagMap
  }>
} {
  return {
    estimate: estimateTags(estimateId),
    line_items: lineItems.map((item) => ({
      line_item_id: item.line_item_id,
      workload_name: item.workload_name,
      workload_type: item.workload_type,
      tags: lineItemTags(estimateId, item),
    })),
  }
}
