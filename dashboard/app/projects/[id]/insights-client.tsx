'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { StatusBar } from '@/components/status-bar'
import { ProjectTabs } from '@/components/project-tabs'
import { EmptyState } from '@/components/empty-state'
import { ClusterContextMenu } from '@/components/cluster-context-menu'
import { InlineRename } from '@/components/inline-rename'
import { MergeDialog } from '@/components/merge-dialog'
import { SplitModal } from '@/components/split-modal'
import { UndoToast } from '@/components/undo-toast'
import { SuggestionBanner } from '@/components/suggestion-banner'
import { RecalculateModal } from '@/components/recalculate-modal'
import { ProgressIndicator } from '@/components/progress-indicator'
import { toast } from '@/components/toast'
import { useProjectEvents } from '@/hooks/useProjectEvents'
import { clientApi } from '@/lib/client-api'
import type {
  ClusterResponse,
  MergeResponse,
  ProjectResponse,
  SuggestionResponse,
} from '@/lib/types'
import type { ClusteringProgressData } from '@/hooks/useProjectEvents'

interface ProjectInsightsClientProps {
  projectId: string
  initialProject: ProjectResponse
  initialClusters: ClusterResponse[]
  token?: string
}

interface UndoState {
  undoId: string
  expiresAt: string
  message: string
}

type EditingState =
  | { type: 'none' }
  | { type: 'rename'; clusterId: string }
  | { type: 'merge'; sourceCluster: ClusterResponse }
  | { type: 'split'; cluster: ClusterResponse }

export function ProjectInsightsClient({
  projectId,
  initialProject,
  initialClusters,
  token = '',
}: ProjectInsightsClientProps) {
  const router = useRouter()
  const [clusters, setClusters] = useState<ClusterResponse[]>(initialClusters)
  const [project] = useState<ProjectResponse>(initialProject)
  const [editing, setEditing] = useState<EditingState>({ type: 'none' })
  const [isRenaming, setIsRenaming] = useState(false)
  const [undoState, setUndoState] = useState<UndoState | null>(null)
  const [suggestions, setSuggestions] = useState<SuggestionResponse[]>([])
  const [showRecalculate, setShowRecalculate] = useState(false)

  // SSE Live-Update State
  const [progress, setProgress] = useState<ClusteringProgressData | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [liveUpdateClusterIds, setLiveUpdateClusterIds] = useState<Set<string>>(new Set())
  const [factCount, setFactCount] = useState(initialProject.fact_count)
  const [clusterCount, setClusterCount] = useState(initialProject.cluster_count)

  // Load suggestions on mount
  useEffect(() => {
    clientApi.getSuggestions(projectId).then(setSuggestions).catch(() => {})
  }, [projectId])

  // SSE Event Handlers
  const handleFactExtracted = useCallback(
    (data: { interview_id: string; fact_count: number }) => {
      // Optimistic counter update -- exakte Counts kommen via router.refresh()
      setFactCount((prev) => prev + data.fact_count)
      // Trigger live_update_badge on all cluster cards (fact not yet assigned to cluster)
      setLiveUpdateClusterIds(new Set(['*']))
      setTimeout(() => setLiveUpdateClusterIds(new Set()), 3000)
    },
    [],
  )

  const handleClusteringStarted = useCallback(() => {
    setIsProcessing(true)
  }, [])

  const handleClusteringProgress = useCallback((data: ClusteringProgressData) => {
    setProgress(data)
  }, [])

  const handleClusteringCompleted = useCallback(
    (data: { cluster_count: number; fact_count: number }) => {
      setIsProcessing(false)
      setProgress(null)
      setClusterCount(data.cluster_count)
      setFactCount(data.fact_count)
      // Server-side refresh fuer exakte Daten (Next.js App Router)
      router.refresh()
    },
    [router],
  )

  const handleClusteringFailed = useCallback(
    (data: { error: string; unassigned_count: number }) => {
      setIsProcessing(false)
      setProgress(null)
      toast.error(
        `Clustering failed: ${data.unassigned_count} facts could not be assigned. Check the Insights tab.`,
      )
    },
    [],
  )

  const handleSummaryUpdated = useCallback(() => {
    router.refresh()
  }, [router])

  // SSE Hook: verbindet mit Backend SSE-Endpoint
  // token wird in Slice 8 aus dem Auth-System befuellt
  useProjectEvents(projectId, token, {
    onFactExtracted: handleFactExtracted,
    onClusteringStarted: handleClusteringStarted,
    onClusteringProgress: handleClusteringProgress,
    onClusteringCompleted: handleClusteringCompleted,
    onClusteringFailed: handleClusteringFailed,
    onSummaryUpdated: handleSummaryUpdated,
  })

  // '*' wildcard = pulse all cards (fact not yet assigned to a specific cluster)
  const anyLiveUpdate = liveUpdateClusterIds.has('*')

  const handleRenameStart = useCallback((clusterId: string) => {
    setEditing({ type: 'rename', clusterId })
  }, [])

  const handleRenameSave = useCallback(
    async (name: string) => {
      if (editing.type !== 'rename') return
      setIsRenaming(true)
      try {
        const updated = await clientApi.renameCluster(projectId, editing.clusterId, name)
        setClusters((prev) =>
          prev.map((c) => (c.id === editing.clusterId ? updated : c))
        )
        setEditing({ type: 'none' })
      } finally {
        setIsRenaming(false)
      }
    },
    [editing, projectId]
  )

  const handleMerge = useCallback(
    async (sourceId: string, targetId: string): Promise<MergeResponse> => {
      const response = await clientApi.mergeClusters(projectId, sourceId, targetId)
      // Optimistic: remove source, update target
      setClusters((prev) =>
        prev
          .filter((c) => c.id !== sourceId)
          .map((c) => (c.id === targetId ? response.merged_cluster : c))
      )
      setUndoState({
        undoId: response.undo_id,
        expiresAt: response.undo_expires_at,
        message: 'Clusters merged.',
      })
      setEditing({ type: 'none' })
      return response
    },
    [projectId]
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
      setClusters((prev) => [
        ...prev.filter((c) => c.id !== clusterId),
        ...newClusters,
      ])
      setEditing({ type: 'none' })
      return newClusters
    },
    [projectId]
  )

  const handleAcceptSuggestion = useCallback(
    async (suggestionId: string) => {
      await clientApi.acceptSuggestion(projectId, suggestionId)
      setSuggestions((prev) => prev.filter((s) => s.id !== suggestionId))
    },
    [projectId]
  )

  const handleDismissSuggestion = useCallback(
    async (suggestionId: string) => {
      await clientApi.dismissSuggestion(projectId, suggestionId)
      setSuggestions((prev) => prev.filter((s) => s.id !== suggestionId))
    },
    [projectId]
  )

  const handleRecluster = useCallback(async () => {
    await clientApi.triggerRecluster(projectId)
    setShowRecalculate(false)
    router.refresh()
  }, [projectId, router])

  const otherClusters = (sourceClusterId: string) =>
    clusters.filter((c) => c.id !== sourceClusterId)

  return (
    <>
      <header className="mb-6">
        <h2
          data-testid="project-title"
          className="text-2xl font-bold text-gray-900"
        >
          {project.name}
        </h2>
        <p data-testid="project-research-goal" className="text-gray-600 mt-1">
          {project.research_goal}
        </p>
      </header>

      <ProjectTabs projectId={projectId} activeTab="insights" />

      <StatusBar
        interviewCount={project.interview_count}
        factCount={factCount}
        clusterCount={clusterCount}
      />

      {/* Progress Indicator -- nur sichtbar waehrend Clustering */}
      {isProcessing && progress && (
        <ProgressIndicator
          step={progress.step}
          completed={progress.completed}
          total={progress.total}
        />
      )}

      {/* Suggestion Banners */}
      {suggestions.length > 0 && (
        <div className="mt-4 space-y-2">
          {suggestions.map((suggestion) => (
            <SuggestionBanner
              key={suggestion.id}
              suggestion={suggestion}
              onAccept={handleAcceptSuggestion}
              onDismiss={handleDismissSuggestion}
            />
          ))}
        </div>
      )}

      {/* Recalculate Button */}
      <div className="mt-4 flex justify-end">
        <button
          onClick={() => setShowRecalculate(true)}
          className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-gray-400"
          data-testid="recalculate-btn"
        >
          Recalculate
        </button>
      </div>

      {clusters.length === 0 ? (
        <EmptyState
          data-testid="clusters-empty-state"
          message="No clusters yet."
          ctaLabel="Assign interviews to get started"
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6">
          {clusters.map((cluster) => (
            <div key={cluster.id} className="relative">
              {editing.type === 'rename' && editing.clusterId === cluster.id ? (
                <article className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                  <InlineRename
                    initialName={cluster.name}
                    onSave={handleRenameSave}
                    onCancel={() => setEditing({ type: 'none' })}
                    isLoading={isRenaming}
                  />
                  <div className="flex gap-4 mt-2">
                    <span className="text-sm text-gray-600">
                      {cluster.fact_count} Facts
                    </span>
                    <span className="text-sm text-gray-600">
                      {cluster.interview_count} Interviews
                    </span>
                  </div>
                </article>
              ) : (
                <article className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm p-5 hover:shadow-md transition-shadow duration-200 relative">
                  {/* live_update_badge -- pulsierender Dot fuer 3s */}
                  {(anyLiveUpdate || liveUpdateClusterIds.has(cluster.id)) && (
                    <span
                      aria-label="New fact added"
                      aria-live="polite"
                      data-testid="live-update-badge"
                      className="absolute top-3 right-10 w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse"
                    />
                  )}
                  <div className="flex items-start justify-between">
                    <Link
                      href={`/projects/${projectId}/clusters/${cluster.id}`}
                      className="flex-1 focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
                      aria-label={`View cluster: ${cluster.name}`}
                      data-testid="cluster-card"
                    >
                      <h3
                        data-testid="cluster-name"
                        className="text-base font-semibold text-gray-900"
                      >
                        {cluster.name}
                      </h3>
                    </Link>
                    <ClusterContextMenu
                      cluster={cluster}
                      projectId={projectId}
                      onRenameStart={() => handleRenameStart(cluster.id)}
                      onMergeStart={() =>
                        setEditing({ type: 'merge', sourceCluster: cluster })
                      }
                      onSplitStart={() =>
                        setEditing({ type: 'split', cluster })
                      }
                    />
                  </div>

                  <div className="flex gap-4 mt-2">
                    <span
                      data-testid="cluster-fact-count"
                      className="text-sm text-gray-600"
                    >
                      {cluster.fact_count} Facts
                    </span>
                    <span
                      data-testid="cluster-interview-count"
                      className="text-sm text-gray-600"
                    >
                      {cluster.interview_count} Interviews
                    </span>
                  </div>

                  {cluster.summary !== null ? (
                    <p className="text-sm text-gray-600 mt-2 line-clamp-3">
                      {cluster.summary}
                    </p>
                  ) : (
                    <p className="text-sm text-gray-400 mt-2 italic">
                      Generating summary...
                    </p>
                  )}
                </article>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Merge Dialog */}
      {editing.type === 'merge' && (
        <MergeDialog
          sourceCluster={editing.sourceCluster}
          availableClusters={otherClusters(editing.sourceCluster.id)}
          projectId={projectId}
          onMerge={handleMerge}
          onClose={() => setEditing({ type: 'none' })}
        />
      )}

      {/* Split Modal */}
      {editing.type === 'split' && (
        <SplitModal
          cluster={editing.cluster}
          projectId={projectId}
          onPreview={(clusterId) => clientApi.getSplitPreview(projectId, clusterId)}
          onConfirm={handleSplitConfirm}
          onClose={() => setEditing({ type: 'none' })}
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

      {/* Recalculate Modal */}
      {showRecalculate && (
        <RecalculateModal
          project={project}
          onConfirm={handleRecluster}
          onClose={() => setShowRecalculate(false)}
        />
      )}
    </>
  )
}
