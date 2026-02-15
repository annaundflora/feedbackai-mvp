/**
 * Unit Tests for Panel component.
 * Tests rendering, visibility, accessibility attributes, and structure.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Panel } from '../../src/components/Panel'

describe('unit: Panel', () => {
  it('renders nothing when open=false', () => {
    const onClose = vi.fn()
    const { container } = render(
      <Panel open={false} onClose={onClose} title="Test Title">
        <p>Content</p>
      </Panel>
    )

    expect(container.innerHTML).toBe('')
  })

  it('renders panel with dialog role when open=true', () => {
    const onClose = vi.fn()
    render(
      <Panel open={true} onClose={onClose} title="Test Title">
        <p>Content</p>
      </Panel>
    )

    const dialog = screen.getByRole('dialog')
    expect(dialog).toBeInTheDocument()
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(dialog).toHaveAttribute('aria-labelledby', 'panel-title')
  })

  it('renders children content inside the panel', () => {
    const onClose = vi.fn()
    render(
      <Panel open={true} onClose={onClose} title="Test Title">
        <p>My content here</p>
      </Panel>
    )

    expect(screen.getByText('My content here')).toBeInTheDocument()
  })

  it('renders the title via PanelHeader', () => {
    const onClose = vi.fn()
    render(
      <Panel open={true} onClose={onClose} title="Feedback">
        <p>Content</p>
      </Panel>
    )

    expect(screen.getByText('Feedback')).toBeInTheDocument()
    const heading = screen.getByRole('heading', { level: 2 })
    expect(heading).toHaveTextContent('Feedback')
    expect(heading).toHaveAttribute('id', 'panel-title')
  })

  it('has z-index 10000 class (higher than FloatingButton)', () => {
    const onClose = vi.fn()
    render(
      <Panel open={true} onClose={onClose} title="Test">
        <p>Content</p>
      </Panel>
    )

    const dialog = screen.getByRole('dialog')
    expect(dialog.className).toContain('z-[10000]')
  })

  it('has slide-up animation style', () => {
    const onClose = vi.fn()
    render(
      <Panel open={true} onClose={onClose} title="Test">
        <p>Content</p>
      </Panel>
    )

    const dialog = screen.getByRole('dialog')
    expect(dialog.style.animation).toContain('slide-up')
  })

  it('has fixed positioning classes', () => {
    const onClose = vi.fn()
    render(
      <Panel open={true} onClose={onClose} title="Test">
        <p>Content</p>
      </Panel>
    )

    const dialog = screen.getByRole('dialog')
    expect(dialog.className).toContain('fixed')
    expect(dialog.className).toContain('bottom-4')
    expect(dialog.className).toContain('right-4')
  })
})
