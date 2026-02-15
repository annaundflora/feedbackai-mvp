import type { EndResponse } from './types'
import { ApiError } from './types'

export interface ApiClient {
  startInterview(anonymousId: string, options?: { signal?: AbortSignal }): Promise<Response>
  sendMessage(sessionId: string, message: string, options?: { signal?: AbortSignal }): Promise<Response>
  endInterview(sessionId: string, options?: { signal?: AbortSignal }): Promise<EndResponse>
}

export function createApiClient(apiUrl: string | null): ApiClient {
  if (!apiUrl) {
    throw new Error('API URL not configured')
  }

  const baseUrl = apiUrl.replace(/\/+$/, '')

  async function post(endpoint: string, body: Record<string, unknown>, signal?: AbortSignal): Promise<Response> {
    const response = await fetch(`${baseUrl}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    })
    return response
  }

  return {
    startInterview(anonymousId, options) {
      return post('/api/interview/start', { anonymous_id: anonymousId }, options?.signal)
    },

    sendMessage(sessionId, message, options) {
      return post('/api/interview/message', { session_id: sessionId, message }, options?.signal)
    },

    async endInterview(sessionId, options) {
      const response = await post('/api/interview/end', { session_id: sessionId }, options?.signal)
      if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Unknown error' }))
        throw new ApiError(error.error || 'Request failed', response.status, error.detail)
      }
      return response.json() as Promise<EndResponse>
    },
  }
}
