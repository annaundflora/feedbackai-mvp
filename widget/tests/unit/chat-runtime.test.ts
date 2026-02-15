/**
 * Unit Tests for chat-runtime module.
 *
 * Tests the dummy ChatModelAdapter and useWidgetChatRuntime hook
 * in isolation, verifying Phase 2 behavior (no backend responses).
 */
import { describe, it, expect, vi } from 'vitest'

// Mock @assistant-ui/react to isolate the runtime logic
vi.mock('@assistant-ui/react', () => ({
  useLocalRuntime: vi.fn((adapter: unknown) => ({
    _adapter: adapter,
    _type: 'mocked-local-runtime',
  })),
}))

describe('unit: chat-runtime', () => {
  it('useWidgetChatRuntime calls useLocalRuntime with the dummy adapter', async () => {
    const { useLocalRuntime } = await import('@assistant-ui/react')
    const { useWidgetChatRuntime } = await import('../../src/lib/chat-runtime')

    // The module-level call to useLocalRuntime happens at import time
    // but since it's a hook, it is called when useWidgetChatRuntime is invoked.
    // We need to verify the adapter is passed through.

    // Call the hook (mocked, so no React context needed)
    const result = useWidgetChatRuntime()

    expect(useLocalRuntime).toHaveBeenCalledTimes(1)
    expect(result).toBeDefined()
    // The mocked useLocalRuntime returns our mock shape
    expect((result as Record<string, unknown>)._type).toBe('mocked-local-runtime')
  })

  it('dummy adapter is an async generator that yields nothing', async () => {
    const { useLocalRuntime } = await import('@assistant-ui/react')
    const mockedUseLocalRuntime = vi.mocked(useLocalRuntime)

    // Get the adapter that was passed to useLocalRuntime
    const adapterArg = mockedUseLocalRuntime.mock.calls[0]?.[0] as {
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
    const { useLocalRuntime } = await import('@assistant-ui/react')
    const mockedUseLocalRuntime = vi.mocked(useLocalRuntime)

    const adapterArg = mockedUseLocalRuntime.mock.calls[0]?.[0] as {
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
