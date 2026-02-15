/**
 * Integration Tests for Screen Components and ScreenRouter.
 *
 * Tests ConsentScreen, ChatScreen, ThankYouScreen rendering,
 * ThankYouScreen auto-close timer with cleanup, and component interactions.
 *
 * Derived from Slice-03 Acceptance Criteria:
 *   AC-1 (ConsentScreen display), AC-2 (CTA click), AC-5 (auto-close timer),
 *   AC-6 (timer fires and resets), AC-9 (reduced motion - CSS only, not testable here)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, cleanup, act } from '@testing-library/react'
import React from 'react'
import { ConsentScreen } from '../../src/components/screens/ConsentScreen'
import { ChatScreen } from '../../src/components/screens/ChatScreen'
import { ThankYouScreen } from '../../src/components/screens/ThankYouScreen'

describe('integration: ConsentScreen', () => {
  const defaultProps = {
    headline: 'Ihr Feedback zaehlt!',
    body: 'Wir moechten Ihnen ein paar kurze Fragen stellen.',
    ctaLabel: "Los geht's",
    onAccept: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
  })

  it('should render headline, body, and CTA button', () => {
    render(<ConsentScreen {...defaultProps} />)

    expect(screen.getByText(defaultProps.headline)).toBeInTheDocument()
    expect(screen.getByText(defaultProps.body)).toBeInTheDocument()
    expect(screen.getByText(defaultProps.ctaLabel)).toBeInTheDocument()
  })

  it('should render headline as h2 element', () => {
    render(<ConsentScreen {...defaultProps} />)
    const heading = screen.getByRole('heading', { level: 2 })
    expect(heading).toHaveTextContent(defaultProps.headline)
  })

  it('should call onAccept when CTA button is clicked', () => {
    render(<ConsentScreen {...defaultProps} />)
    const button = screen.getByText(defaultProps.ctaLabel)
    fireEvent.click(button)
    expect(defaultProps.onAccept).toHaveBeenCalledTimes(1)
  })

  it('should render CTA as a button element', () => {
    render(<ConsentScreen {...defaultProps} />)
    const button = screen.getByRole('button')
    expect(button).toHaveTextContent(defaultProps.ctaLabel)
  })
})

describe('integration: ChatScreen', () => {
  const mockConfig = {
    apiUrl: null,
    lang: 'de',
    texts: {
      panelTitle: 'Feedback',
      consentHeadline: 'Ihr Feedback zaehlt!',
      consentBody: 'Wir moechten Ihnen ein paar kurze Fragen stellen.',
      consentCta: "Los geht's",
      thankYouHeadline: 'Vielen Dank!',
      thankYouBody: 'Ihr Feedback hilft uns, besser zu werden.',
      composerPlaceholder: 'Nachricht eingeben...',
    },
  }

  afterEach(() => {
    cleanup()
  })

  it('should render placeholder text "Chat bereit"', () => {
    render(<ChatScreen config={mockConfig} />)
    expect(screen.getByText('Bereit für Ihr Feedback')).toBeInTheDocument()
  })

  it('should render composer placeholder', () => {
    render(<ChatScreen config={mockConfig} />)
    expect(screen.getByPlaceholderText('Nachricht eingeben...')).toBeInTheDocument()
  })

  it('should render chat icon with aria-hidden', () => {
    render(<ChatScreen config={mockConfig} />)
    const svgs = document.querySelectorAll('svg[aria-hidden="true"]')
    expect(svgs.length).toBeGreaterThan(0)
  })
})

describe('integration: ThankYouScreen', () => {
  const defaultProps = {
    headline: 'Vielen Dank!',
    body: 'Ihr Feedback hilft uns, besser zu werden.',
    onAutoClose: vi.fn(),
  }

  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
  })

  it('should render headline, body, and auto-close hint', () => {
    render(<ThankYouScreen {...defaultProps} />)

    expect(screen.getByText(defaultProps.headline)).toBeInTheDocument()
    expect(screen.getByText(defaultProps.body)).toBeInTheDocument()
    expect(
      screen.getByText(/schlie.*automatisch/i)
    ).toBeInTheDocument()
  })

  it('should render headline as h2 element', () => {
    render(<ThankYouScreen {...defaultProps} />)
    const heading = screen.getByRole('heading', { level: 2 })
    expect(heading).toHaveTextContent(defaultProps.headline)
  })

  it('should render success icon with aria-hidden', () => {
    render(<ThankYouScreen {...defaultProps} />)
    const svgs = document.querySelectorAll('svg[aria-hidden="true"]')
    expect(svgs.length).toBeGreaterThan(0)
  })

  it('should call onAutoClose after default 5000ms delay', () => {
    render(<ThankYouScreen {...defaultProps} />)

    expect(defaultProps.onAutoClose).not.toHaveBeenCalled()

    act(() => {
      vi.advanceTimersByTime(5000)
    })

    expect(defaultProps.onAutoClose).toHaveBeenCalledTimes(1)
  })

  it('should NOT call onAutoClose before 5000ms', () => {
    render(<ThankYouScreen {...defaultProps} />)

    act(() => {
      vi.advanceTimersByTime(4999)
    })

    expect(defaultProps.onAutoClose).not.toHaveBeenCalled()
  })

  it('should use custom autoCloseDelay when provided', () => {
    render(<ThankYouScreen {...defaultProps} autoCloseDelay={2000} />)

    act(() => {
      vi.advanceTimersByTime(2000)
    })

    expect(defaultProps.onAutoClose).toHaveBeenCalledTimes(1)
  })

  it('should cleanup timer on unmount (no memory leak)', () => {
    const { unmount } = render(<ThankYouScreen {...defaultProps} />)

    // Unmount before timer fires
    unmount()

    act(() => {
      vi.advanceTimersByTime(5000)
    })

    // onAutoClose should NOT be called after unmount
    expect(defaultProps.onAutoClose).not.toHaveBeenCalled()
  })

  it('should cleanup timer when component re-renders with new delay', () => {
    const { rerender } = render(
      <ThankYouScreen {...defaultProps} autoCloseDelay={5000} />
    )

    // Advance partway
    act(() => {
      vi.advanceTimersByTime(3000)
    })

    // Re-render with new delay
    rerender(<ThankYouScreen {...defaultProps} autoCloseDelay={2000} />)

    // Old timer should be cleared; new timer starts
    act(() => {
      vi.advanceTimersByTime(2000)
    })

    expect(defaultProps.onAutoClose).toHaveBeenCalledTimes(1)
  })
})
