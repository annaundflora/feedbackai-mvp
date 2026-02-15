/**
 * Unit Tests for FloatingButton component.
 * Tests rendering, visibility, click handling, and accessibility attributes.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { FloatingButton } from '../../src/components/FloatingButton'

describe('unit: FloatingButton', () => {
  it('renders a button with aria-label when visible=true', () => {
    const onClick = vi.fn()
    render(<FloatingButton onClick={onClick} visible={true} />)

    const button = screen.getByRole('button', { name: 'Feedback geben' })
    expect(button).toBeInTheDocument()
    expect(button).toHaveAttribute('aria-label', 'Feedback geben')
  })

  it('renders nothing when visible=false', () => {
    const onClick = vi.fn()
    const { container } = render(<FloatingButton onClick={onClick} visible={false} />)

    expect(container.innerHTML).toBe('')
  })

  it('calls onClick when clicked', () => {
    const onClick = vi.fn()
    render(<FloatingButton onClick={onClick} visible={true} />)

    const button = screen.getByRole('button', { name: 'Feedback geben' })
    fireEvent.click(button)

    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('contains an SVG icon (ChatBubbleIcon) with aria-hidden', () => {
    const onClick = vi.fn()
    render(<FloatingButton onClick={onClick} visible={true} />)

    const button = screen.getByRole('button', { name: 'Feedback geben' })
    const svg = button.querySelector('svg')
    expect(svg).not.toBeNull()
    expect(svg).toHaveAttribute('aria-hidden', 'true')
  })

  it('has fixed positioning classes for bottom-right placement', () => {
    const onClick = vi.fn()
    render(<FloatingButton onClick={onClick} visible={true} />)

    const button = screen.getByRole('button', { name: 'Feedback geben' })
    expect(button.className).toContain('fixed')
    expect(button.className).toContain('bottom-4')
    expect(button.className).toContain('right-4')
  })

  it('has z-index 9999 class', () => {
    const onClick = vi.fn()
    render(<FloatingButton onClick={onClick} visible={true} />)

    const button = screen.getByRole('button', { name: 'Feedback geben' })
    expect(button.className).toContain('z-[9999]')
  })

  it('has focus-visible ring classes for keyboard accessibility', () => {
    const onClick = vi.fn()
    render(<FloatingButton onClick={onClick} visible={true} />)

    const button = screen.getByRole('button', { name: 'Feedback geben' })
    expect(button.className).toContain('focus-visible:ring-2')
  })
})
