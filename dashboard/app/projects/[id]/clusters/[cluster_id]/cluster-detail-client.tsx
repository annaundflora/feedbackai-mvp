'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { InlineRename } from '@/components/inline-rename'
import { MergeDialog } from '@/components/merge-dialog'
import { SplitModal } from '@/components/split-modal'
import { UndoToast } from '@/components/undo-toast'
import { BulkMoveBar } from '@/components/bulk-move-bar'
import { FactContextMenu } from '@/components/fact-context-menu'
import { QuoteItem } from '@/components/quote-item'
import { clientApi } from '@/lib/client-api'
import type {
  ClusterDetailResponse,
  ClusterResponse,
  FactResponse,
  MergeResponse,
} from '@/lib/types'

interface ClusterDetailClientProps {
  projectId: string
  initialCluster: ClusterDetailResponse
  otherClusters: ClusterResponse[]
}

interface UndoState {
  undoId: string
  expiresAt: string
  message: string
}

export function ClusterDetailClient({
  projectId,
  initialCluster,
  otherClusters,
}: ClusterDetailClientProps) {
  const router = useRouter()
  const [cluster, setCluster] = useState<ClusterDetailResponse>(initialCluster)
  const [isEditingName, setIsEditingName] = useState(false)
  const [isRenaming, setIsRenaming] = useState(false)
  const [showMerge, setShowMerge] = useState(false)
  const [showSplit, setShowSplit] = useState(false)
  const [undoState, setUndoState] = useState<UndoState | null>(null)
  const [selectedFactIds, setSelectedFactIds] = useState<Set<string>>(new Set())
  const [isBulkMoving, setIsBulkMoving] = useState(false)

  const handleRenameSave = useCallback(
    async (name: string) => {
      setIsRenaming(true)
      try {
        const updated = await clientApi.renameCluster(projectId, cluster.id, name)
        setCluster((prev) => ({ ...prev, name: updated.name }))
        setIsEditingName(false)
      } finally {
        setIsRenaming(false)
      }
    },
    [projectId, cluster.id]
  )

  const handleMerge = useCallback(
    async (sourceId: string, targetId: string): Promise<MergeResponse> => {
      const response = await clientApi.mergeClusters(projectId, sourceId, targetId)
      setUndoState({
        undoId: response.undo_id,
        expiresAt: response.undo_expires_at,
        message: 'Clusters merged.',
      })
      setShowMerge(false)
      // After merge this cluster is gone -> redirect to project
      router.push(`/projects/${projectId}`)
      return response
    },
    [projectId, router]
  )

  const handleUndo = useCallback(async () => {
    if (!undoState) return
    await clientApi.undoMerge(projectId, undoState.undoId)
    setUndoState(null)
    router.refresh()
  }, [projectId, undoState, router])

  const handleSplitConfirm = useCallback(
    async (
      clusterId: string,
      subclusters: Array<{ name: string; fact_ids: string[] }>
    ) => {
      const newClusters = await clientApi.executeSplit(
        projectId,
        clusterId,
        subclusters
      )
      setShowSplit(false)
      // After split, redirect to project page (original cluster gone)
      router.push(`/projects/${projectId}`)
      return newClusters
    },
    [projectId, router]
  )

  const handleFactMove = useCallback(
    async (factId: string, newClusterId: string | null) => {
      await clientApi.moveFact(projectId, factId, newClusterId)
      // Remove fact from local state (it moved away)
      setCluster((prev) => ({
        ...prev,
        facts: prev.facts.filter((f) => f.id !== factId),
        fact_count: prev.fact_count - 1,
      }))
      setSelectedFactIds((prev) => {
        const next = new Set(prev)
        next.delete(factId)
        return next
      })
    },
    [projectId]
  )

  const handleMarkUnassigned = useCallback(
    async (factId: string) => {
      await handleFactMove(factId, null)
    },
    [handleFactMove]
  )

  const handleBulkMove = useCallback(
    async (targetClusterId: string | null) => {
      const factIds = Array.from(selectedFactIds)
      if (factIds.length === 0) return
      setIsBulkMoving(true)
      try {
        await clientApi.bulkMoveFacts(projectId, factIds, targetClusterId)
        // Remove moved facts from local state
        setCluster((prev) => ({
          ...prev,
          facts: prev.facts.filter((f) => !selectedFactIds.has(f.id)),
          fact_count: prev.fact_count - factIds.length,
        }))
        setSelectedFactIds(new Set())
      } finally {
        setIsBulkMoving(false)
      }
    },
    [projectId, selectedFactIds]
  )

  const toggleFactSelection = useCallback((factId: string) => {
    setSelectedFactIds((prev) => {
      const next = new Set(prev)
      if (next.has(factId)) {
        next.delete(factId)
      } else {
        next.add(factId)
      }
      return next
    })
  }, [])

  // Current cluster as ClusterResponse shape for dialogs
  const clusterAsResponse: ClusterResponse = {
    id: cluster.id,
    name: cluster.name,
    summary: cluster.summary,
    fact_count: cluster.fact_count,
    interview_count: cluster.interview_count,
    created_at: '',
    updated_at: '',
  }

  // Available clusters for fact moves (other clusters in project)
  const availableClustersForFacts = otherClusters.map((c) => ({
    id: c.id,
    name: c.name,
  }))

  return (
    <>
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div className="flex-1 mr-4">
          {isEditingName ? (
            <InlineRename
              initialName={cluster.name}
              onSave={handleRenameSave}
              onCancel={() => setIsEditingName(false)}
              isLoading={isRenaming}
            />
          ) : (
            <div className="flex items-center gap-2">
              <h1
                data-testid="cluster-detail-name"
                className="text-xl font-bold text-gray-900"
              >
                {cluster.name}
              </h1>
              <button
                type="button"
                onClick={() => setIsEditingName(true)}
                aria-label="Rename cluster"
                className="p-1 text-gray-400 hover:text-gray-600 focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
                data-testid="rename-cluster-btn"
              >
                ✎
              </button>
            </div>
          )}
        </div>
        <div className="flex gap-2 shrink-0">
          <button
            type="button"
            data-testid="merge-btn"
            onClick={() => setShowMerge(true)}
            aria-label="Merge cluster"
            className="inline-flex items-center gap-1 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            Merge ▼
          </button>
          <button
            type="button"
            data-testid="split-btn"
            onClick={() => setShowSplit(true)}
            aria-label="Split cluster"
            className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            Split
          </button>
        </div>
      </div>

      {/* Summary */}
      {cluster.summary !== null ? (
        <section aria-label="Cluster summary" className="mb-8">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
            Summary
          </h2>
          <p
            data-testid="cluster-summary"
            className="text-sm text-gray-700 leading-relaxed"
          >
            {cluster.summary}
          </p>
        </section>
      ) : null}

      <hr className="border-gray-200 mb-8" />

      {/* Facts Section */}
      <section data-testid="facts-section" aria-label="Facts" className="mb-8">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
          Facts{' '}
          <span data-testid="facts-count" className="font-normal text-gray-500">
            ({cluster.facts.length})
          </span>
        </h2>

        {/* Bulk Move Bar */}
        <div className="mb-4">
          <BulkMoveBar
            selectedCount={selectedFactIds.size}
            availableClusters={otherClusters}
            onMove={handleBulkMove}
            isMoving={isBulkMoving}
          />
        </div>

        {cluster.facts.length === 0 ? (
          <p
            data-testid="facts-empty-state"
            className="text-sm text-gray-500 italic"
          >
            No facts extracted yet.
          </p>
        ) : (
          <ol className="space-y-3">
            {cluster.facts.map((fact, index) => (
              <FactItemWithControls
                key={fact.id}
                fact={fact}
                index={index}
                isSelected={selectedFactIds.has(fact.id)}
                onToggle={toggleFactSelection}
                onMove={handleFactMove}
                onMarkUnassigned={handleMarkUnassigned}
                availableClusters={availableClustersForFacts}
              />
            ))}
          </ol>
        )}
      </section>

      {/* Quotes Section */}
      {cluster.quotes.length > 0 ? (
        <>
          <hr className="border-gray-200 mb-8" />
          <section data-testid="quotes-section" aria-label="Supporting quotes">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
              Quotes
            </h2>
            <ul className="space-y-3">
              {cluster.quotes.map((quote) => (
                <QuoteItem key={quote.fact_id} quote={quote} />
              ))}
            </ul>
          </section>
        </>
      ) : null}

      {/* Merge Dialog */}
      {showMerge && (
        <MergeDialog
          sourceCluster={clusterAsResponse}
          availableClusters={otherClusters}
          projectId={projectId}
          onMerge={handleMerge}
          onClose={() => setShowMerge(false)}
        />
      )}

      {/* Split Modal */}
      {showSplit && (
        <SplitModal
          cluster={clusterAsResponse}
          projectId={projectId}
          onPreview={(clusterId) => clientApi.getSplitPreview(projectId, clusterId)}
          onConfirm={handleSplitConfirm}
          onClose={() => setShowSplit(false)}
        />
      )}

      {/* Undo Toast */}
      {undoState !== null && (
        <UndoToast
          message={undoState.message}
          expiresAt={undoState.expiresAt}
          onUndo={handleUndo}
          onDismiss={() => setUndoState(null)}
        />
      )}
    </>
  )
}

// Individual fact item with checkbox + context menu
interface FactItemWithControlsProps {
  fact: FactResponse
  index: number
  isSelected: boolean
  onToggle: (factId: string) => void
  onMove: (factId: string, newClusterId: string | null) => Promise<void>
  onMarkUnassigned: (factId: string) => Promise<void>
  availableClusters: Array<{ id: string; name: string }>
}

function FactItemWithControls({
  fact,
  index,
  isSelected,
  onToggle,
  onMove,
  onMarkUnassigned,
  availableClusters,
}: FactItemWithControlsProps) {
  const number = index + 1

  return (
    <li
      data-testid="fact-item"
      className="bg-white rounded-lg border border-gray-200 p-4"
    >
      <div className="flex items-start gap-3">
        {/* Checkbox */}
        <input
          type="checkbox"
          checked={isSelected}
          onChange={() => onToggle(fact.id)}
          aria-label={`Select fact ${number}`}
          className="mt-0.5 h-4 w-4 rounded border-gray-300 accent-blue-600"
        />
        <span
          data-testid="fact-number"
          className="text-sm font-semibold text-gray-500 min-w-[1.5rem] shrink-0"
        >
          {number}.
        </span>
        <div className="flex-1">
          <p data-testid="fact-content" className="text-sm text-gray-900">
            {fact.content}
          </p>
          <div className="flex items-center flex-wrap gap-2 mt-2">
            <span
              data-testid="fact-interview-badge"
              aria-label={`Source: Interview #${number}`}
              className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200"
            >
              Interview #{number}
            </span>
            {fact.confidence !== null ? (
              <span
                data-testid="fact-confidence"
                className="text-xs text-gray-500"
              >
                Confidence: {fact.confidence}
              </span>
            ) : null}
          </div>
        </div>
        {/* Context Menu */}
        <FactContextMenu
          factId={fact.id}
          currentClusterId={fact.cluster_id}
          availableClusters={availableClusters}
          onMove={onMove}
          onMarkUnassigned={onMarkUnassigned}
        />
      </div>
    </li>
  )
}
