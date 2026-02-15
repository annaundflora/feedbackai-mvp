/**
 * Acceptance + Unit Tests for Slice 04: Interview-Ende API Call /end.
 * Derived from GIVEN/WHEN/THEN Acceptance Criteria in the Slice-Spec.
 *
 * Slice-Spec: specs/phase-3/2026-02-15-backend-widget-integration/slices/slice-04-interview-end.md
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createApiClient, type ApiClient } from '../../../src/lib/api-client'
import { ApiError } from '../../../src/lib/types'

const BASE_URL = 'http://localhost:8000'

describe('Slice 04: Interview-End /end', () => {
  let fetchSpy: ReturnType<typeof vi.fn>
  let client: ApiClient

  beforeEach(() => {
    vi.restoreAllMocks()
    fetchSpy = vi.fn()
    vi.stubGlobal('fetch', fetchSpy)
    client = createApiClient(BASE_URL)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // Helper to create a mock Response
  function mockResponse(body: unknown, init?: ResponseInit): Response {
    return new Response(JSON.stringify(body), {
      status: init?.status ?? 200,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
      ...init,
    })
  }

  // ---------------------------------------------------------------------------
  // endInterview - Acceptance Tests
  // ---------------------------------------------------------------------------

  describe('endInterview - acceptance', () => {
    it('AC-1: GIVEN a valid session_id WHEN endInterview() is called THEN it returns { summary: string, message_count: number }', async () => {
      // Arrange (GIVEN)
      const expectedData = { summary: 'Good feedback', message_count: 5 }
      fetchSpy.mockResolvedValue(mockResponse(expectedData))

      // Act (WHEN)
      const result = await client.endInterview('valid-session-id')

      // Assert (THEN)
      expect(result).toEqual({ summary: 'Good feedback', message_count: 5 })
      expect(typeof result.summary).toBe('string')
      expect(typeof result.message_count).toBe('number')

      // Verify correct endpoint was called
      const [url, options] = fetchSpy.mock.calls[0]
      expect(url).toBe('http://localhost:8000/api/interview/end')
      expect(options.method).toBe('POST')
      expect(JSON.parse(options.body)).toEqual({ session_id: 'valid-session-id' })
    })

    it('AC-2: GIVEN a 404 response WHEN endInterview() is called THEN it throws ApiError with status 404', async () => {
      // Arrange (GIVEN)
      fetchSpy.mockResolvedValue(
        mockResponse({ error: 'Session not found' }, { status: 404 })
      )

      // Act & Assert (WHEN / THEN)
      await expect(client.endInterview('expired-session')).rejects.toThrow(ApiError)

      // Verify status code
      try {
        fetchSpy.mockResolvedValue(
          mockResponse({ error: 'Session not found' }, { status: 404 })
        )
        await client.endInterview('expired-session')
        expect.unreachable('Should have thrown')
      } catch (e) {
        expect(e).toBeInstanceOf(ApiError)
        expect((e as ApiError).status).toBe(404)
      }
    })

    it('AC-3: GIVEN a 409 response WHEN endInterview() is called THEN it throws ApiError with status 409', async () => {
      // Arrange (GIVEN)
      fetchSpy.mockResolvedValue(
        mockResponse({ error: 'Session already completed' }, { status: 409 })
      )

      // Act & Assert (WHEN / THEN)
      await expect(client.endInterview('completed-session')).rejects.toThrow(ApiError)

      // Verify status code
      try {
        fetchSpy.mockResolvedValue(
          mockResponse({ error: 'Session already completed' }, { status: 409 })
        )
        await client.endInterview('completed-session')
        expect.unreachable('Should have thrown')
      } catch (e) {
        expect(e).toBeInstanceOf(ApiError)
        expect((e as ApiError).status).toBe(409)
      }
    })

    it('AC-4: GIVEN a 500 response WHEN endInterview() is called THEN it throws ApiError with status 500', async () => {
      // Arrange (GIVEN)
      fetchSpy.mockResolvedValue(
        mockResponse({ error: 'Internal server error' }, { status: 500 })
      )

      // Act & Assert (WHEN / THEN)
      await expect(client.endInterview('any-session')).rejects.toThrow(ApiError)

      // Verify status code
      try {
        fetchSpy.mockResolvedValue(
          mockResponse({ error: 'Internal server error' }, { status: 500 })
        )
        await client.endInterview('any-session')
        expect.unreachable('Should have thrown')
      } catch (e) {
        expect(e).toBeInstanceOf(ApiError)
        expect((e as ApiError).status).toBe(500)
      }
    })
  })

  // ---------------------------------------------------------------------------
  // endInterviewSafe - Acceptance Tests
  // ---------------------------------------------------------------------------

  describe('endInterviewSafe - acceptance', () => {
    it('AC-5: GIVEN any scenario WHEN endInterviewSafe() is called and the request succeeds THEN it returns the EndResponse', async () => {
      // Arrange (GIVEN)
      const expectedData = { summary: 'Interview completed', message_count: 8 }
      fetchSpy.mockResolvedValue(mockResponse(expectedData))

      // Act (WHEN)
      const result = await client.endInterviewSafe('valid-session-id')

      // Assert (THEN)
      expect(result).toEqual({ summary: 'Interview completed', message_count: 8 })
      expect(result).not.toBeNull()
    })

    it('AC-6: GIVEN any error WHEN endInterviewSafe() is called THEN it returns null and logs console.warn()', async () => {
      // Arrange (GIVEN) - server returns 500
      fetchSpy.mockResolvedValue(
        mockResponse({ error: 'Server error' }, { status: 500 })
      )
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      // Act (WHEN)
      const result = await client.endInterviewSafe('any-session')

      // Assert (THEN)
      expect(result).toBeNull()
      expect(warnSpy).toHaveBeenCalledOnce()
      expect(warnSpy).toHaveBeenCalledWith('Failed to end interview:', expect.any(ApiError))
    })

    it('AC-6 (network error): GIVEN a network failure WHEN endInterviewSafe() is called THEN it returns null and logs console.warn()', async () => {
      // Arrange (GIVEN) - network error (fetch rejects)
      fetchSpy.mockRejectedValue(new TypeError('Failed to fetch'))
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      // Act (WHEN)
      const result = await client.endInterviewSafe('any-session')

      // Assert (THEN)
      expect(result).toBeNull()
      expect(warnSpy).toHaveBeenCalledOnce()
      expect(warnSpy).toHaveBeenCalledWith('Failed to end interview:', expect.any(TypeError))
    })

    it('AC-7: GIVEN an AbortSignal WHEN endInterviewSafe() is called with the signal THEN the request is cancellable', async () => {
      // Arrange (GIVEN)
      const controller = new AbortController()
      fetchSpy.mockResolvedValue(mockResponse({ summary: 'Done', message_count: 3 }))

      // Act (WHEN)
      await client.endInterviewSafe('session-id', { signal: controller.signal })

      // Assert (THEN) - signal is forwarded to fetch
      const [, options] = fetchSpy.mock.calls[0]
      expect(options.signal).toBe(controller.signal)
    })

    it('AC-7 (abort during request): GIVEN an AbortSignal WHEN the signal is aborted during endInterviewSafe() THEN it returns null (does not throw)', async () => {
      // Arrange (GIVEN)
      const controller = new AbortController()
      fetchSpy.mockImplementation(() => {
        controller.abort()
        return Promise.reject(new DOMException('The operation was aborted', 'AbortError'))
      })
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      // Act (WHEN)
      const result = await client.endInterviewSafe('session-id', { signal: controller.signal })

      // Assert (THEN)
      expect(result).toBeNull()
      expect(warnSpy).toHaveBeenCalled()
    })
  })

  // ---------------------------------------------------------------------------
  // Unit Tests - additional edge cases
  // ---------------------------------------------------------------------------

  describe('endInterview - unit', () => {
    it('should parse JSON response body correctly for endInterview', async () => {
      // Verifies the JSON parsing pipeline works end-to-end
      const data = { summary: 'Detailed summary with special chars: <>&"', message_count: 42 }
      fetchSpy.mockResolvedValue(mockResponse(data))

      const result = await client.endInterview('sess-123')

      expect(result.summary).toBe('Detailed summary with special chars: <>&"')
      expect(result.message_count).toBe(42)
    })

    it('should handle non-JSON error response body gracefully', async () => {
      // When server returns plain text error (not JSON)
      fetchSpy.mockResolvedValue(
        new Response('Internal Server Error', { status: 500 })
      )

      await expect(client.endInterview('sess-123')).rejects.toThrow(ApiError)
    })

    it('should include error detail from response when available', async () => {
      fetchSpy.mockResolvedValue(
        mockResponse({ error: 'Conflict', detail: 'Session already ended' }, { status: 409 })
      )

      try {
        await client.endInterview('sess-123')
        expect.unreachable('Should have thrown')
      } catch (e) {
        expect(e).toBeInstanceOf(ApiError)
        expect((e as ApiError).status).toBe(409)
        expect((e as ApiError).detail).toBe('Session already ended')
      }
    })
  })

  describe('endInterviewSafe - unit', () => {
    it('should never throw regardless of error type', async () => {
      // Test with various error types to ensure none leak through
      const errorCases = [
        () => fetchSpy.mockRejectedValue(new TypeError('Network error')),
        () => fetchSpy.mockRejectedValue(new DOMException('Aborted', 'AbortError')),
        () => fetchSpy.mockResolvedValue(mockResponse({ error: 'Not found' }, { status: 404 })),
        () => fetchSpy.mockResolvedValue(mockResponse({ error: 'Conflict' }, { status: 409 })),
        () => fetchSpy.mockResolvedValue(mockResponse({ error: 'Server error' }, { status: 500 })),
      ]

      vi.spyOn(console, 'warn').mockImplementation(() => {})

      for (const setupError of errorCases) {
        setupError()
        // endInterviewSafe should NEVER throw
        const result = await client.endInterviewSafe('sess-123')
        expect(result).toBeNull()
      }
    })
  })
})
