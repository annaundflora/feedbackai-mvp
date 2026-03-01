'use client'

import type { ClusterResponse } from '@/lib/types'

interface BulkMoveBarProps {
  selectedCount: number
  availableClusters: ClusterResponse[]
  onMove: (targetClusterId: string | null) => Promise<void>
  isMoving?: boolean
}

export function BulkMoveBar({
  selectedCount,
  availableClusters,
  onMove,
  isMoving = false,
}: BulkMoveBarProps) {
  if (selectedCount === 0) return null

  return (
    <div
      className="flex items-center gap-3 px-4 py-2 bg-blue-50 border border-blue-200 rounded-lg text-sm"
      data-testid="bulk-move-bar"
    >
      <span className="text-blue-700 font-medium">{selectedCount} selected</span>
      <label htmlFor="bulk-move-target" className="sr-only">
        Move selected facts to cluster
      </label>
      <select
        id="bulk-move-target"
        onChange={(e) =>
          onMove(e.target.value === 'unassigned' ? null : e.target.value)
        }
        disabled={isMoving}
        defaultValue=""
        className="text-sm border border-blue-300 rounded-lg px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        data-testid="bulk-move-select"
      >
        <option value="" disabled>
          Move selected to cluster...
        </option>
        <option value="unassigned">Mark as unassigned</option>
        {availableClusters.map((cluster) => (
          <option key={cluster.id} value={cluster.id}>
            {cluster.name}
          </option>
        ))}
      </select>
      {isMoving && (
        <span className="text-blue-500 text-xs">Moving...</span>
      )}
    </div>
  )
}
