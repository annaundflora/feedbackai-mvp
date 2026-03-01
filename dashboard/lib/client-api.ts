'use client'

/**
 * Client-side API helpers and methods.
 *
 * clientFetch: Routes through Next.js proxy (/api/proxy/...) so the
 *   server-side Route Handler can read the HttpOnly auth_token cookie and
 *   forward the Authorization: Bearer header to FastAPI.
 *   Use in ALL Client Components ("use client") for authenticated API calls.
 *
 * clientApi: Taxonomy-Editing API methods (Slice 6), now using clientFetch.
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

// ─── clientFetch: Proxy-based fetch for Client Components ─────────────────────
// Client Components cannot read HttpOnly cookies directly.
// This function routes all requests through /api/proxy/[...path] which is a
// server-side Route Handler that reads the cookie and adds the auth header.

export async function clientFetch<T>(
  path: string, // e.g. "/api/projects/123"
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`/api/proxy${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    },
  })

  if (response.status === 401) {
    window.location.href = '/login'
    throw new Error('UNAUTHORIZED')
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error((error as { detail?: string }).detail ?? `API error ${response.status}`)
  }

  // 200/201 with no body (e.g. suggestions dismiss/accept) -> return {} as T
  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) {
    return {} as T
  }

  return response.json() as Promise<T>
}

// ─── Internal proxy-based fetch for clientApi methods ─────────────────────────
async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  return clientFetch<T>(path, options)
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
