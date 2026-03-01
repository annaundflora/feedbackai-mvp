'use client'

import { useState } from 'react'
import type { ClusterResponse, SplitPreviewResponse } from '@/lib/types'

type Step = 'step1' | 'step1_generating' | 'step2' | 'splitting'

interface SplitModalProps {
  cluster: ClusterResponse
  projectId: string
  onPreview: (clusterId: string) => Promise<SplitPreviewResponse>
  onConfirm: (
    clusterId: string,
    subclusters: Array<{ name: string; fact_ids: string[] }>
  ) => Promise<ClusterResponse[]>
  onClose: () => void
}

export function SplitModal({
  cluster,
  projectId,
  onPreview,
  onConfirm,
  onClose,
}: SplitModalProps) {
  const [step, setStep] = useState<Step>('step1')
  const [preview, setPreview] = useState<SplitPreviewResponse | null>(null)

  async function handleGeneratePreview() {
    setStep('step1_generating')
    try {
      const result = await onPreview(cluster.id)
      setPreview(result)
      setStep('step2')
    } catch {
      setStep('step1')
    }
  }

  async function handleConfirm() {
    if (!preview) return
    setStep('splitting')
    try {
      await onConfirm(
        cluster.id,
        preview.subclusters.map((sc) => ({
          name: sc.name,
          fact_ids: sc.facts.map((f) => f.id),
        }))
      )
      onClose()
    } catch {
      setStep('step2')
    }
  }

  const isGenerating = step === 'step1_generating'
  const isSplitting = step === 'splitting'

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="split-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      data-testid="split-modal"
    >
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 sticky top-0 bg-white">
          <h2
            id="split-modal-title"
            className="text-base font-semibold text-gray-900"
          >
            {step === 'step2' ? 'Split Cluster — Preview' : 'Split Cluster'}
          </h2>
          <button
            onClick={onClose}
            disabled={isSplitting}
            aria-label="Close split modal"
            className="p-1 rounded hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-gray-400 disabled:opacity-50"
          >
            ✕
          </button>
        </div>

        {/* Step 1 */}
        {(step === 'step1' || step === 'step1_generating') && (
          <div className="px-6 py-4">
            <p className="text-sm text-gray-700 mb-2">
              Split{' '}
              <span className="font-medium">&quot;{cluster.name}&quot;</span>{' '}
              ({cluster.fact_count} Facts)?
            </p>
            <p className="text-sm text-gray-500">
              The LLM will analyze the facts and propose sub-clusters for your
              review.
            </p>
          </div>
        )}

        {/* Step 2 Preview */}
        {step === 'step2' && preview !== null && (
          <div className="px-6 py-4">
            <p className="text-sm text-gray-600 mb-4">
              Proposed split for{' '}
              <span className="font-medium">&quot;{cluster.name}&quot;</span>:
            </p>
            <div className="space-y-3">
              {preview.subclusters.map((sc, i) => (
                <div
                  key={i}
                  className="border border-gray-200 rounded-lg p-3"
                  data-testid={`split-preview-subcluster-${i}`}
                >
                  <p className="text-sm font-medium text-gray-900 mb-2">
                    {sc.name} ({sc.fact_count} Facts)
                  </p>
                  <ul className="space-y-1">
                    {sc.facts.map((fact) => (
                      <li
                        key={fact.id}
                        className="text-xs text-gray-600 flex gap-1.5"
                      >
                        <span aria-hidden="true" className="text-gray-400">
                          •
                        </span>
                        <span>{fact.content}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200 sticky bottom-0 bg-white">
          <button
            onClick={onClose}
            disabled={isSplitting}
            className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-gray-400 disabled:opacity-50"
          >
            Cancel
          </button>
          {(step === 'step1' || step === 'step1_generating') && (
            <button
              onClick={handleGeneratePreview}
              disabled={isGenerating}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg disabled:opacity-50 hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500"
              data-testid="generate-preview-btn"
            >
              {isGenerating ? 'Analyzing...' : 'Generate Preview'}
            </button>
          )}
          {step === 'step2' && (
            <button
              onClick={handleConfirm}
              disabled={isSplitting}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg disabled:opacity-50 hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500"
              data-testid="confirm-split-btn"
            >
              {isSplitting ? 'Splitting...' : 'Confirm Split'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
