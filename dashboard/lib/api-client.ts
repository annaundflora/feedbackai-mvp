import type {
  ProjectListItem,
  ProjectResponse,
  ClusterResponse,
  ClusterDetailResponse,
  CreateProjectRequest,
} from '@/lib/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
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
