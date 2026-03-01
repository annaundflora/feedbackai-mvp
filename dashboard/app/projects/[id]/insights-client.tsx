'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
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
import { clientApi } from '@/lib/client-api'
import type {
  ClusterResponse,
  MergeResponse,
  ProjectResponse,
  SuggestionResponse,
} from '@/lib/types'
import Link from 'next/link'

interface ProjectInsightsClientProps {
  projectId: string
  initialProject: ProjectResponse
  initialClusters: ClusterResponse[]
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
}: ProjectInsightsClientProps) {
  const router = useRouter()
  const [clusters, setClusters] = useState<ClusterResponse[]>(initialClusters)
  const [project] = useState<ProjectResponse>(initialProject)
  const [editing, setEditing] = useState<EditingState>({ type: 'none' })
  const [isRenaming, setIsRenaming] = useState(false)
  const [undoState, setUndoState] = useState<UndoState | null>(null)
  const [suggestions, setSuggestions] = useState<SuggestionResponse[]>([])
  const [showRecalculate, setShowRecalculate] = useState(false)

  // Load suggestions on mount
  useEffect(() => {
    clientApi.getSuggestions(projectId).then(setSuggestions).catch(() => {})
  }, [projectId])

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
        factCount={project.fact_count}
        clusterCount={project.cluster_count}
      />

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
                      ● {cluster.fact_count} Facts
                    </span>
                    <span className="text-sm text-gray-600">
                      ● {cluster.interview_count} Interviews
                    </span>
                  </div>
                </article>
              ) : (
                <article className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 hover:shadow-md transition-shadow duration-200">
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
                      ● {cluster.fact_count} Facts
                    </span>
                    <span
                      data-testid="cluster-interview-count"
                      className="text-sm text-gray-600"
                    >
                      ● {cluster.interview_count} Interviews
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
