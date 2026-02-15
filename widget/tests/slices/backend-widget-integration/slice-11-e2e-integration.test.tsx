/**
 * E2E Integration Tests for Backend-Widget-Integration.
 * Validates complete flow through all slices 01-10.
 *
 * This test suite validates the integration of all modules (API client, SSE parsing,
 * adapters, error handling) using mocked fetch responses to simulate the full backend flow.
 *
 * Slice-Spec: specs/phase-3/2026-02-15-backend-widget-integration/slices/slice-11-e2e-integration-tests.md
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { SSEEvent } from '../../../src/lib/types'
import { getOrCreateAnonymousId } from '../../../src/lib/anonymous-id'
import { createApiClient } from '../../../src/lib/api-client'
import { streamStart, streamMessage } from '../../../src/lib/sse-parser'
import { createMockSSEResponse, createMockErrorResponse, createSlowMockSSEResponse } from './helpers/mock-sse'

// UUID v4 regex for validation
const UUID_V4_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

// Test API URL
const TEST_API_URL = 'http://localhost:8000'

// Helper to collect all events from async generator
async function collectEvents<T>(generator: AsyncGenerator<T>): Promise<T[]> {
  const events: T[] = []
  for await (const event of generator) {
    events.push(event)
  }
  return events
}

// ---------------------------------------------------------------------------
// Happy Path Scenarios
// ---------------------------------------------------------------------------

describe('E2E Integration: Backend-Widget-Integration', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  describe('Happy Path', () => {
    it('AC-1: should complete full interview flow: start -> message -> end', async () => {
      // Arrange: Mock fetch for /start, /message, /end
      const mockFetch = vi.fn()
      global.fetch = mockFetch

      let callCount = 0
      mockFetch.mockImplementation((url: string, options?: RequestInit) => {
        callCount++

        // First call: POST /api/interview/start
        if (callCount === 1 && url.includes('/start')) {
          const startEvents: SSEEvent[] = [
            { type: 'metadata', session_id: 'session-abc-123' },
            { type: 'text-delta', content: 'Hello! ' },
            { type: 'text-delta', content: 'How can I help you today?' },
            { type: 'text-done' }
          ]
          return Promise.resolve(createMockSSEResponse(startEvents))
        }

        // Second call: POST /api/interview/message
        if (callCount === 2 && url.includes('/message')) {
          const messageEvents: SSEEvent[] = [
            { type: 'text-delta', content: 'Great! ' },
            { type: 'text-delta', content: 'Tell me more.' },
            { type: 'text-done' }
          ]
          return Promise.resolve(createMockSSEResponse(messageEvents))
        }

        // Third call: POST /api/interview/end
        if (callCount === 3 && url.includes('/end')) {
          return Promise.resolve(
            new Response(
              JSON.stringify({ summary: 'Test summary', message_count: 2 }),
              { status: 200, headers: { 'Content-Type': 'application/json' } }
            )
          )
        }

        return Promise.reject(new Error(`Unexpected fetch call: ${url}`))
      })

      // Act: Execute full interview flow
      const apiClient = createApiClient(TEST_API_URL)
      const anonymousId = getOrCreateAnonymousId()

      // Step 1: Start interview
      const startResponse = await apiClient.startInterview(anonymousId)
      const startGenerator = streamStart(startResponse)
      const startEvents = await collectEvents(startGenerator)

      // Step 2: Extract session_id from metadata event
      const metadataEvent = startEvents.find(e => e.type === 'metadata') as { type: 'metadata'; session_id: string } | undefined
      expect(metadataEvent).toBeDefined()
      const sessionId = metadataEvent!.session_id
      expect(sessionId).toBe('session-abc-123')

      // Step 3: Send user message
      const messageResponse = await apiClient.sendMessage(sessionId, 'Great service!')
      const messageGenerator = streamMessage(messageResponse)
      const messageEvents = await collectEvents(messageGenerator)

      // Step 4: End interview
      const endResponse = await apiClient.endInterview(sessionId)
      expect(endResponse.summary).toBe('Test summary')
      expect(endResponse.message_count).toBe(2)

      // Assert: All API calls made in correct order with correct payloads
      expect(mockFetch).toHaveBeenCalledTimes(3)

      // Verify /start call
      expect(mockFetch.mock.calls[0][0]).toContain('/start')
      const startBody = JSON.parse(mockFetch.mock.calls[0][1]?.body as string)
      expect(startBody.anonymous_id).toMatch(UUID_V4_REGEX)

      // Verify /message call
      expect(mockFetch.mock.calls[1][0]).toContain('/message')
      const messageBody = JSON.parse(mockFetch.mock.calls[1][1]?.body as string)
      expect(messageBody.session_id).toBe('session-abc-123')
      expect(messageBody.message).toBe('Great service!')

      // Verify /end call
      expect(mockFetch.mock.calls[2][0]).toContain('/end')
      const endBody = JSON.parse(mockFetch.mock.calls[2][1]?.body as string)
      expect(endBody.session_id).toBe('session-abc-123')

      // Verify SSE events were properly parsed
      expect(startEvents).toHaveLength(4) // metadata + 2 deltas + done
      expect(messageEvents).toHaveLength(3) // 2 deltas + done

      // Verify text content accumulated
      const startText = startEvents
        .filter(e => e.type === 'text-delta')
        .map(e => (e as { content: string }).content)
        .join('')
      expect(startText).toBe('Hello! How can I help you today?')

      const messageText = messageEvents
        .filter(e => e.type === 'text-delta')
        .map(e => (e as { content: string }).content)
        .join('')
      expect(messageText).toBe('Great! Tell me more.')
    })

    it('AC-6: should persist anonymous_id in localStorage', () => {
      // Arrange: localStorage is empty
      expect(localStorage.getItem('feedbackai_anonymous_id')).toBeNull()

      // Act: Get or create anonymous ID
      const id1 = getOrCreateAnonymousId()

      // Assert: Valid UUID v4 stored in localStorage
      expect(id1).toMatch(UUID_V4_REGEX)
      expect(localStorage.getItem('feedbackai_anonymous_id')).toBe(id1)

      // Act: Call again
      const id2 = getOrCreateAnonymousId()

      // Assert: Same ID returned (not regenerated)
      expect(id2).toBe(id1)
    })

    it('should handle multiple rapid messages correctly (queue behavior)', async () => {
      // Arrange: Mock /start and 3x /message calls
      const mockFetch = vi.fn()
      global.fetch = mockFetch

      let callCount = 0
      mockFetch.mockImplementation((url: string) => {
        callCount++

        // /start
        if (callCount === 1 && url.includes('/start')) {
          const events: SSEEvent[] = [
            { type: 'metadata', session_id: 'session-multi-123' },
            { type: 'text-delta', content: 'Hello!' },
            { type: 'text-done' }
          ]
          return Promise.resolve(createMockSSEResponse(events))
        }

        // /message #1
        if (callCount === 2 && url.includes('/message')) {
          const events: SSEEvent[] = [
            { type: 'text-delta', content: 'Response 1' },
            { type: 'text-done' }
          ]
          return Promise.resolve(createMockSSEResponse(events))
        }

        // /message #2
        if (callCount === 3 && url.includes('/message')) {
          const events: SSEEvent[] = [
            { type: 'text-delta', content: 'Response 2' },
            { type: 'text-done' }
          ]
          return Promise.resolve(createMockSSEResponse(events))
        }

        // /message #3
        if (callCount === 4 && url.includes('/message')) {
          const events: SSEEvent[] = [
            { type: 'text-delta', content: 'Response 3' },
            { type: 'text-done' }
          ]
          return Promise.resolve(createMockSSEResponse(events))
        }

        return Promise.reject(new Error('Unexpected call'))
      })

      // Act: Complete /start, then send 3 messages sequentially
      const apiClient = createApiClient(TEST_API_URL)
      const anonymousId = getOrCreateAnonymousId()

      // Start interview
      const startResponse = await apiClient.startInterview(anonymousId)
      const startGenerator = streamStart(startResponse)
      const startEvents = await collectEvents(startGenerator)

      const metadataEvent = startEvents.find(e => e.type === 'metadata') as { type: 'metadata'; session_id: string } | undefined
      const sessionId = metadataEvent!.session_id

      // Send 3 messages sequentially (simulating queue behavior)
      const message1Response = await apiClient.sendMessage(sessionId, 'Message 1')
      const message1Generator = streamMessage(message1Response)
      const message1Events = await collectEvents(message1Generator)

      const message2Response = await apiClient.sendMessage(sessionId, 'Message 2')
      const message2Generator = streamMessage(message2Response)
      const message2Events = await collectEvents(message2Generator)

      const message3Response = await apiClient.sendMessage(sessionId, 'Message 3')
      const message3Generator = streamMessage(message3Response)
      const message3Events = await collectEvents(message3Generator)

      // Assert: All 4 API calls made in sequence (no concurrent)
      expect(mockFetch).toHaveBeenCalledTimes(4)

      // Verify all responses received
      const text1 = message1Events.filter(e => e.type === 'text-delta').map(e => (e as any).content).join('')
      const text2 = message2Events.filter(e => e.type === 'text-delta').map(e => (e as any).content).join('')
      const text3 = message3Events.filter(e => e.type === 'text-delta').map(e => (e as any).content).join('')

      expect(text1).toBe('Response 1')
      expect(text2).toBe('Response 2')
      expect(text3).toBe('Response 3')
    })
  })

  // ---------------------------------------------------------------------------
  // Error Recovery Scenarios
  // ---------------------------------------------------------------------------

  describe('Error Recovery', () => {
    it('AC-2: should handle network error and allow retry', async () => {
      // Arrange: First fetch fails, second succeeds
      const mockFetch = vi.fn()
      global.fetch = mockFetch

      let attemptCount = 0
      mockFetch.mockImplementation((url: string) => {
        attemptCount++

        if (url.includes('/start')) {
          if (attemptCount === 1) {
            // First attempt: network error
            return Promise.reject(new Error('Network error'))
          } else {
            // Second attempt: success
            const events: SSEEvent[] = [
              { type: 'metadata', session_id: 'session-retry-123' },
              { type: 'text-delta', content: 'Hello after retry!' },
              { type: 'text-done' }
            ]
            return Promise.resolve(createMockSSEResponse(events))
          }
        }

        return Promise.reject(new Error('Unexpected call'))
      })

      // Act: First attempt fails
      const apiClient = createApiClient(TEST_API_URL)
      const anonymousId = getOrCreateAnonymousId()

      let errorCaught = false
      try {
        const response = await apiClient.startInterview(anonymousId)
        const gen = streamStart(response)
        await collectEvents(gen)
      } catch (error) {
        errorCaught = true
        expect(error).toBeInstanceOf(Error)
        expect((error as Error).message).toContain('Network error')
      }

      expect(errorCaught).toBe(true)
      expect(mockFetch).toHaveBeenCalledTimes(1)

      // Act: Retry (second attempt succeeds)
      const retryResponse = await apiClient.startInterview(anonymousId)
      const retryGenerator = streamStart(retryResponse)
      const events = await collectEvents(retryGenerator)

      // Assert: Interview proceeds after retry
      expect(mockFetch).toHaveBeenCalledTimes(2)
      expect(events).toHaveLength(3) // metadata + delta + done

      const text = events.filter(e => e.type === 'text-delta').map(e => (e as any).content).join('')
      expect(text).toBe('Hello after retry!')
    })

    it('AC-3: should handle 404 (session expired) error', async () => {
      // Arrange: /message returns 404
      const mockFetch = vi.fn()
      global.fetch = mockFetch

      mockFetch.mockImplementation((url: string) => {
        if (url.includes('/message')) {
          return Promise.resolve(
            createMockErrorResponse('Session expired', 'Session not found', 404)
          )
        }

        return Promise.reject(new Error('Unexpected call'))
      })

      // Act: Send message with expired session
      const apiClient = createApiClient(TEST_API_URL)

      let errorCaught = false
      try {
        const response = await apiClient.sendMessage('expired-session-id', 'Test message')
        const gen = streamMessage(response)
        await collectEvents(gen)
      } catch (error: any) {
        errorCaught = true
        expect(error.name).toBe('ApiError')
        expect(error.status).toBe(404)
        expect(error.message).toContain('Session expired')
      }

      // Assert: 404 error thrown
      expect(errorCaught).toBe(true)
      expect(mockFetch).toHaveBeenCalledTimes(1)
    })

    it('AC-4: should handle 409 (session completed) error', async () => {
      // Arrange: /message returns 409
      const mockFetch = vi.fn()
      global.fetch = mockFetch

      mockFetch.mockImplementation((url: string) => {
        if (url.includes('/message')) {
          return Promise.resolve(
            createMockErrorResponse('Session completed', 'Interview already ended', 409)
          )
        }

        return Promise.reject(new Error('Unexpected call'))
      })

      // Act: Send message to completed session
      const apiClient = createApiClient(TEST_API_URL)

      let errorCaught = false
      try {
        const response = await apiClient.sendMessage('completed-session-id', 'Test message')
        const gen = streamMessage(response)
        await collectEvents(gen)
      } catch (error: any) {
        errorCaught = true
        expect(error.name).toBe('ApiError')
        expect(error.status).toBe(409)
        expect(error.message).toContain('Session completed')
      }

      // Assert: 409 error thrown
      expect(errorCaught).toBe(true)
      expect(mockFetch).toHaveBeenCalledTimes(1)
    })

    it('should handle SSE error event', async () => {
      // Arrange: SSE stream contains error event
      const mockFetch = vi.fn()
      global.fetch = mockFetch

      mockFetch.mockImplementation((url: string) => {
        if (url.includes('/start')) {
          const events: SSEEvent[] = [
            { type: 'metadata', session_id: 'session-123' },
            { type: 'error', message: 'LLM service unavailable' }
          ]
          return Promise.resolve(createMockSSEResponse(events))
        }

        return Promise.reject(new Error('Unexpected call'))
      })

      // Act: Start interview with SSE error
      const apiClient = createApiClient(TEST_API_URL)
      const anonymousId = getOrCreateAnonymousId()

      const response = await apiClient.startInterview(anonymousId)
      const gen = streamStart(response)
      const events = await collectEvents(gen)

      // Assert: Error event is yielded (not thrown)
      expect(events).toHaveLength(2) // metadata + error
      expect(events[0].type).toBe('metadata')
      expect(events[1].type).toBe('error')
      expect((events[1] as any).message).toBe('LLM service unavailable')
    })
  })

  // ---------------------------------------------------------------------------
  // Stream Cleanup Scenarios
  // ---------------------------------------------------------------------------

  describe('Stream Cleanup', () => {
    it('AC-5: should abort SSE stream when AbortController.abort() is called', async () => {
      // Arrange: Slow SSE stream
      const mockFetch = vi.fn()
      global.fetch = mockFetch

      const abortSpy = vi.fn()

      mockFetch.mockImplementation((url: string, options?: RequestInit) => {
        if (url.includes('/start')) {
          // Monitor abort signal
          if (options?.signal) {
            options.signal.addEventListener('abort', abortSpy)
          }

          // Create slow stream (simulates long-running SSE)
          const events: SSEEvent[] = [
            { type: 'metadata', session_id: 'session-abort-123' },
            { type: 'text-delta', content: 'Hello! ' },
            { type: 'text-delta', content: 'This is a long message...' }
            // Note: No text-done, stream never completes
          ]
          return Promise.resolve(createSlowMockSSEResponse(events, 200))
        }

        return Promise.reject(new Error('Unexpected call'))
      })

      // Act: Start interview and abort during streaming
      const apiClient = createApiClient(TEST_API_URL)
      const anonymousId = getOrCreateAnonymousId()
      const abortController = new AbortController()

      const response = await apiClient.startInterview(anonymousId, { signal: abortController.signal })
      const generator = streamStart(response)

      // Collect first few events
      const events: SSEEvent[] = []
      const iterator = generator[Symbol.asyncIterator]()

      // Get first event
      const first = await iterator.next()
      if (!first.done) events.push(first.value)

      // Abort the stream
      abortController.abort()

      // Try to get next event (should throw)
      let abortError = false
      try {
        await iterator.next()
      } catch (error: any) {
        abortError = true
        expect(error.name).toBe('AbortError')
      }

      // Assert: Abort was triggered
      expect(abortSpy).toHaveBeenCalled()
      expect(events.length).toBeGreaterThan(0)
    })

    it('should handle cleanup on stream error', async () => {
      // Arrange: Stream that errors mid-way
      const mockFetch = vi.fn()
      global.fetch = mockFetch

      mockFetch.mockImplementation((url: string) => {
        if (url.includes('/start')) {
          // Create a stream that errors
          const encoder = new TextEncoder()
          const stream = new ReadableStream({
            start(controller) {
              controller.enqueue(encoder.encode('data: {"type":"metadata","session_id":"session-123"}\n\n'))
              controller.enqueue(encoder.encode('data: {"type":"text-delta","content":"Hello"}\n\n'))
              // Simulate stream error
              controller.error(new Error('Stream interrupted'))
            }
          })

          return Promise.resolve(
            new Response(stream, {
              status: 200,
              headers: { 'Content-Type': 'text/event-stream' }
            })
          )
        }

        return Promise.reject(new Error('Unexpected call'))
      })

      // Act: Start interview with stream error
      const apiClient = createApiClient(TEST_API_URL)
      const anonymousId = getOrCreateAnonymousId()

      let errorCaught = false
      try {
        const response = await apiClient.startInterview(anonymousId)
        const gen = streamStart(response)
        await collectEvents(gen)
      } catch (error: any) {
        errorCaught = true
        expect(error.message).toContain('Stream interrupted')
      }

      // Assert: Error caught and handled
      expect(errorCaught).toBe(true)
    })
  })

  // ---------------------------------------------------------------------------
  // Edge Cases
  // ---------------------------------------------------------------------------

  describe('Edge Cases', () => {
    it('should handle empty SSE stream gracefully', async () => {
      // Arrange: Empty SSE stream
      const mockFetch = vi.fn()
      global.fetch = mockFetch

      mockFetch.mockImplementation((url: string) => {
        if (url.includes('/start')) {
          const events: SSEEvent[] = [] // Empty stream
          return Promise.resolve(createMockSSEResponse(events))
        }

        return Promise.reject(new Error('Unexpected call'))
      })

      // Act: Start interview with empty stream
      const apiClient = createApiClient(TEST_API_URL)
      const anonymousId = getOrCreateAnonymousId()

      const response = await apiClient.startInterview(anonymousId)
      const gen = streamStart(response)
      const events = await collectEvents(gen)

      // Assert: No events received
      expect(events).toHaveLength(0)
    })

    it('should handle malformed JSON in SSE stream', async () => {
      // Arrange: Stream with invalid JSON
      const mockFetch = vi.fn()
      global.fetch = mockFetch

      mockFetch.mockImplementation((url: string) => {
        if (url.includes('/start')) {
          const encoder = new TextEncoder()
          const stream = new ReadableStream({
            start(controller) {
              controller.enqueue(encoder.encode('data: {"type":"metadata","session_id":"session-123"}\n\n'))
              controller.enqueue(encoder.encode('data: {invalid json}\n\n')) // Malformed
              controller.close()
            }
          })

          return Promise.resolve(
            new Response(stream, {
              status: 200,
              headers: { 'Content-Type': 'text/event-stream' }
            })
          )
        }

        return Promise.reject(new Error('Unexpected call'))
      })

      // Act: Start interview with malformed JSON
      const apiClient = createApiClient(TEST_API_URL)
      const anonymousId = getOrCreateAnonymousId()

      const response = await apiClient.startInterview(anonymousId)
      const gen = streamStart(response)
      const events = await collectEvents(gen)

      // Assert: Malformed JSON is skipped silently (parseSSELine returns null)
      // Only valid metadata event is collected
      expect(events).toHaveLength(1)
      expect(events[0].type).toBe('metadata')
    })

    it('should handle text-done without any text-delta events', async () => {
      // Arrange: Stream with only metadata and text-done (no deltas)
      const mockFetch = vi.fn()
      global.fetch = mockFetch

      mockFetch.mockImplementation((url: string) => {
        if (url.includes('/start')) {
          const events: SSEEvent[] = [
            { type: 'metadata', session_id: 'session-123' },
            { type: 'text-done' } // No text-delta events
          ]
          return Promise.resolve(createMockSSEResponse(events))
        }

        return Promise.reject(new Error('Unexpected call'))
      })

      // Act: Start interview with no text deltas
      const apiClient = createApiClient(TEST_API_URL)
      const anonymousId = getOrCreateAnonymousId()

      const response = await apiClient.startInterview(anonymousId)
      const gen = streamStart(response)
      const events = await collectEvents(gen)

      // Assert: Events received (metadata + text-done)
      expect(events).toHaveLength(2)
      expect(events[0].type).toBe('metadata')
      expect(events[1].type).toBe('text-done')
    })

    it('should validate API URL in createApiClient', () => {
      // Assert: Empty string throws error
      expect(() => createApiClient('')).toThrow('API URL not configured')

      // Assert: null throws error
      expect(() => createApiClient(null)).toThrow('API URL not configured')

      // Assert: Valid URL succeeds (even if not a perfect URL format)
      const client1 = createApiClient('http://localhost:8000')
      expect(client1).toBeDefined()
      expect(client1.startInterview).toBeInstanceOf(Function)
      expect(client1.sendMessage).toBeInstanceOf(Function)
      expect(client1.endInterview).toBeInstanceOf(Function)

      // Assert: Non-standard URLs are accepted (validation happens at fetch time)
      const client2 = createApiClient('not-a-url')
      expect(client2).toBeDefined()
    })
  })
})
