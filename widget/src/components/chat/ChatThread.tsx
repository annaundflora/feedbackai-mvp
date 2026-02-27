import { ThreadPrimitive } from '@assistant-ui/react'
import { useThread } from '@assistant-ui/react'
import { ChatMessage } from './ChatMessage'
import { AssistantMessage } from './AssistantMessage'
import { LoadingIndicator } from './LoadingIndicator'
import { TypingIndicator } from './TypingIndicator'

export function ChatThread() {
  const { isRunning, messages } = useThread()

  // Show LoadingIndicator when running and no messages yet (initial connect)
  const showLoadingIndicator = isRunning && messages.length === 0

  // Show TypingIndicator when running and messages exist (assistant is responding)
  const showTypingIndicator = isRunning && messages.length > 0

  return (
    <ThreadPrimitive.Root className="h-full">
      {/* Welcome/Empty State */}
      <ThreadPrimitive.Empty>
        {showLoadingIndicator ? (
          <LoadingIndicator />
        ) : (
          <div className="flex flex-col items-center justify-center h-full px-6 py-8">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="w-8 h-8 text-gray-400"
                  aria-hidden="true"
                >
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
              </div>
              <h3 className="text-base font-medium text-gray-900 mb-1">
                Bereit für Ihr Feedback
              </h3>
              <p className="text-sm text-gray-500">
                Stellen Sie Ihre Frage oder teilen Sie uns Ihre Gedanken mit.
              </p>
            </div>
          </div>
        )}
      </ThreadPrimitive.Empty>

      {/* Message List — Viewport MUST be the scroll container for auto-scroll to work.
           assistant-ui's useThreadViewportAutoScroll calls div.scrollTo() on this element. */}
      <ThreadPrimitive.Viewport className="h-full overflow-y-auto chat-thread px-4 py-2">
        <ThreadPrimitive.Messages components={{ UserMessage: ChatMessage, AssistantMessage: AssistantMessage }} />
        {showTypingIndicator && <TypingIndicator />}
      </ThreadPrimitive.Viewport>
    </ThreadPrimitive.Root>
  )
}
