/**
 * Test exports for E2E integration tests.
 * Exports Widget component and related utilities for testing.
 */
import React, { useReducer } from 'react'
import type { WidgetConfig } from './config'
import { FloatingButton } from './components/FloatingButton'
import { Panel } from './components/Panel'
import { ConsentScreen } from './components/screens/ConsentScreen'
import { ChatScreen } from './components/screens/ChatScreen'
import { ThankYouScreen } from './components/screens/ThankYouScreen'
import { widgetReducer, initialState, WidgetScreen } from './reducer'
import { useWidgetChatRuntime } from './lib/chat-runtime'
import './styles/widget.css'

// Screen Router Component
function ScreenRouter({
  screen,
  config,
  onAcceptConsent,
  onAutoClose,
  onRestart,
  onRedirectToThankYou,
  runtime,
  controls
}: {
  screen: WidgetScreen
  config: WidgetConfig
  onAcceptConsent: () => void
  onAutoClose: () => void
  onRestart: () => void
  onRedirectToThankYou: () => void
  runtime: ReturnType<typeof useWidgetChatRuntime>['runtime']
  controls: ReturnType<typeof useWidgetChatRuntime>['controls']
}) {
  switch (screen) {
    case 'consent':
      return (
        <ConsentScreen
          headline={config.texts.consentHeadline}
          body={config.texts.consentBody}
          ctaLabel={config.texts.consentCta}
          onAccept={onAcceptConsent}
        />
      )

    case 'chat':
      return (
        <ChatScreen
          config={config}
          runtime={runtime}
          controls={controls}
          onRestart={onRestart}
          onRedirectToThankYou={onRedirectToThankYou}
        />
      )

    case 'thankyou':
      return (
        <ThankYouScreen
          headline={config.texts.thankYouHeadline}
          body={config.texts.thankYouBody}
          onAutoClose={onAutoClose}
        />
      )

    default:
      return null
  }
}

// Main Widget Component (exported for tests)
export function Widget({ config }: { config: WidgetConfig }) {
  const [state, dispatch] = useReducer(widgetReducer, initialState)
  const { runtime, controls } = useWidgetChatRuntime(config.apiUrl)

  const handleOpenPanel = () => dispatch({ type: 'OPEN_PANEL' })

  const handleClosePanel = async () => {
    if (controls.hasActiveSession()) {
      await controls.endInterview()
      dispatch({ type: 'GO_TO_THANKYOU' })
    } else {
      dispatch({ type: 'CLOSE_PANEL' })
    }
  }

  const handleAcceptConsent = () => dispatch({ type: 'GO_TO_CHAT' })
  const handleAutoClose = () => dispatch({ type: 'CLOSE_AND_RESET' })
  const handleRestart = () => dispatch({ type: 'CLOSE_AND_RESET' })
  const handleRedirectToThankYou = () => dispatch({ type: 'GO_TO_THANKYOU' })

  return (
    <div className="feedbackai-widget">
      <FloatingButton
        onClick={handleOpenPanel}
        visible={!state.panelOpen}
      />
      <Panel
        open={state.panelOpen}
        onClose={handleClosePanel}
        title={config.texts.panelTitle}
      >
        <ScreenRouter
          screen={state.screen}
          config={config}
          onAcceptConsent={handleAcceptConsent}
          onAutoClose={handleAutoClose}
          onRestart={handleRestart}
          onRedirectToThankYou={handleRedirectToThankYou}
          runtime={runtime}
          controls={controls}
        />
      </Panel>
    </div>
  )
}
