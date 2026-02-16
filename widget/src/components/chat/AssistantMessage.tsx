import { MessagePrimitive } from '@assistant-ui/react'

export function AssistantMessage() {
  return (
    <MessagePrimitive.Root className="flex items-start gap-2 py-1">
      {/* Avatar */}
      <div
        className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center"
        aria-hidden="true"
      >
        <span className="text-xs font-medium text-gray-600">A</span>
      </div>

      {/* Message Bubble */}
      <div className="max-w-[80%] bg-gray-100 text-gray-900 rounded-xl px-3 py-2 text-sm leading-relaxed">
        <MessagePrimitive.Parts />
      </div>
    </MessagePrimitive.Root>
  )
}
