/**
 * Helper function to create mock SSE Response for tests.
 * Creates a ReadableStream that emits SSE-formatted events.
 *
 * SSE format: "data: {json}\n\n"
 */
import type { SSEEvent } from '../../../../src/lib/types'

export function createMockSSEResponse(events: SSEEvent[], status = 200): Response {
  const encoder = new TextEncoder()
  const chunks = events.map(e => `data: ${JSON.stringify(e)}\n\n`)

  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk))
      }
      controller.close()
    }
  })

  return new Response(stream, {
    status,
    headers: { 'Content-Type': 'text/event-stream' }
  })
}

/**
 * Helper to create a slow streaming response (for testing abort scenarios).
 */
export function createSlowMockSSEResponse(
  events: SSEEvent[],
  delayMs = 100,
  status = 200
): Response {
  const encoder = new TextEncoder()
  const chunks = events.map(e => `data: ${JSON.stringify(e)}\n\n`)

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk))
        // Simulate network delay
        await new Promise(resolve => setTimeout(resolve, delayMs))
      }
      controller.close()
    }
  })

  return new Response(stream, {
    status,
    headers: { 'Content-Type': 'text/event-stream' }
  })
}

/**
 * Helper to create a JSON error response (for 404, 409, etc.).
 */
export function createMockErrorResponse(
  error: string,
  detail: string,
  status: number
): Response {
  return new Response(
    JSON.stringify({ error, detail }),
    {
      status,
      headers: { 'Content-Type': 'application/json' }
    }
  )
}
