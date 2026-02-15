import { useLocalRuntime } from '@assistant-ui/react'
import type { ChatModelAdapter } from '@assistant-ui/react'
import { useRef, useMemo } from 'react'
import { getOrCreateAnonymousId } from './anonymous-id'
import { createApiClient } from './api-client'
import { streamStart, streamMessage } from './sse-parser'

/**
 * Interview control functions exposed to Widget component.
 * Allows main.tsx to manage interview lifecycle (end, check active state).
 */
export interface InterviewControls {
  endInterview: () => Promise<void>
  hasActiveSession: () => boolean
}

/**
 * Create ChatModelAdapter that connects to backend SSE endpoints.
 * Handles START flow (no session) and MESSAGE flow (existing session).
 *
 * @param apiUrl - Base URL for API endpoints
 * @param sessionIdRef - Mutable ref to store session_id from metadata event
 * @param abortControllerRef - Mutable ref to store AbortController for stream cleanup
 * @returns ChatModelAdapter compatible with @assistant-ui/react
 */
function createChatModelAdapter(
  apiUrl: string,
  sessionIdRef: React.MutableRefObject<string | null>,
  abortControllerRef: React.MutableRefObject<AbortController | null>
): ChatModelAdapter {
  const apiClient = createApiClient(apiUrl)

  return {
    async *run({ messages, abortSignal }) {
      // Store AbortController reference for cleanup
      if (abortSignal) {
        const controller = new AbortController()
        abortControllerRef.current = controller

        // Forward abort from @assistant-ui to our controller
        abortSignal.addEventListener('abort', () => {
          controller.abort()
        })
      }

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

        // Clear abort controller after successful completion
        abortControllerRef.current = null
        return
      }

      // MESSAGE flow: session exists, send last user message
      const lastUserMessage = [...messages].reverse().find(m => m.role === 'user')
      if (!lastUserMessage) {
        abortControllerRef.current = null
        return
      }

      const messageText = lastUserMessage.content
        .filter((c): c is { type: 'text'; text: string } => c.type === 'text')
        .map(c => c.text)
        .join('')

      const response = await apiClient.sendMessage(
        sessionIdRef.current,
        messageText,
        { signal: abortSignal }
      )

      let text = ''
      for await (const event of streamMessage(response)) {
        if (event.type === 'text-delta') {
          text += event.content
          yield { content: [{ type: 'text' as const, text }] }
        } else if (event.type === 'error') {
          throw new Error(event.message)
        }
        // text-done: loop ends naturally
      }

      // Clear abort controller after successful completion
      abortControllerRef.current = null
    }
  }
}

/**
 * Custom Hook for Widget Chat Runtime.
 *
 * Creates a local runtime with ChatModelAdapter that connects to backend.
 * Handles both START flow (no session) and MESSAGE flow (existing session).
 * Returns both runtime and interview controls for lifecycle management.
 *
 * @param apiUrl - Base URL for API endpoints (from config.apiUrl)
 * @returns Object with runtime and controls
 */
export function useWidgetChatRuntime(apiUrl: string | null): {
  runtime: ReturnType<typeof useLocalRuntime>
  controls: InterviewControls
} {
  const sessionIdRef = useRef<string | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const apiClient = useMemo(() => {
    if (!apiUrl) return null
    return createApiClient(apiUrl)
  }, [apiUrl])

  const controls: InterviewControls = useMemo(() => ({
    async endInterview() {
      // Abort running stream
      abortControllerRef.current?.abort()
      abortControllerRef.current = null

      // Call /end (fire-and-forget)
      const sessionId = sessionIdRef.current
      if (sessionId && apiClient) {
        sessionIdRef.current = null
        await apiClient.endInterviewSafe(sessionId)
      }
    },
    hasActiveSession() {
      return sessionIdRef.current !== null
    }
  }), [apiClient])

  const adapter = useMemo(() => {
    if (!apiUrl) {
      // Fallback: dummy adapter when no API URL configured
      return { async *run() { return } } as ChatModelAdapter
    }
    return createChatModelAdapter(apiUrl, sessionIdRef, abortControllerRef)
  }, [apiUrl])

  const runtime = useLocalRuntime(adapter)

  return { runtime, controls }
}
