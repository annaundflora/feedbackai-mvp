/**
 * Acceptance + Unit Tests for Slice 03: SSE-Client for /message Endpoint.
 * Derived from GIVEN/WHEN/THEN Acceptance Criteria in the Slice-Spec.
 *
 * Slice-Spec: specs/phase-3/2026-02-15-backend-widget-integration/slices/slice-03-sse-client-message.md
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { streamMessage } from '../../../src/lib/sse-parser'
import { ApiError } from '../../../src/lib/types'

// ---------------------------------------------------------------------------
// Helper: create a ReadableStream from SSE-formatted string chunks
// ---------------------------------------------------------------------------
function createSSEStream(...chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk))
      }
      controller.close()
    },
  })
}

// Helper: collect all events from an async generator
async function collectEvents<T>(gen: AsyncGenerator<T>): Promise<T[]> {
  const events: T[] = []
  for await (const event of gen) {
    events.push(event)
  }
  return events
}

// ---------------------------------------------------------------------------
// streamMessage - Acceptance Tests
// ---------------------------------------------------------------------------

describe('streamMessage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  describe('acceptance', () => {
    it('AC-1: GIVEN a successful Response from /message WHEN streamMessage(response) is called THEN it yields text-delta events followed by text-done event (no metadata event)', async () => {
      // Arrange (GIVEN): mock Response with SSE body containing text-delta + text-done (no metadata)
      const sseData = [
        'data: {"type":"text-delta","content":"Wie"}\n\n',
        'data: {"type":"text-delta","content":" geht"}\n\n',
        'data: {"type":"text-delta","content":" es?"}\n\n',
        'data: {"type":"text-done"}\n\n',
      ].join('')
      const mockResponse = {
        ok: true,
        body: createSSEStream(sseData),
      } as unknown as Response

      // Act (WHEN)
      const events = await collectEvents(streamMessage(mockResponse))

      // Assert (THEN)
      expect(events).toEqual([
        { type: 'text-delta', content: 'Wie' },
        { type: 'text-delta', content: ' geht' },
        { type: 'text-delta', content: ' es?' },
        { type: 'text-done' },
      ])
      // Verify: no metadata event present (unlike /start)
      expect(events.every((e) => e.type !== 'metadata')).toBe(true)
      // Verify: last event is text-done
      expect(events[events.length - 1]).toHaveProperty('type', 'text-done')
    })

    it('AC-2: GIVEN a Response with status 404 WHEN streamMessage(response) is called THEN it throws ApiError with status 404 and message "Session not found"', async () => {
      // Arrange (GIVEN): mock Response with status 404
      const mockResponse = {
        ok: false,
        status: 404,
        json: vi.fn().mockResolvedValue({ error: 'Session not found' }),
      } as unknown as Response

      // Act & Assert (WHEN/THEN)
      const generator = streamMessage(mockResponse)
      await expect(generator.next()).rejects.toThrow(ApiError)

      // Verify status and message
      const mockResponse2 = {
        ok: false,
        status: 404,
        json: vi.fn().mockResolvedValue({ error: 'Session not found' }),
      } as unknown as Response
      try {
        const gen2 = streamMessage(mockResponse2)
        await gen2.next()
        expect.unreachable('Should have thrown')
      } catch (e) {
        expect(e).toBeInstanceOf(ApiError)
        expect((e as ApiError).status).toBe(404)
        expect((e as ApiError).message).toBe('Session not found')
      }
    })

    it('AC-3: GIVEN a Response with status 409 WHEN streamMessage(response) is called THEN it throws ApiError with status 409 and message "Session already completed"', async () => {
      // Arrange (GIVEN): mock Response with status 409
      const mockResponse = {
        ok: false,
        status: 409,
        json: vi.fn().mockResolvedValue({ error: 'Session already completed' }),
      } as unknown as Response

      // Act & Assert (WHEN/THEN)
      const generator = streamMessage(mockResponse)
      await expect(generator.next()).rejects.toThrow(ApiError)

      // Verify status and message
      const mockResponse2 = {
        ok: false,
        status: 409,
        json: vi.fn().mockResolvedValue({ error: 'Session already completed' }),
      } as unknown as Response
      try {
        const gen2 = streamMessage(mockResponse2)
        await gen2.next()
        expect.unreachable('Should have thrown')
      } catch (e) {
        expect(e).toBeInstanceOf(ApiError)
        expect((e as ApiError).status).toBe(409)
        expect((e as ApiError).message).toBe('Session already completed')
      }
    })

    it('AC-4: GIVEN a Response with status 500 WHEN streamMessage(response) is called THEN it throws ApiError with status 500', async () => {
      // Arrange (GIVEN): mock Response with status 500
      const mockResponse = {
        ok: false,
        status: 500,
        json: vi.fn().mockResolvedValue({ error: 'Internal Server Error' }),
      } as unknown as Response

      // Act & Assert (WHEN/THEN)
      const generator = streamMessage(mockResponse)
      await expect(generator.next()).rejects.toThrow(ApiError)

      // Verify status
      const mockResponse2 = {
        ok: false,
        status: 500,
        json: vi.fn().mockResolvedValue({ error: 'Internal Server Error' }),
      } as unknown as Response
      try {
        const gen2 = streamMessage(mockResponse2)
        await gen2.next()
        expect.unreachable('Should have thrown')
      } catch (e) {
        expect(e).toBeInstanceOf(ApiError)
        expect((e as ApiError).status).toBe(500)
      }
    })

    it('AC-5: GIVEN a Response with no body WHEN streamMessage(response) is called THEN it throws ApiError with message "No response body"', async () => {
      // Arrange (GIVEN): mock Response with ok status but body === null
      const mockResponse = {
        ok: true,
        body: null,
      } as unknown as Response

      // Act & Assert (WHEN/THEN)
      const generator = streamMessage(mockResponse)
      await expect(generator.next()).rejects.toThrow('No response body')

      // Verify it is an ApiError
      const mockResponse2 = {
        ok: true,
        body: null,
      } as unknown as Response
      try {
        const gen2 = streamMessage(mockResponse2)
        await gen2.next()
        expect.unreachable('Should have thrown')
      } catch (e) {
        expect(e).toBeInstanceOf(ApiError)
        expect((e as ApiError).message).toBe('No response body')
      }
    })
  })

  // ---------------------------------------------------------------------------
  // Unit Tests - additional edge cases
  // ---------------------------------------------------------------------------

  describe('unit', () => {
    it('should handle non-ok response when json() fails (falls back to "Unknown error")', async () => {
      // Arrange: server returns non-ok and json parsing fails
      const mockResponse = {
        ok: false,
        status: 502,
        json: vi.fn().mockRejectedValue(new Error('Invalid JSON')),
      } as unknown as Response

      // Act & Assert
      try {
        const gen = streamMessage(mockResponse)
        await gen.next()
        expect.unreachable('Should have thrown')
      } catch (e) {
        expect(e).toBeInstanceOf(ApiError)
        expect((e as ApiError).status).toBe(502)
      }
    })

    it('should delegate to readSSEStream and yield events for ok response with body', async () => {
      // Arrange
      const sseData = 'data: {"type":"text-done"}\n\n'
      const mockResponse = {
        ok: true,
        body: createSSEStream(sseData),
      } as unknown as Response

      // Act
      const events = await collectEvents(streamMessage(mockResponse))

      // Assert
      expect(events).toEqual([{ type: 'text-done' }])
    })

    it('should preserve detail field from error response', async () => {
      // Arrange: response with detail field
      const mockResponse = {
        ok: false,
        status: 404,
        json: vi.fn().mockResolvedValue({ error: 'Session not found', detail: 'Session abc123 expired' }),
      } as unknown as Response

      // Act & Assert
      try {
        const gen = streamMessage(mockResponse)
        await gen.next()
        expect.unreachable('Should have thrown')
      } catch (e) {
        expect(e).toBeInstanceOf(ApiError)
        expect((e as ApiError).detail).toBe('Session abc123 expired')
      }
    })

    it('should yield multiple text-delta events in order', async () => {
      // Arrange: multiple text-delta chunks
      const sseData = [
        'data: {"type":"text-delta","content":"A"}\n\n',
        'data: {"type":"text-delta","content":"B"}\n\n',
        'data: {"type":"text-delta","content":"C"}\n\n',
        'data: {"type":"text-done"}\n\n',
      ].join('')
      const mockResponse = {
        ok: true,
        body: createSSEStream(sseData),
      } as unknown as Response

      // Act
      const events = await collectEvents(streamMessage(mockResponse))

      // Assert: events arrive in order
      expect(events).toHaveLength(4)
      expect(events[0]).toEqual({ type: 'text-delta', content: 'A' })
      expect(events[1]).toEqual({ type: 'text-delta', content: 'B' })
      expect(events[2]).toEqual({ type: 'text-delta', content: 'C' })
      expect(events[3]).toEqual({ type: 'text-done' })
    })
  })
})
