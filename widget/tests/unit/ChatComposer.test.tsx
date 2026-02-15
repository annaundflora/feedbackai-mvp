/**
 * Unit Tests for ChatComposer component.
 *
 * Tests the composer input field and send button with mocked @assistant-ui primitives.
 * Verifies placeholder text, aria labels, and structural correctness.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

// Mock @assistant-ui/react primitives
vi.mock('@assistant-ui/react', () => ({
  ComposerPrimitive: {
    Root: ({ children, className }: { children: React.ReactNode; className?: string }) => (
      <form data-testid="composer-root" className={className}>
        {children}
      </form>
    ),
    Input: (props: React.TextareaHTMLAttributes<HTMLTextAreaElement> & { rows?: number }) => (
      <textarea
        data-testid="composer-input"
        placeholder={props.placeholder}
        className={props.className}
        rows={props.rows}
        autoFocus={props.autoFocus}
        aria-label={props['aria-label'] || 'Composer input'}
      />
    ),
    Send: ({ children, className, ...rest }: React.ButtonHTMLAttributes<HTMLButtonElement> & { children: React.ReactNode }) => (
      <button
        data-testid="composer-send"
        type="submit"
        className={className}
        aria-label={rest['aria-label']}
      >
        {children}
      </button>
    ),
  },
}))

import { ChatComposer } from '../../src/components/chat/ChatComposer'

describe('unit: ChatComposer', () => {
  it('renders with default placeholder text', () => {
    render(<ChatComposer />)

    const input = screen.getByTestId('composer-input')
    expect(input).toHaveAttribute('placeholder', 'Nachricht eingeben...')
  })

  it('accepts custom placeholder prop', () => {
    render(<ChatComposer placeholder="Type a message..." />)

    const input = screen.getByTestId('composer-input')
    expect(input).toHaveAttribute('placeholder', 'Type a message...')
  })

  it('send button has aria-label "Nachricht senden"', () => {
    render(<ChatComposer />)

    const sendButton = screen.getByTestId('composer-send')
    expect(sendButton).toHaveAttribute('aria-label', 'Nachricht senden')
  })

  it('send button contains an SVG icon', () => {
    const { container } = render(<ChatComposer />)

    const sendButton = screen.getByTestId('composer-send')
    const svg = sendButton.querySelector('svg')
    expect(svg).not.toBeNull()
    expect(svg?.getAttribute('aria-hidden')).toBe('true')
  })

  it('input has autoFocus set to false (no auto-focus in Phase 2)', () => {
    render(<ChatComposer />)

    const input = screen.getByTestId('composer-input')
    // autoFocus should be false for mobile UX
    expect(input).not.toHaveAttribute('autofocus')
  })

  it('input has rows=1 for single-line initial height', () => {
    render(<ChatComposer />)

    const input = screen.getByTestId('composer-input')
    expect(input).toHaveAttribute('rows', '1')
  })

  it('send button has focus-visible ring classes for keyboard navigation', () => {
    render(<ChatComposer />)

    const sendButton = screen.getByTestId('composer-send')
    expect(sendButton.className).toContain('focus-visible:ring-2')
  })

  it('send button has touch-action-manipulation for mobile', () => {
    render(<ChatComposer />)

    const sendButton = screen.getByTestId('composer-send')
    expect(sendButton.className).toContain('touch-action-manipulation')
  })

  it('send button has minimum 40px size (w-10 h-10) for touch targets', () => {
    render(<ChatComposer />)

    const sendButton = screen.getByTestId('composer-send')
    // w-10 = 2.5rem = 40px, h-10 = 2.5rem = 40px
    expect(sendButton.className).toContain('w-10')
    expect(sendButton.className).toContain('h-10')
  })
})
