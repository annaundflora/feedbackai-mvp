import type {
  ProjectResponse,
  CreateProjectRequest,
} from '@/lib/types'

/**
 * Client-side API fetch that proxies through Next.js API routes.
 * The httpOnly auth_token cookie is forwarded automatically by the browser.
 */
async function clientApiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  const res = await fetch(path, { ...options, headers, credentials: 'same-origin' })

  if (res.status === 401) {
    window.location.href = '/login'
    throw new Error('UNAUTHORIZED')
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({}))
    throw new Error((error as { detail?: string }).detail ?? (error as { error?: string }).error ?? `API error ${res.status}`)
  }

  return res.json() as Promise<T>
}

export const browserApiClient = {
  createProject(data: CreateProjectRequest): Promise<ProjectResponse> {
    return clientApiFetch<ProjectResponse>('/api/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
}
