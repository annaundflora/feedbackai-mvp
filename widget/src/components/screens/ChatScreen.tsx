import { AssistantRuntimeProvider, useThreadRuntime } from '@assistant-ui/react'
import { useState, useEffect } from 'react'
import type { useWidgetChatRuntime } from '../../lib/chat-runtime'
import { ChatThread } from '../chat/ChatThread'
import { ChatComposer } from '../chat/ChatComposer'
import { ErrorDisplay } from '../chat/ErrorDisplay'
import { classifyError } from '../../lib/error-utils'
import type { WidgetConfig } from '../../config'

interface ChatScreenProps {
  config: WidgetConfig
  runtime: ReturnType<typeof useWidgetChatRuntime>['runtime']
  controls: ReturnType<typeof useWidgetChatRuntime>['controls']
  onRestart: () => void
  onRedirectToThankYou: () => void
}

function ChatScreenInner({ config, controls, onRestart, onRedirectToThankYou }: Omit<ChatScreenProps, 'runtime'>) {
  const threadRuntime = useThreadRuntime()
  const [error, setError] = useState<{ message: string; action: 'retry' | 'restart' | 'redirect_thankyou' | 'none'; rawError: unknown } | null>(null)

  // Monitor thread for errors
  useEffect(() => {
    const unsubscribe = threadRuntime.subscribe(() => {
      const messages = threadRuntime.messages
      const lastMessage = messages[messages.length - 1]

      // Check if last message has error
      if (lastMessage?.role === 'assistant' && lastMessage.status?.type === 'error') {
        const rawError = (lastMessage.status as any).error
        const classified = classifyError(rawError)

        // Handle 409 (session completed) -> auto-redirect to ThankYou
        if (classified.action === 'redirect_thankyou') {
          onRedirectToThankYou()
          return
        }

        setError({
          message: classified.message,
          action: classified.action,
          rawError
        })
      } else if (error && lastMessage?.status?.type !== 'error') {
        // Clear error if last message is not an error
        setError(null)
      }
    })

    return unsubscribe
  }, [threadRuntime, error, onRedirectToThankYou])

  const handleRetry = () => {
    setError(null)
    // Trigger retry by canceling and restarting the current message
    threadRuntime.cancelRun()
    threadRuntime.startRun()
  }

  const handleRestart = async () => {
    setError(null)
    // End interview and restart
    await controls.endInterview()
    onRestart()
  }

  return (
    <div className="flex flex-col h-full">
      {/* Thread Area */}
      <div className="flex-1 overflow-y-auto chat-thread">
        <ChatThread />
        {error && (
          <ErrorDisplay
            message={error.message}
            action={error.action}
            onRetry={error.action === 'retry' ? handleRetry : undefined}
            onRestart={error.action === 'restart' ? handleRestart : undefined}
          />
        )}
      </div>

      {/* Composer Area */}
      <div className="border-t border-gray-200">
        <ChatComposer placeholder={config.texts.composerPlaceholder} disabled={!!error} />
      </div>
    </div>
  )
}

export function ChatScreen({ config, runtime, controls, onRestart, onRedirectToThankYou }: ChatScreenProps) {
  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <ChatScreenInner
        config={config}
        controls={controls}
        onRestart={onRestart}
        onRedirectToThankYou={onRedirectToThankYou}
      />
    </AssistantRuntimeProvider>
  )
}
