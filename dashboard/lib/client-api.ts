'use client'

/**
 * Client-side API methods fuer Taxonomy-Editing (Slice 6).
 *
 * Alle Requests gehen gegen den Next.js API-Proxy (/api/proxy/...),
 * welcher die Anfragen an den Backend-Server weiterleitet.
 * Alternativ: Direkt gegen NEXT_PUBLIC_API_URL wenn kein Proxy vorhanden.
 *
 * HINWEIS: Identisch mit api-client.ts aber fuer Client-Komponenten gedacht.
 * Nutzt apiFetch aus api-client.ts.
 */

import type {
  ClusterResponse,
  FactResponse,
  MergeResponse,
  ReclusterStarted,
  SplitPreviewResponse,
  SplitSubclusterInput,
  SuggestionResponse,
} from '@/lib/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  })
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`)
  }
  // 200/201 with no body (e.g. suggestions dismiss/accept) -> return {} as T
  const contentType = res.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) {
    return {} as T
  }
  return res.json() as Promise<T>
}

export const clientApi = {
  renameCluster(
    projectId: string,
    clusterId: string,
    name: string
  ): Promise<ClusterResponse> {
    return apiFetch<ClusterResponse>(
      `/api/projects/${projectId}/clusters/${clusterId}`,
      {
        method: 'PUT',
        body: JSON.stringify({ name }),
      }
    )
  },

  mergeClusters(
    projectId: string,
    sourceId: string,
    targetId: string
  ): Promise<MergeResponse> {
    return apiFetch<MergeResponse>(
      `/api/projects/${projectId}/clusters/merge`,
      {
        method: 'POST',
        body: JSON.stringify({
          source_cluster_id: sourceId,
          target_cluster_id: targetId,
        }),
      }
    )
  },

  undoMerge(projectId: string, undoId: string): Promise<ClusterResponse> {
    return apiFetch<ClusterResponse>(
      `/api/projects/${projectId}/clusters/merge/undo`,
      {
        method: 'POST',
        body: JSON.stringify({ undo_id: undoId }),
      }
    )
  },

  getSplitPreview(
    projectId: string,
    clusterId: string
  ): Promise<SplitPreviewResponse> {
    return apiFetch<SplitPreviewResponse>(
      `/api/projects/${projectId}/clusters/${clusterId}/split/preview`,
      { method: 'POST' }
    )
  },

  executeSplit(
    projectId: string,
    clusterId: string,
    subclusters: SplitSubclusterInput[]
  ): Promise<ClusterResponse[]> {
    return apiFetch<ClusterResponse[]>(
      `/api/projects/${projectId}/clusters/${clusterId}/split`,
      {
        method: 'POST',
        body: JSON.stringify({ subclusters }),
      }
    )
  },

  moveFact(
    projectId: string,
    factId: string,
    clusterId: string | null
  ): Promise<FactResponse> {
    return apiFetch<FactResponse>(
      `/api/projects/${projectId}/facts/${factId}`,
      {
        method: 'PUT',
        body: JSON.stringify({ cluster_id: clusterId }),
      }
    )
  },

  bulkMoveFacts(
    projectId: string,
    factIds: string[],
    targetClusterId: string | null
  ): Promise<FactResponse[]> {
    return apiFetch<FactResponse[]>(
      `/api/projects/${projectId}/facts/bulk-move`,
      {
        method: 'POST',
        body: JSON.stringify({
          fact_ids: factIds,
          target_cluster_id: targetClusterId,
        }),
      }
    )
  },

  getSuggestions(projectId: string): Promise<SuggestionResponse[]> {
    return apiFetch<SuggestionResponse[]>(
      `/api/projects/${projectId}/suggestions`
    )
  },

  acceptSuggestion(projectId: string, suggestionId: string): Promise<void> {
    return apiFetch<void>(
      `/api/projects/${projectId}/suggestions/${suggestionId}/accept`,
      { method: 'POST' }
    )
  },

  dismissSuggestion(projectId: string, suggestionId: string): Promise<void> {
    return apiFetch<void>(
      `/api/projects/${projectId}/suggestions/${suggestionId}/dismiss`,
      { method: 'POST' }
    )
  },

  triggerRecluster(projectId: string): Promise<ReclusterStarted> {
    return apiFetch<ReclusterStarted>(
      `/api/projects/${projectId}/clustering/recluster`,
      { method: 'POST' }
    )
  },
}
