import { useLocalRuntime } from '@assistant-ui/react'
import type { ChatModelAdapter } from '@assistant-ui/react'
import { useRef, useMemo } from 'react'
import { getOrCreateAnonymousId } from './anonymous-id'
import { createApiClient } from './api-client'
import { streamStart } from './sse-parser'

/**
 * Create ChatModelAdapter that connects to backend SSE endpoints.
 * Handles START flow (no session) and MESSAGE flow (existing session).
 *
 * @param apiUrl - Base URL for API endpoints
 * @param sessionIdRef - Mutable ref to store session_id from metadata event
 * @returns ChatModelAdapter compatible with @assistant-ui/react
 */
function createChatModelAdapter(
  apiUrl: string,
  sessionIdRef: React.MutableRefObject<string | null>
): ChatModelAdapter {
  const apiClient = createApiClient(apiUrl)

  return {
    async *run({ abortSignal }) {
      // If no session yet, this is a START flow
      if (!sessionIdRef.current) {
        const anonymousId = getOrCreateAnonymousId()
        const response = await apiClient.startInterview(anonymousId, { signal: abortSignal })

        let text = ''
        for await (const event of streamStart(response)) {
          if (event.type === 'metadata') {
            sessionIdRef.current = event.session_id
          } else if (event.type === 'text-delta') {
            text += event.content
            yield { content: [{ type: 'text' as const, text }] }
          } else if (event.type === 'error') {
            throw new Error(event.message)
          }
          // text-done: loop ends naturally
        }
        return
      }

      // MESSAGE flow handled by Slice 06
    }
  }
}

/**
 * Custom Hook for Widget Chat Runtime.
 *
 * Creates a local runtime with ChatModelAdapter that connects to backend.
 * In Slice 05: Handles START flow only.
 * In Slice 06: Will be extended with MESSAGE flow.
 *
 * @param apiUrl - Base URL for API endpoints (from config.apiUrl)
 * @returns Local runtime instance for @assistant-ui
 */
export function useWidgetChatRuntime(apiUrl: string | null) {
  const sessionIdRef = useRef<string | null>(null)

  const adapter = useMemo(() => {
    if (!apiUrl) {
      // Fallback: dummy adapter when no API URL configured
      return { async *run() { return } } as ChatModelAdapter
    }
    return createChatModelAdapter(apiUrl, sessionIdRef)
  }, [apiUrl])

  return useLocalRuntime(adapter)
}
