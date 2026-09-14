import { Fragment, useMemo, useState } from 'react'
import { Menu, Transition } from '@headlessui/react'
import { TagIcon, ClipboardDocumentIcon, ChevronDownIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import {
  buildEstimateTagPack,
  formatTagsJson,
  formatTagsKeyValue,
  type FinOpsLineItemTagSource,
} from '../lib/finopsTags'

async function copyText(label: string, text: string) {
  try {
    await navigator.clipboard.writeText(text)
    toast.success(`${label} copied`)
  } catch {
    toast.error('Could not copy to clipboard')
  }
}

export default function FinOpsTagsButton({
  estimateId,
  lineItems,
  className,
}: {
  estimateId: string
  lineItems: FinOpsLineItemTagSource[]
  className?: string
}) {
  const [openPack, setOpenPack] = useState(false)
  const pack = useMemo(
    () => buildEstimateTagPack(estimateId, lineItems),
    [estimateId, lineItems]
  )

  return (
    <>
      <Menu as="div" className={clsx('relative inline-block text-left', className)}>
        <Menu.Button
          className="btn btn-secondary"
          title="Copy FinOps attribution tags for jobs/clusters"
          disabled={!estimateId}
        >
          <TagIcon className="w-4 h-4" />
          <span className="hidden sm:inline">FinOps tags</span>
          <ChevronDownIcon className="w-3.5 h-3.5 opacity-70" />
        </Menu.Button>
        <Transition
          as={Fragment}
          enter="transition ease-out duration-100"
          enterFrom="transform opacity-0 scale-95"
          enterTo="transform opacity-100 scale-100"
          leave="transition ease-in duration-75"
          leaveFrom="transform opacity-100 scale-100"
          leaveTo="transform opacity-0 scale-95"
        >
          <Menu.Items className="absolute right-0 z-40 mt-1 w-72 origin-top-right rounded-md border border-[var(--border-primary)] bg-[var(--bg-primary)] shadow-lg focus:outline-none py-1">
            <div className="px-3 py-2 border-b border-[var(--border-primary)]">
              <p className="text-xs font-semibold text-[var(--text-primary)]">Attribution tags</p>
              <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
                Apply on jobs/clusters or serverless usage policies for Actuals variance.
              </p>
            </div>
            <Menu.Item>
              {({ active }) => (
                <button
                  type="button"
                  className={clsx(
                    'w-full flex items-center gap-2 px-3 py-2 text-sm text-left',
                    active ? 'bg-[var(--bg-secondary)]' : ''
                  )}
                  onClick={() =>
                    copyText('Estimate tag', formatTagsKeyValue(pack.estimate))
                  }
                >
                  <ClipboardDocumentIcon className="w-4 h-4 text-[var(--text-muted)]" />
                  Copy estimate id tag
                </button>
              )}
            </Menu.Item>
            <Menu.Item>
              {({ active }) => (
                <button
                  type="button"
                  className={clsx(
                    'w-full flex items-center gap-2 px-3 py-2 text-sm text-left',
                    active ? 'bg-[var(--bg-secondary)]' : ''
                  )}
                  onClick={() =>
                    copyText('Estimate tags (JSON)', formatTagsJson(pack.estimate))
                  }
                >
                  <ClipboardDocumentIcon className="w-4 h-4 text-[var(--text-muted)]" />
                  Copy estimate tags (JSON)
                </button>
              )}
            </Menu.Item>
            <Menu.Item>
              {({ active }) => (
                <button
                  type="button"
                  className={clsx(
                    'w-full flex items-center gap-2 px-3 py-2 text-sm text-left',
                    active ? 'bg-[var(--bg-secondary)]' : '',
                    pack.line_items.length === 0 && 'opacity-50'
                  )}
                  disabled={pack.line_items.length === 0}
                  onClick={() => {
                    const body = pack.line_items
                      .map(
                        (li) =>
                          `# ${li.workload_name || li.line_item_id}\n${formatTagsKeyValue(li.tags)}`
                      )
                      .join('\n\n')
                    copyText('Line-item tags', body)
                  }}
                >
                  <ClipboardDocumentIcon className="w-4 h-4 text-[var(--text-muted)]" />
                  Copy all line-item tags
                </button>
              )}
            </Menu.Item>
            <Menu.Item>
              {({ active }) => (
                <button
                  type="button"
                  className={clsx(
                    'w-full flex items-center gap-2 px-3 py-2 text-sm text-left',
                    active ? 'bg-[var(--bg-secondary)]' : ''
                  )}
                  onClick={() => setOpenPack(true)}
                >
                  <TagIcon className="w-4 h-4 text-[var(--text-muted)]" />
                  View tag pack…
                </button>
              )}
            </Menu.Item>
          </Menu.Items>
        </Transition>
      </Menu>

      {openPack && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40"
          role="dialog"
          aria-modal="true"
          aria-labelledby="finops-tag-pack-title"
          onClick={() => setOpenPack(false)}
        >
          <div
            className="w-full max-w-lg max-h-[80vh] overflow-auto rounded-lg border border-[var(--border-primary)] bg-[var(--bg-primary)] p-4 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3 mb-3">
              <div>
                <h2
                  id="finops-tag-pack-title"
                  className="text-sm font-semibold text-[var(--text-primary)]"
                >
                  FinOps tag pack
                </h2>
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  Keys: lakemeter_estimate_id (required), lakemeter_workload_type,
                  lakemeter_line_item_id
                </p>
              </div>
              <button
                type="button"
                className="text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                onClick={() => setOpenPack(false)}
              >
                Close
              </button>
            </div>
            <pre className="text-xs font-mono whitespace-pre-wrap rounded-md bg-[var(--bg-secondary)] p-3 text-[var(--text-secondary)]">
              {JSON.stringify(pack, null, 2)}
            </pre>
            <p className="mt-2 text-[11px] text-[var(--text-muted)]">
              After tagging workloads, run lakemeter_finops_gold and compare on Actuals → variance.
            </p>
            <button
              type="button"
              className="mt-3 btn btn-secondary text-sm"
              onClick={() => copyText('Tag pack', JSON.stringify(pack, null, 2))}
            >
              Copy full pack (JSON)
            </button>
          </div>
        </div>
      )}
    </>
  )
}
