/**
 * Unit Tests for PanelBody component.
 * Tests children rendering and overflow behavior.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PanelBody } from '../../src/components/PanelBody'

describe('unit: PanelBody', () => {
  it('renders children content', () => {
    render(
      <PanelBody>
        <p>Screen content here</p>
      </PanelBody>
    )

    expect(screen.getByText('Screen content here')).toBeInTheDocument()
  })

  it('has overflow-y-auto class for scrollable content', () => {
    const { container } = render(
      <PanelBody>
        <p>Content</p>
      </PanelBody>
    )

    const div = container.firstElementChild as HTMLElement
    expect(div.className).toContain('overflow-y-auto')
  })

  it('has flex-1 class for flexible height', () => {
    const { container } = render(
      <PanelBody>
        <p>Content</p>
      </PanelBody>
    )

    const div = container.firstElementChild as HTMLElement
    expect(div.className).toContain('flex-1')
  })
})
