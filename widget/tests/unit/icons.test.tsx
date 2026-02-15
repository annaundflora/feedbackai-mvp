/**
 * Unit Tests for Icon components (ChatBubbleIcon, XIcon).
 * Tests SVG rendering, aria-hidden, and className forwarding.
 */
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { ChatBubbleIcon } from '../../src/components/icons/ChatBubbleIcon'
import { XIcon } from '../../src/components/icons/XIcon'

describe('unit: ChatBubbleIcon', () => {
  it('renders an SVG element with aria-hidden=true', () => {
    const { container } = render(<ChatBubbleIcon />)
    const svg = container.querySelector('svg')
    expect(svg).not.toBeNull()
    expect(svg).toHaveAttribute('aria-hidden', 'true')
  })

  it('forwards className prop', () => {
    const { container } = render(<ChatBubbleIcon className="w-6 h-6 text-white" />)
    const svg = container.querySelector('svg')
    // SVG className is an SVGAnimatedString, use getAttribute('class') instead
    const classAttr = svg?.getAttribute('class') ?? ''
    expect(classAttr).toContain('w-6')
    expect(classAttr).toContain('h-6')
  })

  it('uses currentColor for stroke', () => {
    const { container } = render(<ChatBubbleIcon />)
    const svg = container.querySelector('svg')
    expect(svg).toHaveAttribute('stroke', 'currentColor')
  })
})

describe('unit: XIcon', () => {
  it('renders an SVG element with aria-hidden=true', () => {
    const { container } = render(<XIcon />)
    const svg = container.querySelector('svg')
    expect(svg).not.toBeNull()
    expect(svg).toHaveAttribute('aria-hidden', 'true')
  })

  it('forwards className prop', () => {
    const { container } = render(<XIcon className="w-5 h-5 text-gray-500" />)
    const svg = container.querySelector('svg')
    // SVG className is an SVGAnimatedString, use getAttribute('class') instead
    const classAttr = svg?.getAttribute('class') ?? ''
    expect(classAttr).toContain('w-5')
    expect(classAttr).toContain('h-5')
  })

  it('uses currentColor for stroke', () => {
    const { container } = render(<XIcon />)
    const svg = container.querySelector('svg')
    expect(svg).toHaveAttribute('stroke', 'currentColor')
  })
})
