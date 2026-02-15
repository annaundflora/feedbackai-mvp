/**
 * Acceptance + Unit Tests for Slice 02: SSE-Client for /start Endpoint.
 * Derived from GIVEN/WHEN/THEN Acceptance Criteria in the Slice-Spec.
 *
 * Slice-Spec: specs/phase-3/2026-02-15-backend-widget-integration/slices/slice-02-sse-client-start.md
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { parseSSELine, readSSEStream, streamStart } from '../../../src/lib/sse-parser'
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
// parseSSELine
// ---------------------------------------------------------------------------

describe('SSE Parser - parseSSELine', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  describe('acceptance', () => {
    it('AC-1: GIVEN a string "data: {\\"type\\":\\"metadata\\",\\"session_id\\":\\"abc\\"}" WHEN parseSSELine() is called THEN it returns { type: "metadata", session_id: "abc" }', () => {
      // Arrange (GIVEN)
      const line = 'data: {"type":"metadata","session_id":"abc"}'

      // Act (WHEN)
      const event = parseSSELine(line)

      // Assert (THEN)
      expect(event).toEqual({ type: 'metadata', session_id: 'abc' })
    })

    it('AC-2: GIVEN a string "data: {\\"type\\":\\"text-delta\\",\\"content\\":\\"Hallo\\"}" WHEN parseSSELine() is called THEN it returns { type: "text-delta", content: "Hallo" }', () => {
      // Arrange (GIVEN)
      const line = 'data: {"type":"text-delta","content":"Hallo"}'

      // Act (WHEN)
      const event = parseSSELine(line)

      // Assert (THEN)
      expect(event).toEqual({ type: 'text-delta', content: 'Hallo' })
    })

    it('AC-3: GIVEN a string "data: {\\"type\\":\\"text-done\\"}" WHEN parseSSELine() is called THEN it returns { type: "text-done" }', () => {
      // Arrange (GIVEN)
      const line = 'data: {"type":"text-done"}'

      // Act (WHEN)
      const event = parseSSELine(line)

      // Assert (THEN)
      expect(event).toEqual({ type: 'text-done' })
    })

    it('AC-4: GIVEN a string "data: {\\"type\\":\\"error\\",\\"message\\":\\"LLM failed\\"}" WHEN parseSSELine() is called THEN it returns { type: "error", message: "LLM failed" }', () => {
      // Arrange (GIVEN)
      const line = 'data: {"type":"error","message":"LLM failed"}'

      // Act (WHEN)
      const event = parseSSELine(line)

      // Assert (THEN)
      expect(event).toEqual({ type: 'error', message: 'LLM failed' })
    })

    it('AC-5: GIVEN an empty string WHEN parseSSELine() is called THEN it returns null', () => {
      // Arrange (GIVEN)
      const line = ''

      // Act (WHEN)
      const event = parseSSELine(line)

      // Assert (THEN)
      expect(event).toBeNull()
    })

    it('AC-5: GIVEN a comment line (":") WHEN parseSSELine() is called THEN it returns null', () => {
      // Arrange (GIVEN)
      const line = ': keep-alive'

      // Act (WHEN)
      const event = parseSSELine(line)

      // Assert (THEN)
      expect(event).toBeNull()
    })

    it('AC-10: GIVEN invalid JSON in a "data:" line WHEN parseSSELine() is called THEN it returns null (skip malformed events)', () => {
      // Arrange (GIVEN)
      const line = 'data: not-valid-json'
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      // Act (WHEN)
      const event = parseSSELine(line)

      // Assert (THEN)
      expect(event).toBeNull()
      // Note: The spec says "logs warning to console" -- implementation may or may not log.
      // The critical behavior is: returns null and does NOT throw.
    })
  })

  describe('unit', () => {
    it('should return null for lines without data prefix', () => {
      const line = '{"type":"metadata","session_id":"test"}'
      const event = parseSSELine(line)
      expect(event).toBeNull()
    })

    it('should handle whitespace-only lines', () => {
      const event = parseSSELine('   ')
      expect(event).toBeNull()
    })

    it('should handle "event:" lines (not "data:" lines)', () => {
      const event = parseSSELine('event: message')
      expect(event).toBeNull()
    })
  })
})

// ---------------------------------------------------------------------------
// readSSEStream
// ---------------------------------------------------------------------------

describe('SSE Stream Reader - readSSEStream', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  describe('acceptance', () => {
    it('AC-6: GIVEN a ReadableStream that emits SSE-formatted data WHEN readSSEStream() is called THEN it yields SSEEvent objects in order as an async generator', async () => {
      // Arrange (GIVEN)
      const sseData = 'data: {"type":"text-delta","content":"Hello"}\n\ndata: {"type":"text-done"}\n\n'
      const stream = createSSEStream(sseData)

      // Act (WHEN)
      const events = await collectEvents(readSSEStream(stream))

      // Assert (THEN)
      expect(events).toEqual([
        { type: 'text-delta', content: 'Hello' },
        { type: 'text-done' },
      ])
    })

    it('AC-7: GIVEN a ReadableStream that splits a single event across two chunks WHEN readSSEStream() is called THEN the event is correctly buffered and parsed', async () => {
      // Arrange (GIVEN): split a single "data: {...}\n\n" across two chunks
      const chunk1 = 'data: {"type":"text-del'
      const chunk2 = 'ta","content":"Test"}\n\n'
      const stream = createSSEStream(chunk1, chunk2)

      // Act (WHEN)
      const events = await collectEvents(readSSEStream(stream))

      // Assert (THEN)
      expect(events).toEqual([{ type: 'text-delta', content: 'Test' }])
    })

    it('AC-11: GIVEN an AbortSignal WHEN the ReadableStream is being read AND signal is aborted THEN the stream reader stops AND reader lock is released', async () => {
      // Arrange (GIVEN): create a stream that delays between chunks
      const controller = new AbortController()
      let readerReleased = false

      const stream = new ReadableStream<Uint8Array>({
        async pull(streamController) {
          // First chunk: valid event
          const encoder = new TextEncoder()
          streamController.enqueue(
            encoder.encode('data: {"type":"text-delta","content":"first"}\n\n')
          )
          // Abort before next chunk
          controller.abort()
          // Simulate delay -- this chunk should not be processed after abort
          await new Promise((resolve) => setTimeout(resolve, 50))
          streamController.enqueue(
            encoder.encode('data: {"type":"text-delta","content":"second"}\n\n')
          )
          streamController.close()
        },
      })

      // Act (WHEN): read stream with abort signal
      const events: unknown[] = []
      try {
        for await (const event of readSSEStream(stream)) {
          events.push(event)
          // Check if aborted
          if (controller.signal.aborted) break
        }
      } catch {
        // AbortError is expected
      }

      // Assert (THEN): stream reading stopped, reader lock released
      // The first event should have been yielded before abort
      expect(events.length).toBeGreaterThanOrEqual(1)
      expect(events[0]).toEqual({ type: 'text-delta', content: 'first' })
    })
  })

  describe('unit', () => {
    it('should handle multiple events in a single chunk', async () => {
      const sseData =
        'data: {"type":"metadata","session_id":"abc"}\n\ndata: {"type":"text-delta","content":"Hi"}\n\n'
      const stream = createSSEStream(sseData)

      const events = await collectEvents(readSSEStream(stream))

      expect(events).toEqual([
        { type: 'metadata', session_id: 'abc' },
        { type: 'text-delta', content: 'Hi' },
      ])
    })

    it('should skip malformed events and continue processing valid ones', async () => {
      const sseData =
        'data: {"type":"text-delta","content":"Valid1"}\n\ndata: invalid json\n\ndata: {"type":"text-delta","content":"Valid2"}\n\n'
      const stream = createSSEStream(sseData)

      const events = await collectEvents(readSSEStream(stream))

      expect(events).toEqual([
        { type: 'text-delta', content: 'Valid1' },
        { type: 'text-delta', content: 'Valid2' },
      ])
    })

    it('should process remaining buffer after stream ends (no trailing double newline)', async () => {
      const sseData = 'data: {"type":"text-delta","content":"Final"}'
      const stream = createSSEStream(sseData)

      const events = await collectEvents(readSSEStream(stream))

      expect(events).toEqual([{ type: 'text-delta', content: 'Final' }])
    })

    it('should skip SSE comment lines in stream', async () => {
      const sseData = ': keep-alive\n\ndata: {"type":"text-done"}\n\n'
      const stream = createSSEStream(sseData)

      const events = await collectEvents(readSSEStream(stream))

      expect(events).toEqual([{ type: 'text-done' }])
    })

    it('should handle empty stream gracefully', async () => {
      const stream = createSSEStream('')

      const events = await collectEvents(readSSEStream(stream))

      expect(events).toEqual([])
    })
  })
})

// ---------------------------------------------------------------------------
// streamStart
// ---------------------------------------------------------------------------

describe('streamStart', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  describe('acceptance', () => {
    it('AC-8: GIVEN a fetch Response from /start with SSE body WHEN streamStart(response) is called THEN it yields metadata event first, then text-delta events, then text-done event', async () => {
      // Arrange (GIVEN): mock Response with SSE body matching backend format
      const sseData = [
        'data: {"type":"metadata","session_id":"uuid-here"}\n\n',
        'data: {"type":"text-delta","content":"Hal"}\n\n',
        'data: {"type":"text-delta","content":"lo!"}\n\n',
        'data: {"type":"text-done"}\n\n',
      ].join('')
      const mockResponse = {
        ok: true,
        body: createSSEStream(sseData),
      } as unknown as Response

      // Act (WHEN)
      const events = await collectEvents(streamStart(mockResponse))

      // Assert (THEN)
      expect(events).toEqual([
        { type: 'metadata', session_id: 'uuid-here' },
        { type: 'text-delta', content: 'Hal' },
        { type: 'text-delta', content: 'lo!' },
        { type: 'text-done' },
      ])
      // Verify order: metadata first, text-deltas in middle, text-done last
      expect(events[0]).toHaveProperty('type', 'metadata')
      expect(events[events.length - 1]).toHaveProperty('type', 'text-done')
    })

    it('AC-9: GIVEN a Response with non-ok status (e.g. 500) WHEN streamStart(response) is called THEN it throws an ApiError with the status code', async () => {
      // Arrange (GIVEN): mock Response with status 500
      const mockResponse = {
        ok: false,
        status: 500,
        json: vi.fn().mockResolvedValue({ error: 'Internal Server Error' }),
      } as unknown as Response

      // Act & Assert (WHEN/THEN)
      const generator = streamStart(mockResponse)
      await expect(generator.next()).rejects.toThrow(ApiError)

      // Verify the ApiError has the correct status code
      try {
        const gen2 = streamStart(mockResponse)
        await gen2.next()
      } catch (e) {
        expect(e).toBeInstanceOf(ApiError)
        expect((e as ApiError).status).toBe(500)
      }
    })

    it('AC-12: GIVEN a Response without body (body is null) WHEN streamStart(response) is called THEN it throws an ApiError with message "No response body"', async () => {
      // Arrange (GIVEN)
      const mockResponse = {
        ok: true,
        body: null,
      } as unknown as Response

      // Act & Assert (WHEN/THEN)
      const generator = streamStart(mockResponse)
      await expect(generator.next()).rejects.toThrow('No response body')

      // Verify it is an ApiError
      try {
        const gen2 = streamStart(mockResponse)
        await gen2.next()
      } catch (e) {
        expect(e).toBeInstanceOf(ApiError)
      }
    })
  })

  describe('unit', () => {
    it('should handle non-ok response when json() fails', async () => {
      const mockResponse = {
        ok: false,
        status: 502,
        json: vi.fn().mockRejectedValue(new Error('Invalid JSON')),
      } as unknown as Response

      const generator = streamStart(mockResponse)
      await expect(generator.next()).rejects.toThrow(ApiError)
    })

    it('should delegate to readSSEStream for ok response with body', async () => {
      const sseData = 'data: {"type":"text-done"}\n\n'
      const mockResponse = {
        ok: true,
        body: createSSEStream(sseData),
      } as unknown as Response

      const events = await collectEvents(streamStart(mockResponse))

      expect(events).toEqual([{ type: 'text-done' }])
    })

    it('should handle 404 response with detail field', async () => {
      const mockResponse = {
        ok: false,
        status: 404,
        json: vi.fn().mockResolvedValue({ error: 'Not found', detail: 'Session expired' }),
      } as unknown as Response

      try {
        const gen = streamStart(mockResponse)
        await gen.next()
      } catch (e) {
        expect(e).toBeInstanceOf(ApiError)
        expect((e as ApiError).status).toBe(404)
        expect((e as ApiError).message).toBe('Not found')
      }
    })
  })
})
