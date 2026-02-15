/**
 * Unit Tests for PanelHeader component.
 * Tests title rendering, close button, and accessibility.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { PanelHeader } from '../../src/components/PanelHeader'

describe('unit: PanelHeader', () => {
  it('renders the title with correct id for aria-labelledby', () => {
    const onClose = vi.fn()
    render(<PanelHeader title="Feedback" onClose={onClose} />)

    const heading = screen.getByRole('heading', { level: 2 })
    expect(heading).toHaveTextContent('Feedback')
    expect(heading).toHaveAttribute('id', 'panel-title')
  })

  it('renders a close button with aria-label', () => {
    const onClose = vi.fn()
    render(<PanelHeader title="Test" onClose={onClose} />)

    const closeButton = screen.getByRole('button', { name: /panel schlie/i })
    expect(closeButton).toBeInTheDocument()
    expect(closeButton).toHaveAttribute('aria-label', 'Panel schlie\u00dfen')
  })

  it('calls onClose when close button is clicked', () => {
    const onClose = vi.fn()
    render(<PanelHeader title="Test" onClose={onClose} />)

    const closeButton = screen.getByRole('button', { name: /panel schlie/i })
    fireEvent.click(closeButton)

    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('close button contains XIcon SVG with aria-hidden', () => {
    const onClose = vi.fn()
    render(<PanelHeader title="Test" onClose={onClose} />)

    const closeButton = screen.getByRole('button', { name: /panel schlie/i })
    const svg = closeButton.querySelector('svg')
    expect(svg).not.toBeNull()
    expect(svg).toHaveAttribute('aria-hidden', 'true')
  })

  it('close button has focus-visible ring classes', () => {
    const onClose = vi.fn()
    render(<PanelHeader title="Test" onClose={onClose} />)

    const closeButton = screen.getByRole('button', { name: /panel schlie/i })
    expect(closeButton.className).toContain('focus-visible:ring-2')
  })
})
