/**
 * Integration Tests for Widget component (FloatingButton + Panel interaction).
 * Tests the full open/close lifecycle with real component composition.
 */
import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React, { useState } from 'react'
import { FloatingButton } from '../../src/components/FloatingButton'
import { Panel } from '../../src/components/Panel'

/**
 * Minimal Widget wrapper that mirrors main.tsx state logic.
 * We recreate the component here rather than importing main.tsx
 * because main.tsx has IIFE side effects.
 */
function TestWidget({ title = 'Feedback' }: { title?: string }) {
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
        title={title}
      >
        <div>
          <h3>Panel Content</h3>
          <p>Screens kommen in Slice 3</p>
        </div>
      </Panel>
    </div>
  )
}

describe('integration: Widget Panel Toggle', () => {
  it('initially shows FloatingButton and hides Panel', () => {
    render(<TestWidget />)

    const button = screen.getByRole('button', { name: 'Feedback geben' })
    expect(button).toBeInTheDocument()

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('clicking FloatingButton opens Panel and hides button', () => {
    render(<TestWidget />)

    const floatingButton = screen.getByRole('button', { name: 'Feedback geben' })
    fireEvent.click(floatingButton)

    // Panel is now open
    const dialog = screen.getByRole('dialog')
    expect(dialog).toBeInTheDocument()

    // FloatingButton is hidden (visible=false renders null)
    expect(screen.queryByRole('button', { name: 'Feedback geben' })).not.toBeInTheDocument()
  })

  it('clicking X-Button in Panel header closes Panel and shows FloatingButton', () => {
    render(<TestWidget />)

    // Open panel first
    fireEvent.click(screen.getByRole('button', { name: 'Feedback geben' }))
    expect(screen.getByRole('dialog')).toBeInTheDocument()

    // Click close button
    const closeButton = screen.getByRole('button', { name: /panel schlie/i })
    fireEvent.click(closeButton)

    // Panel is closed
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    // FloatingButton is visible again
    expect(screen.getByRole('button', { name: 'Feedback geben' })).toBeInTheDocument()
  })

  it('Panel displays the configured title', () => {
    render(<TestWidget title="Mein Feedback" />)

    fireEvent.click(screen.getByRole('button', { name: 'Feedback geben' }))

    const heading = screen.getByRole('heading', { level: 2 })
    expect(heading).toHaveTextContent('Mein Feedback')
  })

  it('Panel renders children content (placeholder for Slice 3)', () => {
    render(<TestWidget />)

    fireEvent.click(screen.getByRole('button', { name: 'Feedback geben' }))

    expect(screen.getByText('Panel Content')).toBeInTheDocument()
    expect(screen.getByText('Screens kommen in Slice 3')).toBeInTheDocument()
  })

  it('can toggle panel open and closed multiple times', () => {
    render(<TestWidget />)

    // Open
    fireEvent.click(screen.getByRole('button', { name: 'Feedback geben' }))
    expect(screen.getByRole('dialog')).toBeInTheDocument()

    // Close
    fireEvent.click(screen.getByRole('button', { name: /panel schlie/i }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    // Open again
    fireEvent.click(screen.getByRole('button', { name: 'Feedback geben' }))
    expect(screen.getByRole('dialog')).toBeInTheDocument()

    // Close again
    fireEvent.click(screen.getByRole('button', { name: /panel schlie/i }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
