import { useLocalRuntime } from '@assistant-ui/react'
import type { ChatModelAdapter } from '@assistant-ui/react'

/**
 * Dummy Chat Model Adapter für Phase 2
 *
 * In Phase 2 gibt es kein Backend. Der Adapter returned nichts.
 * In Phase 3 wird dieser Adapter ersetzt durch einen, der SSE-Backend aufruft.
 */
const dummyChatModelAdapter: ChatModelAdapter = {
  async *run({ messages, abortSignal }) {
    // Phase 2: Keine Antwort
    // User kann tippen, aber es kommt keine Response

    // In Phase 3: Hier würde SSE-Call zum Backend stattfinden
    // yield { type: 'text-delta', textDelta: '...' }

    // Dummy: Return nothing
    return
  }
}

/**
 * Custom Hook für Widget Chat Runtime
 *
 * Verwendet useLocalRuntime mit Dummy-Adapter in Phase 2.
 * In Phase 3: Adapter wird ersetzt, Hook-Interface bleibt gleich.
 */
export function useWidgetChatRuntime() {
  return useLocalRuntime(dummyChatModelAdapter)
}
