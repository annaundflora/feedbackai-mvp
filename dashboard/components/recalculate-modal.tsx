'use client'

import { useState } from 'react'
import type { ProjectResponse } from '@/lib/types'

interface RecalculateModalProps {
  project: ProjectResponse
  onConfirm: () => Promise<void>
  onClose: () => void
}

export function RecalculateModal({
  project,
  onConfirm,
  onClose,
}: RecalculateModalProps) {
  const [isRecalculating, setIsRecalculating] = useState(false)

  async function handleConfirm() {
    setIsRecalculating(true)
    try {
      await onConfirm()
      onClose()
    } finally {
      setIsRecalculating(false)
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="recalculate-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      data-testid="recalculate-modal"
    >
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2
            id="recalculate-modal-title"
            className="text-base font-semibold text-gray-900"
          >
            Recalculate Clusters
          </h2>
          <button
            onClick={onClose}
            disabled={isRecalculating}
            aria-label="Close recalculate modal"
            className="p-1 rounded hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-gray-400 disabled:opacity-50"
          >
            ✕
          </button>
        </div>
        <div className="px-6 py-4">
          <div className="flex items-start gap-3 mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <span aria-hidden="true" className="text-red-500 flex-shrink-0">
              ⚠
            </span>
            <p className="text-sm text-red-800 font-medium">Warning</p>
          </div>
          <p className="text-sm text-gray-600 mb-3">
            All existing cluster assignments will be reset. Facts will be
            preserved, but a completely new cluster structure will be generated
            from scratch.
          </p>
          <ul className="space-y-1 text-sm text-gray-600">
            <li>• {project.cluster_count} Clusters (will be deleted)</li>
            <li>• {project.fact_count} Fact assignments (will be reset)</li>
            <li>• All cluster summaries (regenerated)</li>
          </ul>
        </div>
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200">
          <button
            onClick={onClose}
            disabled={isRecalculating}
            className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-gray-400 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={isRecalculating}
            className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg disabled:opacity-50 hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-500"
            data-testid="recalculate-confirm-btn"
          >
            {isRecalculating ? 'Recalculating...' : 'Recalculate All'}
          </button>
        </div>
      </div>
    </div>
  )
}
