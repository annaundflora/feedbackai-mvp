import React, { useReducer } from 'react'
import ReactDOM from 'react-dom/client'
import { parseConfig, findWidgetScript, WidgetConfig } from './config'
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
  runtime
}: {
  screen: WidgetScreen
  config: WidgetConfig
  onAcceptConsent: () => void
  onAutoClose: () => void
  runtime: ReturnType<typeof useWidgetChatRuntime>['runtime']
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
      return <ChatScreen config={config} runtime={runtime} />

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

// Main Widget Component
function Widget({ config }: { config: WidgetConfig }) {
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
          runtime={runtime}
        />
      </Panel>
    </div>
  )
}

// IIFE Entry Point
(function() {
  // Singleton check
  if (document.querySelector('.feedbackai-widget')) {
    console.warn('FeedbackAI Widget already mounted')
    return
  }

  // Find script tag
  const scriptTag = findWidgetScript()
  if (!scriptTag) {
    console.error('FeedbackAI Widget script tag not found')
    return
  }

  // Parse config
  const config = parseConfig(scriptTag)

  // Create container
  const container = document.createElement('div')
  container.className = 'feedbackai-widget-root'
  document.body.appendChild(container)

  // Mount React
  const root = ReactDOM.createRoot(container)
  root.render(
    <React.StrictMode>
      <Widget config={config} />
    </React.StrictMode>
  )

  console.log('FeedbackAI Widget mounted', config)
})()
