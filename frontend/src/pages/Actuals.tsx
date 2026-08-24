import { useEffect, useMemo, useState } from 'react'
import {
  fetchFinopsMetadata,
  fetchFinopsSummary,
  fetchFinopsTopSkus,
  fetchFinopsVariance,
  type FinOpsMetadata,
  type FinOpsSummary,
  type FinOpsTopSkus,
  type FinOpsVariance,
} from '../api/client'

const DAY_OPTIONS = [7, 30, 90] as const

function formatUsd(value: number): string {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: value >= 1000 ? 0 : 2,
  }).format(value)
}

function formatDate(value: string | null | undefined): string | null {
  if (!value) return null
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

function applyDiscount(listUsd: number, discountPct: number): number {
  const pct = Math.max(0, Math.min(100, discountPct))
  return listUsd * (1 - pct / 100)
}

function Sparkline({ values }: { values: number[] }) {
  if (values.length === 0) {
    return <div className="h-16 text-xs text-[var(--text-muted)] flex items-end">No daily data</div>
  }
  const max = Math.max(...values, 1)
  return (
    <div className="flex items-end gap-0.5 h-16" role="img" aria-label="Daily list cost trend">
      {values.map((v, i) => (
        <div
          key={i}
          className="flex-1 min-w-[2px] rounded-t bg-lava-600/80"
          style={{ height: `${Math.max(4, (v / max) * 100)}%` }}
          title={formatUsd(v)}
        />
      ))}
    </div>
  )
}

function ProductBars({
  rows,
  discountPct,
}: {
  rows: { billing_origin_product: string; list_cost_usd: number }[]
  discountPct: number
}) {
  if (rows.length === 0) {
    return <p className="text-sm text-[var(--text-muted)]">No product breakdown for this window.</p>
  }
  const max = Math.max(...rows.map((r) => applyDiscount(r.list_cost_usd, discountPct)), 1)
  return (
    <ul className="space-y-3">
      {rows.map((row) => {
        const amount = applyDiscount(row.list_cost_usd, discountPct)
        const pct = (amount / max) * 100
        return (
          <li key={row.billing_origin_product}>
            <div className="flex justify-between text-sm mb-1 gap-4">
              <span className="font-medium text-[var(--text-primary)] truncate">
                {row.billing_origin_product}
              </span>
              <span className="tabular-nums text-[var(--text-secondary)] shrink-0">
                {formatUsd(amount)}
              </span>
            </div>
            <div className="h-2 rounded bg-[var(--bg-secondary)] overflow-hidden">
              <div className="h-full bg-lava-600" style={{ width: `${pct}%` }} />
            </div>
          </li>
        )
      })}
    </ul>
  )
}

export default function Actuals() {
  const [days, setDays] = useState<(typeof DAY_OPTIONS)[number]>(30)
  const [discountPct, setDiscountPct] = useState(0)
  const [workspaceId, setWorkspaceId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [metadata, setMetadata] = useState<FinOpsMetadata | null>(null)
  const [summary, setSummary] = useState<FinOpsSummary | null>(null)
  const [topSkus, setTopSkus] = useState<FinOpsTopSkus | null>(null)
  const [varianceId, setVarianceId] = useState('')
  const [varianceLoading, setVarianceLoading] = useState(false)
  const [varianceError, setVarianceError] = useState<string | null>(null)
  const [variance, setVariance] = useState<FinOpsVariance | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    const params = {
      days,
      ...(workspaceId.trim() ? { workspace_id: workspaceId.trim() } : {}),
    }
    Promise.all([
      fetchFinopsMetadata(),
      fetchFinopsSummary(params),
      fetchFinopsTopSkus({ ...params, limit: 25 }),
    ])
      .then(([meta, sum, skus]) => {
        if (cancelled) return
        setMetadata(meta)
        setSummary(sum)
        setTopSkus(skus)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err?.response?.data?.detail || err?.message || 'Failed to load Actuals')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [days, workspaceId])

  const commercialTotal = useMemo(() => {
    if (!summary) return 0
    return applyDiscount(summary.total_list_cost_usd, discountPct)
  }, [summary, discountPct])

  const unavailableMessage =
    summary?.message || metadata?.message || topSkus?.message || null
  const showData = Boolean(summary?.available)

  return (
    <div className="max-w-7xl xl:max-w-[1400px] 2xl:max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-16">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Actuals</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)] max-w-2xl">
          Account spend from Databricks billable usage (list cost). Separate from estimate
          planning prices — not your invoice.
        </p>
      </div>

      <div className="mb-4 rounded-md border border-[var(--border-primary)] bg-[var(--bg-secondary)] px-4 py-3 text-sm text-[var(--text-secondary)]">
        {metadata?.available && metadata.built_at ? (
          <p>
            Gold as of{' '}
            <span className="font-semibold text-[var(--text-primary)]">
              {formatDate(metadata.built_at)}
            </span>
            <span className="text-[var(--text-muted)]">
              {' '}
              · basis: {metadata.cost_basis || 'list'}
              {metadata.catalog && metadata.schema
                ? ` · ${metadata.catalog}.${metadata.schema}`
                : null}
              {typeof metadata.attributed_pct === 'number'
                ? ` · ${metadata.attributed_pct.toFixed(1)}% tagged to estimates`
                : null}
              {typeof metadata.unpriced_positive_usage_rows === 'number' &&
              metadata.unpriced_positive_usage_rows > 0
                ? ` · ${metadata.unpriced_positive_usage_rows.toLocaleString()} unpriced rows`
                : null}
            </span>
          </p>
        ) : (
          <p>
            {unavailableMessage ||
              'FinOps gold is not available yet. Deploy etl/finops and set FINOPS_WAREHOUSE_ID.'}
          </p>
        )}
        <p className="mt-1 text-xs text-[var(--text-muted)]">
          Dollars are list cost from system.billing.list_prices. Optional discount below is a
          commercial overlay only — label it for stakeholders; it is not invoice truth.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-4 mb-8">
        <div>
          <label className="block text-xs font-medium text-[var(--text-muted)] mb-1">Window</label>
          <div className="flex gap-1">
            {DAY_OPTIONS.map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => setDays(d)}
                className={`px-3 py-1.5 text-sm font-semibold rounded border transition-colors ${
                  days === d
                    ? 'border-lava-600 bg-lava-600 text-white'
                    : 'border-[var(--border-primary)] text-[var(--text-secondary)] hover:border-lava-600'
                }`}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>
        <div>
          <label
            htmlFor="actuals-workspace"
            className="block text-xs font-medium text-[var(--text-muted)] mb-1"
          >
            Workspace ID (optional)
          </label>
          <input
            id="actuals-workspace"
            type="text"
            value={workspaceId}
            onChange={(e) => setWorkspaceId(e.target.value)}
            placeholder="Filter by workspace"
            className="w-48 text-sm"
          />
        </div>
        <div>
          <label
            htmlFor="actuals-discount"
            className="block text-xs font-medium text-[var(--text-muted)] mb-1"
            title="Applies a labeled commercial overlay on list dollars"
          >
            Commercial discount %
          </label>
          <input
            id="actuals-discount"
            type="number"
            min={0}
            max={100}
            step={1}
            value={discountPct}
            onChange={(e) => setDiscountPct(Number(e.target.value) || 0)}
            className="w-24 text-right text-sm"
          />
        </div>
      </div>

      {loading && (
        <div className="py-16 text-center text-sm text-[var(--text-muted)]">Loading actuals…</div>
      )}

      {!loading && error && (
        <div className="rounded-md border border-red-300 bg-red-50 dark:bg-red-950/30 px-4 py-3 text-sm text-red-800 dark:text-red-200">
          {error}
        </div>
      )}

      {!loading && !error && !showData && (
        <div className="rounded-md border border-[var(--border-primary)] px-6 py-12 text-center">
          <p className="text-[var(--text-primary)] font-medium">Actuals not configured</p>
          <p className="mt-2 text-sm text-[var(--text-secondary)] max-w-lg mx-auto">
            {unavailableMessage ||
              'Run the lakemeter_finops_gold job, grant the app SP SELECT on gold, and set FINOPS_WAREHOUSE_ID on the app.'}
          </p>
        </div>
      )}

      {!loading && !error && showData && summary && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            <div className="rounded-md border border-[var(--border-primary)] px-4 py-4">
              <p className="text-xs uppercase tracking-wide text-[var(--text-muted)]">
                List cost ({days}d)
              </p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-[var(--text-primary)]">
                {formatUsd(summary.total_list_cost_usd)}
              </p>
              <p className="mt-1 text-xs text-[var(--text-muted)]">AC · list basis</p>
            </div>
            <div className="rounded-md border border-[var(--border-primary)] px-4 py-4">
              <p className="text-xs uppercase tracking-wide text-[var(--text-muted)]">
                After commercial overlay
              </p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-[var(--text-primary)]">
                {formatUsd(commercialTotal)}
              </p>
              <p className="mt-1 text-xs text-[var(--text-muted)]">
                {discountPct > 0 ? `${discountPct}% discount on list` : 'Same as list (0% discount)'}
              </p>
            </div>
            <div className="rounded-md border border-[var(--border-primary)] px-4 py-4">
              <p className="text-xs uppercase tracking-wide text-[var(--text-muted)] mb-2">
                Daily list cost
              </p>
              <Sparkline values={summary.daily.map((d) => d.list_cost_usd)} />
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-10">
            <section>
              <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-3">
                By billing origin product
              </h2>
              <ProductBars rows={summary.by_product} discountPct={discountPct} />
            </section>
            <section>
              <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-3">
                Top SKUs (list cost)
              </h2>
              {!topSkus?.skus?.length ? (
                <p className="text-sm text-[var(--text-muted)]">No SKU rows for this window.</p>
              ) : (
                <div className="overflow-x-auto border border-[var(--border-primary)] rounded-md">
                  <table className="min-w-full text-sm">
                    <thead className="bg-[var(--bg-secondary)] text-[var(--text-muted)] text-left">
                      <tr>
                        <th className="px-3 py-2 font-medium">SKU</th>
                        <th className="px-3 py-2 font-medium">Product</th>
                        <th className="px-3 py-2 font-medium text-right">List $</th>
                      </tr>
                    </thead>
                    <tbody>
                      {topSkus.skus.map((sku) => (
                        <tr
                          key={`${sku.sku_name}-${sku.billing_origin_product}-${sku.cloud}`}
                          className="border-t border-[var(--border-primary)]"
                        >
                          <td className="px-3 py-2 text-[var(--text-primary)] max-w-[220px] truncate">
                            {sku.sku_name}
                          </td>
                          <td className="px-3 py-2 text-[var(--text-secondary)]">
                            {sku.billing_origin_product}
                          </td>
                          <td className="px-3 py-2 text-right tabular-nums text-[var(--text-primary)]">
                            {formatUsd(applyDiscount(sku.list_cost_usd, discountPct))}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </div>

          <section className="border-t border-[var(--border-primary)] pt-8">
            <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-1">
              Estimate ↔ actual variance
            </h2>
            <p className="text-xs text-[var(--text-muted)] mb-4 max-w-2xl">
              Requires workloads tagged with{' '}
              <code className="text-[var(--text-secondary)]">lakemeter_estimate_id</code>. Copy tags
              from an estimate via <span className="font-medium">FinOps tags</span> in the
              calculator toolbar, or see{' '}
              <code className="text-[var(--text-secondary)]">etl/finops/TAGGING.md</code>. Plan is
              prorated monthly × (days/30); actuals are tagged list cost.
            </p>
            <div className="flex flex-wrap items-end gap-3 mb-4">
              <div className="flex-1 min-w-[240px]">
                <label
                  htmlFor="variance-estimate-id"
                  className="block text-xs font-medium text-[var(--text-muted)] mb-1"
                >
                  Estimate ID
                </label>
                <input
                  id="variance-estimate-id"
                  type="text"
                  value={varianceId}
                  onChange={(e) => setVarianceId(e.target.value)}
                  placeholder="UUID from Estimates"
                  className="w-full text-sm font-mono"
                />
              </div>
              <button
                type="button"
                disabled={varianceLoading || !varianceId.trim()}
                onClick={() => {
                  const id = varianceId.trim()
                  if (!id) return
                  setVarianceLoading(true)
                  setVarianceError(null)
                  setVariance(null)
                  fetchFinopsVariance(id, { days })
                    .then(setVariance)
                    .catch((err) => {
                      setVarianceError(
                        err?.response?.data?.detail || err?.message || 'Variance lookup failed'
                      )
                    })
                    .finally(() => setVarianceLoading(false))
                }}
                className="px-4 py-2 text-sm font-semibold rounded bg-lava-600 text-white disabled:opacity-50"
              >
                {varianceLoading ? 'Loading…' : 'Compare'}
              </button>
            </div>
            {varianceError && (
              <p className="text-sm text-red-700 dark:text-red-300 mb-3">{varianceError}</p>
            )}
            {variance && (
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 mb-4">
                <div className="rounded-md border border-[var(--border-primary)] px-3 py-3">
                  <p className="text-xs text-[var(--text-muted)]">Plan ({variance.days}d)</p>
                  <p className="text-lg font-semibold tabular-nums">
                    {formatUsd(variance.plan_period_usd)}
                  </p>
                </div>
                <div className="rounded-md border border-[var(--border-primary)] px-3 py-3">
                  <p className="text-xs text-[var(--text-muted)]">Actual (list)</p>
                  <p className="text-lg font-semibold tabular-nums">
                    {formatUsd(variance.actual_list_cost_usd)}
                  </p>
                </div>
                <div className="rounded-md border border-[var(--border-primary)] px-3 py-3">
                  <p className="text-xs text-[var(--text-muted)]">Variance</p>
                  <p
                    className={`text-lg font-semibold tabular-nums ${
                      variance.variance_usd > 0
                        ? 'text-red-600 dark:text-red-400'
                        : variance.variance_usd < 0
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : ''
                    }`}
                  >
                    {formatUsd(variance.variance_usd)}
                    {variance.variance_pct != null
                      ? ` (${variance.variance_pct >= 0 ? '+' : ''}${variance.variance_pct.toFixed(1)}%)`
                      : ''}
                  </p>
                </div>
                <div className="rounded-md border border-[var(--border-primary)] px-3 py-3">
                  <p className="text-xs text-[var(--text-muted)]">Estimate</p>
                  <p className="text-sm font-medium truncate" title={variance.estimate_name}>
                    {variance.estimate_name}
                  </p>
                  <p className="text-xs text-[var(--text-muted)] mt-1">
                    {variance.line_items_with_plan ?? 0}/{variance.line_item_count ?? 0} line items
                    with plan
                  </p>
                </div>
              </div>
            )}
            {variance?.message && (
              <p className="text-xs text-[var(--text-muted)]">{variance.message}</p>
            )}
          </section>
        </>
      )}
    </div>
  )
}
