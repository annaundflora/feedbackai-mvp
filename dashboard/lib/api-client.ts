import 'server-only'

import type {
  ProjectListItem,
  ProjectResponse,
  ClusterResponse,
  ClusterDetailResponse,
  CreateProjectRequest,
} from '@/lib/types'
import { getAuthToken } from '@/lib/auth'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await getAuthToken()

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (res.status === 401) {
    // Token expired — redirect to login (Server Component context)
    throw new Error('UNAUTHORIZED')
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({}))
    throw new Error((error as { detail?: string }).detail ?? `API error ${res.status}`)
  }

  return res.json() as Promise<T>
}

export const apiClient = {
  getProjects(): Promise<ProjectListItem[]> {
    return apiFetch<ProjectListItem[]>('/api/projects')
  },

  getProject(id: string): Promise<ProjectResponse> {
    return apiFetch<ProjectResponse>(`/api/projects/${id}`)
  },

  getClusters(id: string): Promise<ClusterResponse[]> {
    return apiFetch<ClusterResponse[]>(`/api/projects/${id}/clusters`)
  },

  createProject(data: CreateProjectRequest): Promise<ProjectResponse> {
    return apiFetch<ProjectResponse>('/api/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  getClusterDetail(projectId: string, clusterId: string): Promise<ClusterDetailResponse> {
    return apiFetch<ClusterDetailResponse>(`/api/projects/${projectId}/clusters/${clusterId}`)
  },
}
