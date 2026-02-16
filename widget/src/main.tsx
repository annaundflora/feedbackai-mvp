import React, { useReducer, useContext, createContext, Suspense } from 'react'
import ReactDOM from 'react-dom/client'
import { AssistantRuntimeProvider } from '@assistant-ui/react'
import { parseConfig, findWidgetScript, WidgetConfig } from './config'
import { FloatingButton } from './components/FloatingButton'
import { Panel } from './components/Panel'
import { ConsentScreen } from './components/screens/ConsentScreen'
import { ChatScreen } from './components/screens/ChatScreen'
import { ThankYouScreen } from './components/screens/ThankYouScreen'
import { widgetReducer, initialState, WidgetScreen } from './reducer'
import { useWidgetChatRuntime, InterviewControls } from './lib/chat-runtime'
import './styles/widget.css'

// Context to pass controls from RuntimeProvider to WidgetContent
const ControlsContext = createContext<InterviewControls | null>(null)

/**
 * RuntimeProvider isolates useLocalRuntime from state-driven re-renders.
 *
 * The infinite re-render bug (React Error #185) was fixed in @assistant-ui/react
 * v0.8.4. This separation remains as a best practice — keeping the runtime
 * provider above state-driven components prevents unnecessary hook re-fires.
 */
function RuntimeProvider({
  apiUrl,
  children
}: {
  apiUrl: string | null
  children: React.ReactNode
}) {
  const { runtime, controls } = useWidgetChatRuntime(apiUrl)

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <ControlsContext.Provider value={controls}>
        {children}
      </ControlsContext.Provider>
    </AssistantRuntimeProvider>
  )
}

// Screen Router Component
function ScreenRouter({
  screen,
  config,
  onAcceptConsent,
  onAutoClose,
  onRestart,
  onRedirectToThankYou,
  controls
}: {
  screen: WidgetScreen
  config: WidgetConfig
  onAcceptConsent: () => void
  onAutoClose: () => void
  onRestart: () => void
  onRedirectToThankYou: () => void
  controls: InterviewControls
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

/**
 * WidgetContent holds all state (useReducer) and UI.
 * Re-renders from dispatch do NOT propagate to RuntimeProvider above.
 */
function WidgetContent({ config }: { config: WidgetConfig }) {
  const [state, dispatch] = useReducer(widgetReducer, initialState)
  const controls = useContext(ControlsContext)!

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
          controls={controls}
        />
      </Panel>
    </div>
  )
}

// Main Widget Component
function Widget({ config }: { config: WidgetConfig }) {
  return (
    <RuntimeProvider apiUrl={config.apiUrl}>
      <WidgetContent config={config} />
    </RuntimeProvider>
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
      <Suspense fallback={
        <div className="feedbackai-widget">
          <div style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            width: '56px',
            height: '56px',
            borderRadius: '50%',
            backgroundColor: '#3b82f6',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            opacity: 0.6
          }}>
            <div style={{
              width: '24px',
              height: '24px',
              border: '3px solid white',
              borderTopColor: 'transparent',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite'
            }} />
          </div>
        </div>
      }>
        <Widget config={config} />
      </Suspense>
    </React.StrictMode>
  )

  console.log('FeedbackAI Widget mounted', config)
})()
