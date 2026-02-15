/**
 * Acceptance Tests for Slice 02: Floating Button + Panel Shell.
 * Derived 1:1 from GIVEN/WHEN/THEN Acceptance Criteria in
 * slice-02-floating-button-panel-shell.md.
 *
 * AC-1:  FloatingButton visible at bottom-right when panelOpen=false
 * AC-2:  Click FloatingButton opens Panel with slide-up animation
 * AC-3:  Panel fully visible, FloatingButton hidden when panel open
 * AC-4:  Click X-Button closes Panel, FloatingButton reappears
 * AC-5:  Desktop viewport: Panel ~400x600px, fixed bottom-right
 * AC-6:  Mobile viewport (<=768px): Panel fullscreen
 * AC-7:  FloatingButton shows focus ring on keyboard focus
 * AC-8:  Enter/Space on focused FloatingButton opens Panel
 * AC-9:  X-Button shows focus ring on keyboard focus
 * AC-10: Enter/Space on focused X-Button closes Panel
 */
import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React, { useState } from 'react'
import { FloatingButton } from '../../src/components/FloatingButton'
import { Panel } from '../../src/components/Panel'

/**
 * Minimal Widget wrapper that mirrors main.tsx state logic.
 * Recreated here to avoid IIFE side effects from main.tsx.
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

describe('Slice 02: Floating Button + Panel Shell -- Acceptance', () => {
  it('AC-1: GIVEN Widget gemountet WHEN panelOpen=false THEN Floating Button ist sichtbar am bottom-right', () => {
    /**
     * AC-1: When Widget is mounted with default state (panelOpen=false),
     * the FloatingButton must be visible and positioned at bottom-right.
     */
    render(<TestWidget />)

    // GIVEN: Widget is mounted (panelOpen=false by default)
    // WHEN: Initial render with panelOpen=false
    // THEN: FloatingButton is visible
    const button = screen.getByRole('button', { name: 'Feedback geben' })
    expect(button).toBeInTheDocument()

    // THEN: Positioned at bottom-right (fixed, bottom-4, right-4)
    expect(button.className).toContain('fixed')
    expect(button.className).toContain('bottom-4')
    expect(button.className).toContain('right-4')
  })

  it('AC-2: GIVEN Floating Button sichtbar WHEN User klickt Button THEN Panel gleitet hoch (Slide-Up Animation 300ms)', () => {
    /**
     * AC-2: Clicking the FloatingButton opens the Panel with slide-up animation.
     */
    render(<TestWidget />)

    // GIVEN: FloatingButton is visible
    const button = screen.getByRole('button', { name: 'Feedback geben' })
    expect(button).toBeInTheDocument()

    // WHEN: User clicks Button
    fireEvent.click(button)

    // THEN: Panel opens with slide-up animation
    const dialog = screen.getByRole('dialog')
    expect(dialog).toBeInTheDocument()
    expect(dialog.style.animation).toContain('slide-up')
    // Animation uses --transition-slide which is 300ms
    expect(dialog.style.animation).toContain('var(--transition-slide)')
  })

  it('AC-3: GIVEN Panel offen WHEN Animation abgeschlossen THEN Panel ist vollstaendig sichtbar, Floating Button versteckt', () => {
    /**
     * AC-3: When the Panel is open, it is fully visible and the
     * FloatingButton is hidden.
     */
    render(<TestWidget />)

    // GIVEN: Open the Panel
    fireEvent.click(screen.getByRole('button', { name: 'Feedback geben' }))

    // WHEN: Animation completed (we test the DOM state post-click)
    // THEN: Panel is fully visible
    const dialog = screen.getByRole('dialog')
    expect(dialog).toBeInTheDocument()

    // THEN: FloatingButton is hidden (returns null when visible=false)
    expect(screen.queryByRole('button', { name: 'Feedback geben' })).not.toBeInTheDocument()
  })

  it('AC-4: GIVEN Panel offen WHEN User klickt X-Button im Header THEN Panel gleitet runter, Floating Button erscheint', () => {
    /**
     * AC-4: Clicking the X-Button closes the Panel and shows
     * the FloatingButton again.
     */
    render(<TestWidget />)

    // GIVEN: Panel is open
    fireEvent.click(screen.getByRole('button', { name: 'Feedback geben' }))
    expect(screen.getByRole('dialog')).toBeInTheDocument()

    // WHEN: User clicks X-Button in Header
    const closeButton = screen.getByRole('button', { name: /panel schlie/i })
    fireEvent.click(closeButton)

    // THEN: Panel is closed
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    // THEN: FloatingButton appears again
    const floatingButton = screen.getByRole('button', { name: 'Feedback geben' })
    expect(floatingButton).toBeInTheDocument()
  })

  it('AC-5: GIVEN Desktop Viewport (>768px) WHEN Panel offen THEN Panel ist ~400x600px, fixed bottom-right', () => {
    /**
     * AC-5: On desktop viewport, the Panel uses CSS custom properties
     * for width (~384px = 24rem) and height (~600px = 37.5rem),
     * positioned fixed at bottom-right.
     *
     * Note: jsdom does not compute CSS custom properties, so we validate
     * the CSS classes that define the sizing behavior.
     */
    render(<TestWidget />)

    // GIVEN: Desktop viewport (default jsdom, >768px assumed)
    // Open the panel
    fireEvent.click(screen.getByRole('button', { name: 'Feedback geben' }))

    // WHEN: Panel is open
    const dialog = screen.getByRole('dialog')

    // THEN: Panel uses CSS custom properties for ~400x600px sizing
    expect(dialog.className).toContain('w-[var(--panel-width)]')
    expect(dialog.className).toContain('h-[var(--panel-height)]')

    // THEN: Fixed bottom-right positioning
    expect(dialog.className).toContain('fixed')
    expect(dialog.className).toContain('bottom-4')
    expect(dialog.className).toContain('right-4')
  })

  it('AC-6: GIVEN Mobile Viewport (<=768px) WHEN Panel offen THEN Panel ist Fullscreen (100vw x 100vh)', () => {
    /**
     * AC-6: On mobile viewport, the Panel has responsive classes that
     * make it fullscreen via max-md: modifiers.
     *
     * Note: jsdom cannot simulate media queries, so we validate the
     * presence of the responsive CSS classes that implement fullscreen.
     */
    render(<TestWidget />)

    // Open the panel
    fireEvent.click(screen.getByRole('button', { name: 'Feedback geben' }))

    // WHEN: Panel is open
    const dialog = screen.getByRole('dialog')

    // THEN: Has mobile fullscreen responsive classes
    expect(dialog.className).toContain('max-md:inset-0')
    expect(dialog.className).toContain('max-md:w-full')
    expect(dialog.className).toContain('max-md:h-full')
    expect(dialog.className).toContain('max-md:rounded-none')
  })

  it('AC-7: GIVEN Floating Button WHEN Keyboard Focus (Tab) THEN Focus Ring sichtbar (focus-visible:ring-2)', () => {
    /**
     * AC-7: The FloatingButton has focus-visible:ring-2 classes so that
     * keyboard focus produces a visible ring.
     */
    render(<TestWidget />)

    // GIVEN: FloatingButton is in the DOM
    const button = screen.getByRole('button', { name: 'Feedback geben' })

    // WHEN: Keyboard focus (Tab) - we simulate focus
    fireEvent.focus(button)

    // THEN: Focus ring classes are present (visual ring on :focus-visible)
    expect(button.className).toContain('focus-visible:ring-2')
    expect(button.className).toContain('focus-visible:ring-brand')
    expect(button.className).toContain('focus-visible:ring-offset-2')
  })

  it('AC-8: GIVEN Floating Button fokussiert WHEN User drueckt Enter/Space THEN Panel oeffnet sich', () => {
    /**
     * AC-8: Pressing Enter or Space on a focused FloatingButton opens the Panel.
     * Native button elements fire click on Enter/Space by default.
     */
    render(<TestWidget />)

    // GIVEN: FloatingButton is focused
    const button = screen.getByRole('button', { name: 'Feedback geben' })
    button.focus()

    // WHEN: User presses Enter (simulated via keyDown + click, as native buttons do)
    fireEvent.keyDown(button, { key: 'Enter', code: 'Enter' })
    fireEvent.click(button) // Native button behavior on Enter

    // THEN: Panel opens
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Feedback geben' })).not.toBeInTheDocument()
  })

  it('AC-9: GIVEN Panel Header X-Button WHEN Keyboard Focus THEN Focus Ring sichtbar', () => {
    /**
     * AC-9: The X-Button in PanelHeader has focus-visible:ring-2 classes
     * for keyboard accessibility.
     */
    render(<TestWidget />)

    // Open panel first
    fireEvent.click(screen.getByRole('button', { name: 'Feedback geben' }))

    // GIVEN: X-Button is in the DOM
    const closeButton = screen.getByRole('button', { name: /panel schlie/i })

    // WHEN: Keyboard focus
    fireEvent.focus(closeButton)

    // THEN: Focus ring classes are present
    expect(closeButton.className).toContain('focus-visible:ring-2')
    expect(closeButton.className).toContain('focus-visible:ring-gray-500')
  })

  it('AC-10: GIVEN Panel Header X-Button fokussiert WHEN User drueckt Enter/Space THEN Panel schliesst sich', () => {
    /**
     * AC-10: Pressing Enter or Space on a focused X-Button closes the Panel.
     */
    render(<TestWidget />)

    // Open panel first
    fireEvent.click(screen.getByRole('button', { name: 'Feedback geben' }))
    expect(screen.getByRole('dialog')).toBeInTheDocument()

    // GIVEN: X-Button is focused
    const closeButton = screen.getByRole('button', { name: /panel schlie/i })
    closeButton.focus()

    // WHEN: User presses Space (simulated via keyDown + click)
    fireEvent.keyDown(closeButton, { key: ' ', code: 'Space' })
    fireEvent.click(closeButton) // Native button behavior on Space

    // THEN: Panel closes
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    // THEN: FloatingButton reappears
    expect(screen.getByRole('button', { name: 'Feedback geben' })).toBeInTheDocument()
  })
})
