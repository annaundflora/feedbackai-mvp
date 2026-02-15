import React from 'react'
import ReactDOM from 'react-dom/client'
import { parseConfig, findWidgetScript } from './config'
import './styles/widget.css'

// Placeholder Widget Component (Slice 2 wird echte UI bauen)
function Widget({ config }: { config: ReturnType<typeof parseConfig> }) {
  return (
    <div className="feedbackai-widget">
      <div className="p-4 bg-white rounded shadow">
        <h2>FeedbackAI Widget</h2>
        <p>Language: {config.lang}</p>
        <p>API URL: {config.apiUrl || 'Not set'}</p>
      </div>
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
