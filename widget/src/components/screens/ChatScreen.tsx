import { useThreadRuntime } from '@assistant-ui/react'
import { useState, useEffect, Suspense } from 'react'
import type { InterviewControls } from '../../lib/chat-runtime'
import { ChatThread } from '../chat/ChatThread'
import { ChatComposer } from '../chat/ChatComposer'
import { ErrorDisplay } from '../chat/ErrorDisplay'
import { classifyError } from '../../lib/error-utils'
import type { WidgetConfig } from '../../config'

interface ChatScreenProps {
  config: WidgetConfig
  controls: InterviewControls
  onRestart: () => void
  onRedirectToThankYou: () => void
}

function ChatScreenInner({ config, controls, onRestart, onRedirectToThankYou }: ChatScreenProps) {
  const threadRuntime = useThreadRuntime()
  const [error, setError] = useState<{ message: string; action: 'retry' | 'restart' | 'redirect_thankyou' | 'none'; rawError: unknown } | null>(null)

  // Monitor thread for errors
  useEffect(() => {
    const unsubscribe = threadRuntime.subscribe(() => {
      const state = threadRuntime.getState()
      const messages = state.messages
      const lastMessage = messages[messages.length - 1]

      // Check if last message has error (status.type === 'incomplete' && status.reason === 'error')
      if (
        lastMessage?.role === 'assistant' &&
        lastMessage.status?.type === 'incomplete' &&
        lastMessage.status.reason === 'error'
      ) {
        const rawError = lastMessage.status.error
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
      } else if (
        error &&
        !(lastMessage?.status?.type === 'incomplete' && lastMessage.status.reason === 'error')
      ) {
        // Clear error if last message is not an error
        setError(null)
      }
    })

    return unsubscribe
  }, [threadRuntime, error, onRedirectToThankYou])

  const handleRetry = () => {
    setError(null)
    // Trigger retry by canceling and restarting the current message
    const state = threadRuntime.getState()
    const lastMessage = state.messages[state.messages.length - 1]
    threadRuntime.cancelRun()
    threadRuntime.startRun({ parentId: lastMessage?.id || null })
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

export function ChatScreen({ config, controls, onRestart, onRedirectToThankYou }: ChatScreenProps) {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-[feedbackai-pulse_1.5s_ease-in-out_infinite] text-gray-500">
            Lädt...
          </div>
        </div>
      </div>
    }>
      <ChatScreenInner
        config={config}
        controls={controls}
        onRestart={onRestart}
        onRedirectToThankYou={onRedirectToThankYou}
      />
    </Suspense>
  )
}
