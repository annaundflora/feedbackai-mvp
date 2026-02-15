import React from 'react'
import { MessagePrimitive } from '@assistant-ui/react'

export function ChatMessage() {
  return (
    <MessagePrimitive.If user>
      <div className="flex gap-3 chat-message justify-end mb-4">
        {/* User Message Bubble */}
        <div className="max-w-[80%] rounded-2xl px-4 py-2.5 bg-brand text-white">
          <MessagePrimitive.Content
            components={{
              Text: ({ part }) => (
                <p className="text-sm leading-relaxed whitespace-pre-wrap">
                  {part.text}
                </p>
              )
            }}
          />
        </div>
      </div>
    </MessagePrimitive.If>
  )
}
