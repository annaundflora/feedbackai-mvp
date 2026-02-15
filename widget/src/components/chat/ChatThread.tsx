import { ThreadPrimitive } from '@assistant-ui/react'
import { ChatMessage } from './ChatMessage'

export function ChatThread() {
  return (
    <ThreadPrimitive.Root className="h-full">
      {/* Welcome/Empty State */}
      <ThreadPrimitive.Empty>
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
      </ThreadPrimitive.Empty>

      {/* Message List */}
      <ThreadPrimitive.Viewport className="px-4 py-2">
        <ThreadPrimitive.Messages components={{ UserMessage: ChatMessage, AssistantMessage: ChatMessage }} />
      </ThreadPrimitive.Viewport>
    </ThreadPrimitive.Root>
  )
}
