/**
 * Unit Tests for chat-runtime module.
 *
 * Tests the dummy ChatModelAdapter and useWidgetChatRuntime hook
 * in isolation, verifying Phase 2 behavior (no backend responses).
 */
import { describe, it, expect, vi } from 'vitest'
import { renderHook } from '@testing-library/react'

// Track the adapter passed to useLocalRuntime
let capturedAdapter: unknown = null

// Mock @assistant-ui/react to isolate the runtime logic
vi.mock('@assistant-ui/react', () => ({
  useLocalRuntime: vi.fn((adapter: unknown) => {
    capturedAdapter = adapter
    return {
      _adapter: adapter,
      _type: 'mocked-local-runtime',
    }
  }),
}))

describe('unit: chat-runtime', () => {
  it('useWidgetChatRuntime calls useLocalRuntime with the dummy adapter', async () => {
    const { useLocalRuntime } = await import('@assistant-ui/react')
    const { useWidgetChatRuntime } = await import('../../src/lib/chat-runtime')

    const { result } = renderHook(() => useWidgetChatRuntime(null))

    expect(useLocalRuntime).toHaveBeenCalled()
    expect(result.current).toBeDefined()
    expect((result.current.runtime as Record<string, unknown>)._type).toBe('mocked-local-runtime')
  })

  it('dummy adapter is an async generator that yields nothing', async () => {
    const adapterArg = capturedAdapter as {
      run: (params: { messages: unknown[]; abortSignal: AbortSignal }) => AsyncGenerator
    }
    expect(adapterArg).toBeDefined()
    expect(typeof adapterArg.run).toBe('function')

    // Run the adapter -- it should return immediately with no yields
    const controller = new AbortController()
    const generator = adapterArg.run({
      messages: [{ role: 'user', content: [{ type: 'text', text: 'Hello' }] }],
      abortSignal: controller.signal,
    })

    // Collect all yielded values
    const yielded: unknown[] = []
    for await (const value of generator) {
      yielded.push(value)
    }

    // Dummy adapter should yield nothing (Phase 2: no backend)
    expect(yielded).toHaveLength(0)
  })

  it('dummy adapter does not throw on abort signal', async () => {
    const adapterArg = capturedAdapter as {
      run: (params: { messages: unknown[]; abortSignal: AbortSignal }) => AsyncGenerator
    }

    const controller = new AbortController()
    controller.abort() // Already aborted

    // Should not throw even with aborted signal
    const generator = adapterArg.run({
      messages: [],
      abortSignal: controller.signal,
    })

    const yielded: unknown[] = []
    for await (const value of generator) {
      yielded.push(value)
    }

    expect(yielded).toHaveLength(0)
  })
})
