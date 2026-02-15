/**
 * Acceptance + Unit Tests for Slice 06: Implement ChatModelAdapter for Message Flow.
 * Derived from GIVEN/WHEN/THEN Acceptance Criteria in the Slice-Spec.
 *
 * Slice-Spec: specs/phase-3/2026-02-15-backend-widget-integration/slices/slice-06-adapter-message-flow.md
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { SSEEvent } from '../../../src/lib/types'
import { ApiError } from '../../../src/lib/types'

// ---------------------------------------------------------------------------
// Hoisted mocks -- vi.hoisted() ensures variables are available in vi.mock()
// ---------------------------------------------------------------------------

const {
  mockStartInterview,
  mockSendMessage,
  mockStreamStart,
  mockStreamMessage,
  mockUseLocalRuntime,
  mockCreateApiClient,
  mockGetOrCreateAnonymousId,
  mockUseRef,
  mockUseMemo,
} = vi.hoisted(() => {
  const mockStartInterview = vi.fn()
  const mockSendMessage = vi.fn()
  const mockStreamStart = vi.fn()
  const mockStreamMessage = vi.fn()
  const mockUseLocalRuntime = vi.fn((adapter: unknown) => ({ adapter, _runtime: true }))
  const mockCreateApiClient = vi.fn(() => ({
    startInterview: mockStartInterview,
    sendMessage: mockSendMessage,
    endInterview: vi.fn(),
  }))
  const mockGetOrCreateAnonymousId = vi.fn(() => 'mock-anon-id-1234')
  const mockUseRef = vi.fn((initialValue: unknown) => ({ current: initialValue }))
  const mockUseMemo = vi.fn((factory: () => unknown) => factory())

  return {
    mockStartInterview,
    mockSendMessage,
    mockStreamStart,
    mockStreamMessage,
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
  streamMessage: mockStreamMessage,
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
 * Simulates what streamMessage() would return.
 */
async function* fakeSSEStream(events: SSEEvent[]): AsyncGenerator<SSEEvent> {
  for (const event of events) {
    yield event
  }
}

/**
 * Create an async generator that throws an ApiError.
 * Simulates streamMessage() throwing on non-ok response.
 */
async function* fakeErrorStream(error: ApiError): AsyncGenerator<SSEEvent> {
  throw error
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
 * Build a messages array in @assistant-ui format.
 * Each message has role and content array with text parts.
 */
function buildMessages(
  ...msgs: Array<{ role: 'user' | 'assistant'; text: string }>
) {
  return msgs.map(m => ({
    role: m.role,
    content: [{ type: 'text' as const, text: m.text }],
  }))
}

/**
 * Extract the adapter from useWidgetChatRuntime result.
 * Slice 07 changed the API: useWidgetChatRuntime now returns { runtime, controls }.
 * The adapter is stored in runtime (which is mocked to return { adapter, _runtime: true }).
 */
function getAdapterWithSession(apiUrl: string, sessionId: string) {
  // Set sessionIdRef.current to a session_id so the MESSAGE flow branch is taken
  const sessionRef = { current: sessionId }
  const abortControllerRef = { current: null }

  // Mock useRef to return our test refs in order: sessionIdRef first, abortControllerRef second
  let useRefCallCount = 0
  mockUseRef.mockImplementation((initialValue: unknown) => {
    useRefCallCount++
    if (useRefCallCount === 1) return sessionRef
    if (useRefCallCount === 2) return abortControllerRef
    return { current: initialValue }
  })

  const { runtime } = useWidgetChatRuntime(apiUrl)
  const runtimeWithAdapter = runtime as unknown as {
    adapter: {
      run: (params: {
        messages: Array<{ role: string; content: Array<{ type: string; text: string }> }>
        abortSignal: AbortSignal
      }) => AsyncGenerator<unknown>
    }
  }
  return { adapter: runtimeWithAdapter.adapter, sessionRef }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ChatModelAdapter - Message Flow (Slice 06)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset sendMessage mock default
    mockSendMessage.mockResolvedValue({} as Response)
    // Reset streamMessage mock default
    mockStreamMessage.mockImplementation(() => fakeSSEStream([]))
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
    it('AC-1: GIVEN a session_id exists (from previous /start) WHEN the adapter run() is called with user messages THEN it calls /api/interview/message with the session_id and last user message text', async () => {
      // Arrange (GIVEN): session exists, mock sendMessage and streamMessage
      const mockResponse = {} as Response
      mockSendMessage.mockResolvedValue(mockResponse)
      mockStreamMessage.mockImplementation(() =>
        fakeSSEStream([
          { type: 'text-delta', content: 'Response' },
          { type: 'text-done' },
        ])
      )

      const messages = buildMessages(
        { role: 'assistant', text: 'Welcome!' },
        { role: 'user', text: 'My feedback' }
      )

      const { adapter } = getAdapterWithSession('http://localhost:8000', 'session-123')
      const controller = new AbortController()

      // Act (WHEN)
      await collectYields(adapter.run({ messages, abortSignal: controller.signal }))

      // Assert (THEN): sendMessage called with session_id and last user message
      expect(mockSendMessage).toHaveBeenCalledWith(
        'session-123',
        'My feedback',
        { signal: controller.signal }
      )
    })

    it('AC-2: GIVEN the /message SSE stream sends text-delta events WHEN the adapter processes them THEN it yields { content: [{ type: "text", text: accumulatedText }] } progressively', async () => {
      // Arrange (GIVEN): SSE stream with two text-deltas
      mockStreamMessage.mockImplementation(() =>
        fakeSSEStream([
          { type: 'text-delta', content: 'Das ' },
          { type: 'text-delta', content: 'freut mich' },
          { type: 'text-done' },
        ])
      )

      const messages = buildMessages(
        { role: 'assistant', text: 'Wie geht es?' },
        { role: 'user', text: 'Gut!' }
      )

      const { adapter } = getAdapterWithSession('http://localhost:8000', 'session-abc')
      const controller = new AbortController()

      // Act (WHEN)
      const yields = await collectYields(adapter.run({ messages, abortSignal: controller.signal }))

      // Assert (THEN): progressive accumulated text
      expect(yields).toHaveLength(2)
      expect(yields[0]).toEqual({ content: [{ type: 'text', text: 'Das ' }] })
      expect(yields[1]).toEqual({ content: [{ type: 'text', text: 'Das freut mich' }] })
    })

    it('AC-3: GIVEN the /message SSE stream sends a text-done event WHEN the adapter processes it THEN the generator completes', async () => {
      // Arrange (GIVEN)
      mockStreamMessage.mockImplementation(() =>
        fakeSSEStream([
          { type: 'text-delta', content: 'Done test' },
          { type: 'text-done' },
        ])
      )

      const messages = buildMessages(
        { role: 'user', text: 'Test message' }
      )

      const { adapter } = getAdapterWithSession('http://localhost:8000', 'session-done')
      const controller = new AbortController()

      // Act (WHEN)
      const gen = adapter.run({ messages, abortSignal: controller.signal })
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

    it('AC-4: GIVEN the /message SSE stream sends an error event WHEN the adapter processes it THEN it throws an Error with the error message', async () => {
      // Arrange (GIVEN): SSE stream with error event
      mockStreamMessage.mockImplementation(() =>
        fakeSSEStream([
          { type: 'error', message: 'LLM processing failed' },
        ])
      )

      const messages = buildMessages(
        { role: 'user', text: 'Something' }
      )

      const { adapter } = getAdapterWithSession('http://localhost:8000', 'session-err')
      const controller = new AbortController()

      // Act & Assert (WHEN/THEN)
      await expect(
        collectYields(adapter.run({ messages, abortSignal: controller.signal }))
      ).rejects.toThrow('LLM processing failed')
    })

    it('AC-5: GIVEN the adapter receives a 404 error (session expired) WHEN processing the response THEN it throws an Error that can be caught by error handling', async () => {
      // Arrange (GIVEN): streamMessage throws ApiError with status 404
      mockStreamMessage.mockImplementation(() =>
        fakeErrorStream(new ApiError('Session not found', 404))
      )

      const messages = buildMessages(
        { role: 'user', text: 'Hello again' }
      )

      const { adapter } = getAdapterWithSession('http://localhost:8000', 'session-expired')
      const controller = new AbortController()

      // Act & Assert (WHEN/THEN)
      await expect(
        collectYields(adapter.run({ messages, abortSignal: controller.signal }))
      ).rejects.toThrow('Session not found')

      try {
        await collectYields(adapter.run({ messages, abortSignal: controller.signal }))
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError)
        expect((err as ApiError).status).toBe(404)
      }
    })

    it('AC-6: GIVEN the adapter receives a 409 error (session completed) WHEN processing the response THEN it throws an Error that can be caught by error handling', async () => {
      // Arrange (GIVEN): streamMessage throws ApiError with status 409
      mockStreamMessage.mockImplementation(() =>
        fakeErrorStream(new ApiError('Session already completed', 409))
      )

      const messages = buildMessages(
        { role: 'user', text: 'One more' }
      )

      const { adapter } = getAdapterWithSession('http://localhost:8000', 'session-completed')
      const controller = new AbortController()

      // Act & Assert (WHEN/THEN)
      await expect(
        collectYields(adapter.run({ messages, abortSignal: controller.signal }))
      ).rejects.toThrow('Session already completed')

      try {
        await collectYields(adapter.run({ messages, abortSignal: controller.signal }))
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError)
        expect((err as ApiError).status).toBe(409)
      }
    })

    it('AC-7: GIVEN the adapter run() is called with an abortSignal WHEN the signal is aborted THEN the fetch request is cancelled', async () => {
      // Arrange (GIVEN)
      mockStreamMessage.mockImplementation(() =>
        fakeSSEStream([
          { type: 'text-delta', content: 'Partial' },
          { type: 'text-done' },
        ])
      )

      const messages = buildMessages(
        { role: 'user', text: 'Cancel me' }
      )

      const controller = new AbortController()
      const { adapter } = getAdapterWithSession('http://localhost:8000', 'session-abort')

      // Act (WHEN)
      await collectYields(adapter.run({ messages, abortSignal: controller.signal }))

      // Assert (THEN): abortSignal was forwarded to sendMessage
      expect(mockSendMessage).toHaveBeenCalledWith(
        'session-abort',
        'Cancel me',
        { signal: controller.signal }
      )

      // Verify the signal object is the same reference
      const callArgs = mockSendMessage.mock.calls[0]
      expect(callArgs[2].signal).toBe(controller.signal)
    })
  })

  // -------------------------------------------------------------------------
  // Unit Tests -- additional edge cases and isolation tests
  // -------------------------------------------------------------------------

  describe('unit', () => {
    it('should extract only the last user message from a multi-message array', async () => {
      // Arrange: multiple user messages in the conversation
      mockStreamMessage.mockImplementation(() =>
        fakeSSEStream([
          { type: 'text-delta', content: 'OK' },
          { type: 'text-done' },
        ])
      )

      const messages = buildMessages(
        { role: 'user', text: 'First question' },
        { role: 'assistant', text: 'First answer' },
        { role: 'user', text: 'Second question' },
        { role: 'assistant', text: 'Second answer' },
        { role: 'user', text: 'Third question - the latest' }
      )

      const { adapter } = getAdapterWithSession('http://localhost:8000', 'session-multi')
      const controller = new AbortController()

      // Act
      await collectYields(adapter.run({ messages, abortSignal: controller.signal }))

      // Assert: only the last user message text was sent
      expect(mockSendMessage).toHaveBeenCalledWith(
        'session-multi',
        'Third question - the latest',
        expect.any(Object)
      )
    })

    it('should not call sendMessage when no user message exists in messages array', async () => {
      // Arrange: only assistant messages
      const messages = buildMessages(
        { role: 'assistant', text: 'Welcome!' }
      )

      const { adapter } = getAdapterWithSession('http://localhost:8000', 'session-no-user')
      const controller = new AbortController()

      // Act
      const yields = await collectYields(adapter.run({ messages, abortSignal: controller.signal }))

      // Assert: no sendMessage call, no yields
      expect(mockSendMessage).not.toHaveBeenCalled()
      expect(yields).toHaveLength(0)
    })

    it('should accumulate text across multiple text-delta events in message flow', async () => {
      // Arrange: three text-deltas
      mockStreamMessage.mockImplementation(() =>
        fakeSSEStream([
          { type: 'text-delta', content: 'Hello ' },
          { type: 'text-delta', content: 'World' },
          { type: 'text-delta', content: '!' },
          { type: 'text-done' },
        ])
      )

      const messages = buildMessages(
        { role: 'user', text: 'Hi' }
      )

      const { adapter } = getAdapterWithSession('http://localhost:8000', 'session-accum')
      const controller = new AbortController()

      // Act
      const yields = await collectYields(adapter.run({ messages, abortSignal: controller.signal }))

      // Assert: each yield has accumulated text
      expect(yields).toHaveLength(3)
      expect(yields[0]).toEqual({ content: [{ type: 'text', text: 'Hello ' }] })
      expect(yields[1]).toEqual({ content: [{ type: 'text', text: 'Hello World' }] })
      expect(yields[2]).toEqual({ content: [{ type: 'text', text: 'Hello World!' }] })
    })

    it('should propagate errors from sendMessage (fetch failure)', async () => {
      // Arrange: sendMessage rejects
      mockSendMessage.mockRejectedValue(new Error('Network error'))

      const messages = buildMessages(
        { role: 'user', text: 'Try this' }
      )

      const { adapter } = getAdapterWithSession('http://localhost:8000', 'session-net-err')
      const controller = new AbortController()

      // Act & Assert
      await expect(
        collectYields(adapter.run({ messages, abortSignal: controller.signal }))
      ).rejects.toThrow('Network error')
    })

    it('should call streamMessage with the response from sendMessage', async () => {
      // Arrange
      const mockResponse = { body: 'fake-body' } as unknown as Response
      mockSendMessage.mockResolvedValue(mockResponse)
      mockStreamMessage.mockImplementation(() =>
        fakeSSEStream([{ type: 'text-done' }])
      )

      const messages = buildMessages(
        { role: 'user', text: 'Check response passing' }
      )

      const { adapter } = getAdapterWithSession('http://localhost:8000', 'session-resp')
      const controller = new AbortController()

      // Act
      await collectYields(adapter.run({ messages, abortSignal: controller.signal }))

      // Assert: streamMessage was called with the response from sendMessage
      expect(mockStreamMessage).toHaveBeenCalledWith(mockResponse)
    })
  })
})
