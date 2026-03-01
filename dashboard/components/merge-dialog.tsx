'use client'

import { useState } from 'react'
import type { ClusterResponse, MergeResponse } from '@/lib/types'

interface MergeDialogProps {
  sourceCluster: ClusterResponse
  availableClusters: ClusterResponse[]
  projectId: string
  onMerge: (sourceId: string, targetId: string) => Promise<MergeResponse>
  onClose: () => void
}

export function MergeDialog({
  sourceCluster,
  availableClusters,
  projectId,
  onMerge,
  onClose,
}: MergeDialogProps) {
  const [selectedTargetId, setSelectedTargetId] = useState<string | null>(null)
  const [isMerging, setIsMerging] = useState(false)
  const isValid = selectedTargetId !== null && !isMerging

  async function handleMerge() {
    if (!isValid || !selectedTargetId) return
    setIsMerging(true)
    try {
      await onMerge(sourceCluster.id, selectedTargetId)
      onClose()
    } finally {
      setIsMerging(false)
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="merge-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      data-testid="merge-dialog"
    >
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2
            id="merge-dialog-title"
            className="text-base font-semibold text-gray-900"
          >
            Merge Cluster
          </h2>
          <button
            onClick={onClose}
            aria-label="Close merge dialog"
            className="p-1 rounded hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-gray-400"
          >
            ✕
          </button>
        </div>
        <div className="px-6 py-4">
          <p className="text-sm text-gray-600 mb-4">
            Merge{' '}
            <span className="font-medium">&quot;{sourceCluster.name}&quot;</span>{' '}
            with:
          </p>
          <fieldset className="space-y-2">
            <legend className="sr-only">Select target cluster</legend>
            {availableClusters.map((cluster) => (
              <label
                key={cluster.id}
                className="flex items-center gap-3 p-2 rounded-lg border border-gray-200 cursor-pointer hover:bg-gray-50 has-[:checked]:border-blue-500 has-[:checked]:bg-blue-50"
              >
                <input
                  type="radio"
                  name="target-cluster"
                  value={cluster.id}
                  checked={selectedTargetId === cluster.id}
                  onChange={() => setSelectedTargetId(cluster.id)}
                  className="accent-blue-600"
                  data-testid={`merge-target-${cluster.id}`}
                />
                <span className="text-sm text-gray-700">
                  {cluster.name}
                  <span className="ml-2 text-xs text-gray-400">
                    ({cluster.fact_count} Facts)
                  </span>
                </span>
              </label>
            ))}
          </fieldset>
          <div
            className="mt-4 flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800"
            role="note"
          >
            <span aria-hidden="true">⚠</span>
            <span>
              All facts from &quot;{sourceCluster.name}&quot; will be moved to the
              selected cluster. You can undo this within 30 seconds.
            </span>
          </div>
        </div>
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200">
          <button
            onClick={onClose}
            disabled={isMerging}
            className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-gray-400"
          >
            Cancel
          </button>
          <button
            onClick={handleMerge}
            disabled={!isValid}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg disabled:opacity-50 hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500"
            data-testid="merge-confirm-btn"
          >
            {isMerging ? 'Merging...' : 'Merge Clusters'}
          </button>
        </div>
      </div>
    </div>
  )
}
