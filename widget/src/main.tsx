import React, { useState } from 'react'
import ReactDOM from 'react-dom/client'
import { parseConfig, findWidgetScript } from './config'
import { FloatingButton } from './components/FloatingButton'
import { Panel } from './components/Panel'
import './styles/widget.css'

function Widget({ config }: { config: ReturnType<typeof parseConfig> }) {
  const [panelOpen, setPanelOpen] = useState(false)

  return (
    <div className="feedbackai-widget">
      <FloatingButton
        onClick={() => setPanelOpen(true)}
        visible={!panelOpen}
      />
      <Panel
        open={panelOpen}
        onClose={() => setPanelOpen(false)}
        title={config.texts.panelTitle}
      >
        {/* Placeholder Content - Slice 3 wird Screens hier einsetzen */}
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Panel Content
            </h3>
            <p className="text-sm text-gray-600">
              Screens kommen in Slice 3
            </p>
          </div>
        </div>
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
