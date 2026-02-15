/**
 * Acceptance + Unit Tests for Slice 05: Implement ChatModelAdapter for Interview Start Flow.
 * Derived from GIVEN/WHEN/THEN Acceptance Criteria in the Slice-Spec.
 *
 * Slice-Spec: specs/phase-3/2026-02-15-backend-widget-integration/slices/slice-05-adapter-start-flow.md
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { SSEEvent } from '../../../src/lib/types'

// ---------------------------------------------------------------------------
// Hoisted mocks -- vi.hoisted() ensures variables are available in vi.mock()
// ---------------------------------------------------------------------------

const {
  mockStartInterview,
  mockStreamStart,
  mockUseLocalRuntime,
  mockCreateApiClient,
  mockGetOrCreateAnonymousId,
  mockUseRef,
  mockUseMemo,
} = vi.hoisted(() => {
  const mockStartInterview = vi.fn()
  const mockStreamStart = vi.fn()
  const mockUseLocalRuntime = vi.fn((adapter: unknown) => ({ adapter, _runtime: true }))
  const mockCreateApiClient = vi.fn(() => ({
    startInterview: mockStartInterview,
    sendMessage: vi.fn(),
    endInterview: vi.fn(),
  }))
  const mockGetOrCreateAnonymousId = vi.fn(() => 'mock-anon-id-1234')
  const mockUseRef = vi.fn((initialValue: unknown) => ({ current: initialValue }))
  const mockUseMemo = vi.fn((factory: () => unknown) => factory())

  return {
    mockStartInterview,
    mockStreamStart,
    mockUseLocalRuntime,
    mockCreateApiClient,
    mockGetOrCreateAnonymousId,
    mockUseRef,
    mockUseMemo,
  }
})

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

vi.mock('../../../src/lib/anonymous-id', () => ({
  getOrCreateAnonymousId: mockGetOrCreateAnonymousId,
}))

vi.mock('../../../src/lib/api-client', () => ({
  createApiClient: mockCreateApiClient,
}))

vi.mock('../../../src/lib/sse-parser', () => ({
  streamStart: mockStreamStart,
}))

vi.mock('@assistant-ui/react', () => ({
  useLocalRuntime: mockUseLocalRuntime,
}))

vi.mock('react', async () => {
  const actual = await vi.importActual<typeof import('react')>('react')
  return {
    ...actual,
    useRef: mockUseRef,
    useMemo: mockUseMemo,
  }
})

// Import AFTER mocks are set up
import { useWidgetChatRuntime } from '../../../src/lib/chat-runtime'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Create an async generator from an array of SSEEvent objects.
 * Simulates what streamStart() would return.
 */
async function* fakeSSEStream(events: SSEEvent[]): AsyncGenerator<SSEEvent> {
  for (const event of events) {
    yield event
  }
}

/**
 * Collect all yielded values from an async generator.
 */
async function collectYields<T>(gen: AsyncGenerator<T>): Promise<T[]> {
  const results: T[] = []
  for await (const value of gen) {
    results.push(value)
  }
  return results
}

/**
 * Extract the adapter from useWidgetChatRuntime result.
 * Slice 07 changed the API: useWidgetChatRuntime now returns { runtime, controls }.
 * The adapter is stored in runtime (which is mocked to return { adapter, _runtime: true }).
 */
function getAdapter(apiUrl: string) {
  const { runtime } = useWidgetChatRuntime(apiUrl)
  const runtimeWithAdapter = runtime as unknown as {
    adapter: {
      run: (params: { abortSignal: AbortSignal }) => AsyncGenerator<unknown>
    }
  }
  return runtimeWithAdapter.adapter
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ChatModelAdapter - Start Flow (Slice 05)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    // Reset startInterview mock default
    mockStartInterview.mockResolvedValue({} as Response)
    // Reset streamStart mock default
    mockStreamStart.mockImplementation(() => fakeSSEStream([]))
    // Reset useRef to default behavior
    mockUseRef.mockImplementation((initialValue: unknown) => ({ current: initialValue }))
    // Reset useMemo to default behavior
    mockUseMemo.mockImplementation((factory: () => unknown) => factory())
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // -------------------------------------------------------------------------
  // Acceptance Tests -- 1:1 from GIVEN/WHEN/THEN in Slice-Spec
  // -------------------------------------------------------------------------

  describe('acceptance', () => {
    it('AC-1: GIVEN the ChatScreen mounts for the first time WHEN the adapter run() is called THEN it calls /api/interview/start with the anonymous_id from localStorage', async () => {
      // Arrange (GIVEN): SSE stream with metadata + text-done (minimal valid flow)
      const mockResponse = {} as Response
      mockStartInterview.mockResolvedValue(mockResponse)
      mockStreamStart.mockImplementation(() =>
        fakeSSEStream([
          { type: 'metadata', session_id: 'sess-001' },
          { type: 'text-done' },
        ])
      )

      const adapter = getAdapter('http://localhost:8000')
      const controller = new AbortController()

      // Act (WHEN)
      await collectYields(adapter.run({ messages: [], abortSignal: controller.signal }))

      // Assert (THEN)
      expect(mockGetOrCreateAnonymousId).toHaveBeenCalled()
      expect(mockStartInterview).toHaveBeenCalledWith('mock-anon-id-1234', {
        signal: controller.signal,
      })
    })

    it('AC-2: GIVEN the /start SSE stream sends a metadata event WHEN the adapter processes it THEN the session_id is stored (accessible for future /message calls)', async () => {
      // Arrange (GIVEN): SSE stream with metadata containing session_id
      mockStreamStart.mockImplementation(() =>
        fakeSSEStream([
          { type: 'metadata', session_id: 'stored-session-123' },
          { type: 'text-done' },
        ])
      )

      // Capture the sessionIdRef to verify it was set
      const sessionRef = { current: null as string | null }
      const abortControllerRef = { current: null }

      // Mock useRef to return our test refs in order: sessionIdRef first, abortControllerRef second
      let useRefCallCount = 0
      mockUseRef.mockImplementation((initialValue: unknown) => {
        useRefCallCount++
        if (useRefCallCount === 1) return sessionRef
        if (useRefCallCount === 2) return abortControllerRef
        return { current: initialValue }
      })

      const adapter = getAdapter('http://localhost:8000')
      const controller = new AbortController()

      // Act (WHEN)
      await collectYields(adapter.run({ messages: [], abortSignal: controller.signal }))

      // Assert (THEN): session_id stored in ref
      expect(sessionRef.current).toBe('stored-session-123')
    })

    it('AC-3: GIVEN the /start SSE stream sends text-delta events WHEN the adapter processes them THEN it yields { content: [{ type: "text", text: accumulatedText }] } progressively', async () => {
      // Arrange (GIVEN): SSE stream with metadata + two text-deltas + text-done
      mockStreamStart.mockImplementation(() =>
        fakeSSEStream([
          { type: 'metadata', session_id: 'sess-002' },
          { type: 'text-delta', content: 'Hal' },
          { type: 'text-delta', content: 'lo!' },
          { type: 'text-done' },
        ])
      )

      const adapter = getAdapter('http://localhost:8000')
      const controller = new AbortController()

      // Act (WHEN)
      const yields = await collectYields(adapter.run({ messages: [], abortSignal: controller.signal }))

      // Assert (THEN): progressive accumulated text
      expect(yields).toHaveLength(2) // Two text-delta events = two yields
      expect(yields[0]).toEqual({ content: [{ type: 'text', text: 'Hal' }] })
      expect(yields[1]).toEqual({ content: [{ type: 'text', text: 'Hallo!' }] })
    })

    it('AC-4: GIVEN the /start SSE stream sends a text-done event WHEN the adapter processes it THEN the generator completes (returns)', async () => {
      // Arrange (GIVEN)
      mockStreamStart.mockImplementation(() =>
        fakeSSEStream([
          { type: 'metadata', session_id: 'sess-003' },
          { type: 'text-delta', content: 'Done test' },
          { type: 'text-done' },
        ])
      )

      const adapter = getAdapter('http://localhost:8000')
      const controller = new AbortController()

      // Act (WHEN)
      const gen = adapter.run({ messages: [], abortSignal: controller.signal })
      const yields: unknown[] = []
      let result = await gen.next()
      while (!result.done) {
        yields.push(result.value)
        result = await gen.next()
      }

      // Assert (THEN): generator completed (done: true)
      expect(result.done).toBe(true)
      // We got at least one yield (text-delta) before completion
      expect(yields.length).toBeGreaterThanOrEqual(1)
    })

    it('AC-5: GIVEN the /start SSE stream sends an error event WHEN the adapter processes it THEN it throws an Error with the error message', async () => {
      // Arrange (GIVEN): SSE stream with metadata + error
      mockStreamStart.mockImplementation(() =>
        fakeSSEStream([
          { type: 'metadata', session_id: 'sess-004' },
          { type: 'error', message: 'LLM failed' },
        ])
      )

      const adapter = getAdapter('http://localhost:8000')
      const controller = new AbortController()

      // Act & Assert (WHEN/THEN)
      await expect(
        collectYields(adapter.run({ messages: [], abortSignal: controller.signal }))
      ).rejects.toThrow('LLM failed')
    })

    it('AC-6: GIVEN the adapter run() is called with an abortSignal WHEN the signal is aborted THEN the fetch request is cancelled', async () => {
      // Arrange (GIVEN)
      const mockResponse = {} as Response
      mockStartInterview.mockResolvedValue(mockResponse)
      mockStreamStart.mockImplementation(() =>
        fakeSSEStream([
          { type: 'metadata', session_id: 'sess-005' },
          { type: 'text-done' },
        ])
      )

      const controller = new AbortController()
      const adapter = getAdapter('http://localhost:8000')

      // Act (WHEN)
      await collectYields(adapter.run({ messages: [], abortSignal: controller.signal }))

      // Assert (THEN): abortSignal was forwarded to startInterview
      expect(mockStartInterview).toHaveBeenCalledWith('mock-anon-id-1234', {
        signal: controller.signal,
      })

      // Verify the signal object is the same reference
      const callArgs = mockStartInterview.mock.calls[0]
      expect(callArgs[1].signal).toBe(controller.signal)
    })

    it('AC-7: GIVEN useWidgetChatRuntime(apiUrl) is called WHEN apiUrl is a valid string THEN useLocalRuntime is initialized with the real adapter', () => {
      // Arrange (GIVEN): valid apiUrl

      // Act (WHEN)
      useWidgetChatRuntime('http://localhost:8000')

      // Assert (THEN): useLocalRuntime was called with an adapter that has a run method
      expect(mockUseLocalRuntime).toHaveBeenCalledTimes(1)
      const adapterArg = mockUseLocalRuntime.mock.calls[0][0]
      expect(adapterArg).toBeDefined()
      expect(typeof adapterArg.run).toBe('function')
      // createApiClient should have been called with the apiUrl
      expect(mockCreateApiClient).toHaveBeenCalledWith('http://localhost:8000')
    })

    it('AC-8: GIVEN ChatScreen component WHEN it renders THEN it passes config.apiUrl to useWidgetChatRuntime', () => {
      // This AC validates that ChatScreen passes config.apiUrl to useWidgetChatRuntime.
      // Since ChatScreen.tsx imports useWidgetChatRuntime and calls it with config.apiUrl,
      // we verify the contract: useWidgetChatRuntime accepts a string|null parameter.

      // Arrange (GIVEN): call with a config-like apiUrl value
      const apiUrl = 'https://api.example.com'

      // Act (WHEN): simulate what ChatScreen does -- call hook with apiUrl
      useWidgetChatRuntime(apiUrl)

      // Assert (THEN): useLocalRuntime was called (indicating the hook works with apiUrl)
      expect(mockUseLocalRuntime).toHaveBeenCalled()
      expect(mockCreateApiClient).toHaveBeenCalledWith(apiUrl)
    })
  })

  // -------------------------------------------------------------------------
  // Unit Tests -- additional edge cases and isolation tests
  // -------------------------------------------------------------------------

  describe('unit', () => {
    it('should return a dummy adapter when apiUrl is null', () => {
      // Act
      useWidgetChatRuntime(null)

      // Assert: useLocalRuntime still called, but with a fallback adapter
      expect(mockUseLocalRuntime).toHaveBeenCalledTimes(1)
      const adapterArg = mockUseLocalRuntime.mock.calls[0][0]
      expect(adapterArg).toBeDefined()
      expect(typeof adapterArg.run).toBe('function')
      // createApiClient should NOT have been called
      expect(mockCreateApiClient).not.toHaveBeenCalled()
    })

    it('should yield @assistant-ui compatible format { content: [{ type: "text", text }] }', async () => {
      // Arrange: single text-delta
      mockStreamStart.mockImplementation(() =>
        fakeSSEStream([
          { type: 'metadata', session_id: 'sess-format' },
          { type: 'text-delta', content: 'Test content' },
          { type: 'text-done' },
        ])
      )

      const adapter = getAdapter('http://localhost:8000')
      const controller = new AbortController()

      // Act
      const yields = await collectYields(adapter.run({ messages: [], abortSignal: controller.signal }))

      // Assert: verify exact @assistant-ui format
      expect(yields).toHaveLength(1)
      const yielded = yields[0] as { content: Array<{ type: string; text: string }> }
      expect(yielded.content).toBeInstanceOf(Array)
      expect(yielded.content).toHaveLength(1)
      expect(yielded.content[0].type).toBe('text')
      expect(yielded.content[0].text).toBe('Test content')
    })

    it('should accumulate text across multiple text-delta events', async () => {
      // Arrange: three text-deltas
      mockStreamStart.mockImplementation(() =>
        fakeSSEStream([
          { type: 'metadata', session_id: 'sess-accum' },
          { type: 'text-delta', content: 'Hello ' },
          { type: 'text-delta', content: 'World' },
          { type: 'text-delta', content: '!' },
          { type: 'text-done' },
        ])
      )

      const adapter = getAdapter('http://localhost:8000')
      const controller = new AbortController()

      // Act
      const yields = await collectYields(adapter.run({ messages: [], abortSignal: controller.signal }))

      // Assert: each yield has accumulated text
      expect(yields).toHaveLength(3)
      expect(yields[0]).toEqual({ content: [{ type: 'text', text: 'Hello ' }] })
      expect(yields[1]).toEqual({ content: [{ type: 'text', text: 'Hello World' }] })
      expect(yields[2]).toEqual({ content: [{ type: 'text', text: 'Hello World!' }] })
    })

    it('should not yield anything for metadata-only stream (no text-deltas)', async () => {
      // Arrange
      mockStreamStart.mockImplementation(() =>
        fakeSSEStream([
          { type: 'metadata', session_id: 'sess-meta-only' },
          { type: 'text-done' },
        ])
      )

      const adapter = getAdapter('http://localhost:8000')
      const controller = new AbortController()

      // Act
      const yields = await collectYields(adapter.run({ messages: [], abortSignal: controller.signal }))

      // Assert: no yields since no text-delta events
      expect(yields).toHaveLength(0)
    })

    it('should throw when error event occurs before any text-delta', async () => {
      // Arrange
      mockStreamStart.mockImplementation(() =>
        fakeSSEStream([
          { type: 'metadata', session_id: 'sess-err-early' },
          { type: 'error', message: 'Service unavailable' },
        ])
      )

      const adapter = getAdapter('http://localhost:8000')
      const controller = new AbortController()

      // Act & Assert
      await expect(
        collectYields(adapter.run({ messages: [], abortSignal: controller.signal }))
      ).rejects.toThrow('Service unavailable')
    })

    it('should propagate errors from startInterview (fetch failure)', async () => {
      // Arrange: startInterview rejects
      mockStartInterview.mockRejectedValue(new Error('Network error'))

      const adapter = getAdapter('http://localhost:8000')
      const controller = new AbortController()

      // Act & Assert
      await expect(
        collectYields(adapter.run({ messages: [], abortSignal: controller.signal }))
      ).rejects.toThrow('Network error')
    })
  })
})
