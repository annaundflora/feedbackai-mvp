/**
 * Acceptance + Unit Tests for Slice 01: Anonymous-ID Manager + API-Client Foundation.
 * Derived from GIVEN/WHEN/THEN Acceptance Criteria in the Slice-Spec.
 *
 * Slice-Spec: specs/phase-3/2026-02-15-backend-widget-integration/slices/slice-01-anonymous-id-api-client.md
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { getOrCreateAnonymousId } from '../../../src/lib/anonymous-id'
import { createApiClient, type ApiClient } from '../../../src/lib/api-client'
import { ApiError } from '../../../src/lib/types'

// UUID v4 regex pattern
const UUID_V4_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

// ---------------------------------------------------------------------------
// Anonymous-ID Manager
// ---------------------------------------------------------------------------

describe('Anonymous-ID Manager', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  describe('acceptance', () => {
    it('AC-1: GIVEN the widget loads for the first time WHEN getOrCreateAnonymousId() is called THEN a UUID v4 is generated via crypto.randomUUID() AND stored in localStorage key feedbackai_anonymous_id AND returned', () => {
      // Arrange (GIVEN): localStorage is empty (cleared in beforeEach)

      // Act (WHEN)
      const id = getOrCreateAnonymousId()

      // Assert (THEN)
      expect(id).toMatch(UUID_V4_REGEX)
      expect(localStorage.getItem('feedbackai_anonymous_id')).toBe(id)
    })

    it('AC-2: GIVEN an anonymous_id already exists in localStorage WHEN getOrCreateAnonymousId() is called THEN the existing value is returned without generating a new one', () => {
      // Arrange (GIVEN)
      const existingId = 'aaaaaaaa-bbbb-4ccc-9ddd-eeeeeeeeeeee'
      localStorage.setItem('feedbackai_anonymous_id', existingId)
      const randomUUIDSpy = vi.spyOn(crypto, 'randomUUID')

      // Act (WHEN)
      const id = getOrCreateAnonymousId()

      // Assert (THEN)
      expect(id).toBe(existingId)
      expect(randomUUIDSpy).not.toHaveBeenCalled()
    })

    it('AC-3: GIVEN localStorage is blocked (SecurityError) WHEN getOrCreateAnonymousId() is called THEN a fresh UUID is generated and returned (no persistence, no throw)', () => {
      // Arrange (GIVEN): mock localStorage to throw SecurityError
      vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
        throw new DOMException('Access denied', 'SecurityError')
      })

      // Act (WHEN) -- should NOT throw
      const id = getOrCreateAnonymousId()

      // Assert (THEN)
      expect(id).toMatch(UUID_V4_REGEX)
    })
  })

  describe('unit', () => {
    it('should generate valid UUID v4 format', () => {
      const id = getOrCreateAnonymousId()
      expect(id).toMatch(UUID_V4_REGEX)
    })

    it('should return the same ID on repeated calls (idempotent)', () => {
      const first = getOrCreateAnonymousId()
      const second = getOrCreateAnonymousId()
      expect(first).toBe(second)
    })

    it('should still return a UUID when localStorage.setItem throws', () => {
      vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null)
      vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
        throw new DOMException('Quota exceeded', 'QuotaExceededError')
      })

      const id = getOrCreateAnonymousId()
      expect(id).toMatch(UUID_V4_REGEX)
    })
  })
})

// ---------------------------------------------------------------------------
// API-Client
// ---------------------------------------------------------------------------

describe('API-Client', () => {
  const BASE_URL = 'http://localhost:8000'
  let fetchSpy: ReturnType<typeof vi.fn>

  beforeEach(() => {
    vi.restoreAllMocks()
    fetchSpy = vi.fn()
    vi.stubGlobal('fetch', fetchSpy)
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

  describe('acceptance', () => {
    it('AC-4: GIVEN a valid apiUrl from config WHEN createApiClient(apiUrl) is called THEN an object with startInterview, sendMessage, endInterview methods is returned', () => {
      // Arrange (GIVEN): valid apiUrl
      // Act (WHEN)
      const client = createApiClient(BASE_URL)

      // Assert (THEN)
      expect(client).toBeDefined()
      expect(typeof client.startInterview).toBe('function')
      expect(typeof client.sendMessage).toBe('function')
      expect(typeof client.endInterview).toBe('function')
    })

    it('AC-5: GIVEN apiUrl is null WHEN createApiClient(null) is called THEN an error is thrown with message "API URL not configured"', () => {
      // Act & Assert
      expect(() => createApiClient(null)).toThrowError('API URL not configured')
    })

    it('AC-6: GIVEN a valid apiClient WHEN startInterview(anonymous_id) is called THEN a fetch POST to {apiUrl}/api/interview/start with body {"anonymous_id": "..."} and Content-Type application/json is made AND the raw Response is returned', async () => {
      // Arrange (GIVEN)
      const client = createApiClient(BASE_URL)
      const fakeResponse = mockResponse({ session_id: 'sess-123' })
      fetchSpy.mockResolvedValue(fakeResponse)

      // Act (WHEN)
      const response = await client.startInterview('test-anon-id')

      // Assert (THEN)
      expect(fetchSpy).toHaveBeenCalledOnce()
      const [url, options] = fetchSpy.mock.calls[0]
      expect(url).toBe('http://localhost:8000/api/interview/start')
      expect(options.method).toBe('POST')
      expect(options.headers['Content-Type']).toBe('application/json')
      expect(JSON.parse(options.body)).toEqual({ anonymous_id: 'test-anon-id' })
      // Raw Response returned
      expect(response).toBe(fakeResponse)
    })

    it('AC-7: GIVEN a valid apiClient WHEN sendMessage(session_id, message) is called THEN a fetch POST to {apiUrl}/api/interview/message with body {"session_id": "...", "message": "..."} is made AND the raw Response is returned', async () => {
      // Arrange (GIVEN)
      const client = createApiClient(BASE_URL)
      const fakeResponse = mockResponse({ ok: true })
      fetchSpy.mockResolvedValue(fakeResponse)

      // Act (WHEN)
      const response = await client.sendMessage('sess-123', 'Hello')

      // Assert (THEN)
      expect(fetchSpy).toHaveBeenCalledOnce()
      const [url, options] = fetchSpy.mock.calls[0]
      expect(url).toBe('http://localhost:8000/api/interview/message')
      expect(options.method).toBe('POST')
      expect(JSON.parse(options.body)).toEqual({ session_id: 'sess-123', message: 'Hello' })
      expect(response).toBe(fakeResponse)
    })

    it('AC-8: GIVEN a valid apiClient WHEN endInterview(session_id) is called THEN a fetch POST to {apiUrl}/api/interview/end with body {"session_id": "..."} is made AND the JSON response {summary, message_count} is returned', async () => {
      // Arrange (GIVEN)
      const client = createApiClient(BASE_URL)
      const endData = { summary: 'Great feedback session', message_count: 5 }
      fetchSpy.mockResolvedValue(mockResponse(endData))

      // Act (WHEN)
      const result = await client.endInterview('sess-123')

      // Assert (THEN)
      expect(fetchSpy).toHaveBeenCalledOnce()
      const [url, options] = fetchSpy.mock.calls[0]
      expect(url).toBe('http://localhost:8000/api/interview/end')
      expect(options.method).toBe('POST')
      expect(JSON.parse(options.body)).toEqual({ session_id: 'sess-123' })
      expect(result).toEqual(endData)
    })

    it('AC-9: GIVEN any apiClient method WHEN an AbortSignal is passed THEN the fetch uses that signal AND aborting the signal cancels the request', async () => {
      // Arrange (GIVEN)
      const client = createApiClient(BASE_URL)
      const controller = new AbortController()
      fetchSpy.mockResolvedValue(mockResponse({}))

      // Act (WHEN)
      await client.startInterview('anon-id', { signal: controller.signal })

      // Assert (THEN) -- signal is passed to fetch
      const [, options] = fetchSpy.mock.calls[0]
      expect(options.signal).toBe(controller.signal)
    })

    it('AC-9 (sendMessage): AbortSignal is forwarded for sendMessage', async () => {
      const client = createApiClient(BASE_URL)
      const controller = new AbortController()
      fetchSpy.mockResolvedValue(mockResponse({}))

      await client.sendMessage('sess-123', 'hi', { signal: controller.signal })

      const [, options] = fetchSpy.mock.calls[0]
      expect(options.signal).toBe(controller.signal)
    })

    it('AC-9 (endInterview): AbortSignal is forwarded for endInterview', async () => {
      const client = createApiClient(BASE_URL)
      const controller = new AbortController()
      fetchSpy.mockResolvedValue(mockResponse({ summary: '', message_count: 0 }))

      await client.endInterview('sess-123', { signal: controller.signal })

      const [, options] = fetchSpy.mock.calls[0]
      expect(options.signal).toBe(controller.signal)
    })

    it('AC-10: GIVEN apiUrl has a trailing slash WHEN any endpoint is called THEN the URL is constructed correctly without double slashes', async () => {
      // Arrange (GIVEN): trailing slash in URL
      const client = createApiClient('http://localhost:8000/')
      fetchSpy.mockResolvedValue(mockResponse({}))

      // Act (WHEN)
      await client.startInterview('anon-id')

      // Assert (THEN)
      const [url] = fetchSpy.mock.calls[0]
      expect(url).toBe('http://localhost:8000/api/interview/start')
      // Verify no double slashes after the protocol+host portion
      const pathPart = new URL(url).pathname
      expect(pathPart).toBe('/api/interview/start')
      expect(pathPart).not.toMatch(/\/\//)
    })
  })

  describe('unit', () => {
    it('should throw ApiError with status when endInterview gets non-ok response', async () => {
      const client = createApiClient(BASE_URL)
      fetchSpy.mockResolvedValue(
        new Response(JSON.stringify({ error: 'Not found', detail: 'Session not found' }), {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        })
      )

      await expect(client.endInterview('bad-session')).rejects.toThrow(ApiError)
      try {
        await client.endInterview('bad-session')
      } catch (e) {
        expect(e).toBeInstanceOf(ApiError)
        expect((e as ApiError).status).toBe(404)
      }
    })

    it('should handle endInterview error when response body is not JSON', async () => {
      const client = createApiClient(BASE_URL)
      fetchSpy.mockResolvedValue(
        new Response('Internal Server Error', {
          status: 500,
        })
      )

      await expect(client.endInterview('bad-session')).rejects.toThrow(ApiError)
    })

    it('should handle trailing multiple slashes in apiUrl', async () => {
      const client = createApiClient('http://localhost:8000///')
      fetchSpy.mockResolvedValue(mockResponse({}))

      await client.startInterview('anon-id')

      const [url] = fetchSpy.mock.calls[0]
      expect(url).toBe('http://localhost:8000/api/interview/start')
    })

    it('should throw for empty string apiUrl', () => {
      expect(() => createApiClient('')).toThrowError('API URL not configured')
    })
  })
})
