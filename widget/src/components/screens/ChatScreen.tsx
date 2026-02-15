import React from 'react'
import { AssistantRuntimeProvider } from '@assistant-ui/react'
import { useWidgetChatRuntime } from '../../lib/chat-runtime'
import { ChatThread } from '../chat/ChatThread'
import { ChatComposer } from '../chat/ChatComposer'
import type { WidgetConfig } from '../../config'

interface ChatScreenProps {
  config: WidgetConfig
}

export function ChatScreen({ config }: ChatScreenProps) {
  const runtime = useWidgetChatRuntime()

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <div className="flex flex-col h-full">
        {/* Thread Area */}
        <div className="flex-1 overflow-y-auto chat-thread">
          <ChatThread />
        </div>

        {/* Composer Area */}
        <div className="border-t border-gray-200">
          <ChatComposer placeholder={config.texts.composerPlaceholder} />
        </div>
      </div>
    </AssistantRuntimeProvider>
  )
}
