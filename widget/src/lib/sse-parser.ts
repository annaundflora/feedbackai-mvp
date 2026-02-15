import type { SSEEvent } from './types'
import { ApiError } from './types'

/**
 * Parse a single SSE data line into a typed SSEEvent.
 * Returns null for empty lines, comments, or malformed JSON.
 *
 * @param line - SSE line (e.g., "data: {...}")
 * @returns Parsed SSEEvent or null if invalid
 */
export function parseSSELine(line: string): SSEEvent | null {
  const trimmed = line.trim()
  if (!trimmed || trimmed.startsWith(':')) return null

  const dataPrefix = 'data: '
  if (!trimmed.startsWith(dataPrefix)) return null

  const jsonStr = trimmed.slice(dataPrefix.length)
  try {
    return JSON.parse(jsonStr) as SSEEvent
  } catch {
    // Skip malformed JSON - don't throw to allow stream to continue
    return null
  }
}

/**
 * Read a ReadableStream of SSE data and yield parsed SSEEvent objects.
 * Handles buffering for events split across chunks.
 *
 * @param body - ReadableStream from fetch Response.body
 * @yields Parsed SSEEvent objects
 */
export async function* readSSEStream(
  body: ReadableStream<Uint8Array>
): AsyncGenerator<SSEEvent> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // Split by double newline (SSE event boundary)
      const parts = buffer.split('\n\n')
      // Last part may be incomplete - keep in buffer
      buffer = parts.pop() ?? ''

      for (const part of parts) {
        // Each part may have multiple lines (event: ...\ndata: ...)
        // We only care about data: lines
        for (const line of part.split('\n')) {
          const event = parseSSELine(line)
          if (event) yield event
        }
      }
    }

    // Process remaining buffer (for events without final \n\n)
    if (buffer.trim()) {
      for (const line of buffer.split('\n')) {
        const event = parseSSELine(line)
        if (event) yield event
      }
    }
  } finally {
    // Critical: release reader lock to prevent memory leaks
    reader.releaseLock()
  }
}

/**
 * Validate response and return SSE stream reader.
 * Throws ApiError for non-ok responses or missing body.
 *
 * @param response - Fetch Response from API call
 * @yields Parsed SSEEvent objects
 * @throws ApiError if response is not ok or body is missing
 */
export async function* streamStart(response: Response): AsyncGenerator<SSEEvent> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new ApiError(error.error || 'Request failed', response.status, error.detail)
  }

  if (!response.body) {
    throw new ApiError('No response body', 0)
  }

  yield* readSSEStream(response.body)
}
