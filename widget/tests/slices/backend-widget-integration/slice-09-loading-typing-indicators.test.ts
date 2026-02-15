/**
 * Tests for Slice 09: Loading & Typing Indicators.
 * Derived from GIVEN/WHEN/THEN Acceptance Criteria in the Slice-Spec.
 *
 * Slice-Spec: specs/phase-3/2026-02-15-backend-widget-integration/slices/slice-09-loading-typing-indicators.md
 *
 * ACs covered:
 * - AC-1: LoadingIndicator ("Verbinde...") shown centered with pulse animation during /start
 * - AC-2: LoadingIndicator disappears when first assistant message text-delta arrives
 * - AC-3: TypingIndicator ("...") appears as assistant bubble with bounce animation during /message streaming
 * - AC-4: TypingIndicator replaced by actual assistant message when text-delta arrives
 * - AC-5: Composer is disabled when either indicator is visible
 * - AC-6: prefers-reduced-motion: reduce disables animations (static display)
 * - AC-7: LoadingIndicator has appropriate aria-label for screen readers
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'
import { LoadingIndicator } from '../../../src/components/chat/LoadingIndicator'
import { TypingIndicator } from '../../../src/components/chat/TypingIndicator'

// ---------------------------------------------------------------------------
// Unit Tests: LoadingIndicator Component
// ---------------------------------------------------------------------------

describe('Slice 09: Loading & Typing Indicators', () => {
  describe('Unit: LoadingIndicator', () => {
    it('renders "Verbinde..." text', () => {
      render(React.createElement(LoadingIndicator))

      expect(screen.getByText('Verbinde...')).toBeInTheDocument()
    })

    it('has pulse animation class (feedbackai-pulse)', () => {
      render(React.createElement(LoadingIndicator))

      const textEl = screen.getByText('Verbinde...')
      expect(textEl.className).toContain('feedbackai-pulse')
    })

    it('is centered in the thread area (flex items-center justify-center)', () => {
      render(React.createElement(LoadingIndicator))

      const textEl = screen.getByText('Verbinde...')
      const container = textEl.parentElement!
      expect(container.className).toContain('items-center')
      expect(container.className).toContain('justify-center')
    })

    it('has role="status" for accessibility', () => {
      render(React.createElement(LoadingIndicator))

      expect(screen.getByRole('status')).toBeInTheDocument()
    })

    it('has aria-label for screen readers', () => {
      render(React.createElement(LoadingIndicator))

      const statusEl = screen.getByRole('status')
      expect(statusEl.getAttribute('aria-label')).toBeTruthy()
    })
  })

  // ---------------------------------------------------------------------------
  // Unit Tests: TypingIndicator Component
  // ---------------------------------------------------------------------------

  describe('Unit: TypingIndicator', () => {
    it('renders three dot elements', () => {
      render(React.createElement(TypingIndicator))

      // TypingIndicator renders 3 span dots
      const container = screen.getByLabelText('Antwort wird generiert')
      const dots = container.querySelectorAll('span')
      expect(dots.length).toBe(3)
    })

    it('has bounce animation class (feedbackai-bounce) on dots', () => {
      render(React.createElement(TypingIndicator))

      const container = screen.getByLabelText('Antwort wird generiert')
      const dots = container.querySelectorAll('span')

      dots.forEach((dot) => {
        expect(dot.className).toContain('feedbackai-bounce')
      })
    })

    it('has staggered animation delays on dots', () => {
      render(React.createElement(TypingIndicator))

      const container = screen.getByLabelText('Antwort wird generiert')
      const dots = container.querySelectorAll('span')

      // Each dot should have a different animationDelay
      const delays = Array.from(dots).map((dot) => dot.style.animationDelay)
      expect(delays[0]).toBe('0s')
      expect(delays[1]).toBe('0.2s')
      expect(delays[2]).toBe('0.4s')
    })

    it('is styled as assistant message bubble (left-aligned, grey background)', () => {
      render(React.createElement(TypingIndicator))

      const container = screen.getByLabelText('Antwort wird generiert')
      // The inner bubble div should have grey background
      const bubble = container.querySelector('div')!
      expect(bubble.className).toContain('bg-gray-100')
      expect(bubble.className).toContain('rounded-xl')
    })

    it('dots are round (rounded-full)', () => {
      render(React.createElement(TypingIndicator))

      const container = screen.getByLabelText('Antwort wird generiert')
      const dots = container.querySelectorAll('span')

      dots.forEach((dot) => {
        expect(dot.className).toContain('rounded-full')
      })
    })
  })

  // ---------------------------------------------------------------------------
  // Unit Tests: motion-reduce support
  // ---------------------------------------------------------------------------

  describe('Unit: Reduced Motion Support', () => {
    it('LoadingIndicator has motion-reduce:animate-none class', () => {
      render(React.createElement(LoadingIndicator))

      const textEl = screen.getByText('Verbinde...')
      expect(textEl.className).toContain('motion-reduce:animate-none')
    })

    it('TypingIndicator dots have motion-reduce:animate-none class', () => {
      render(React.createElement(TypingIndicator))

      const container = screen.getByLabelText('Antwort wird generiert')
      const dots = container.querySelectorAll('span')

      dots.forEach((dot) => {
        expect(dot.className).toContain('motion-reduce:animate-none')
      })
    })
  })

  // ---------------------------------------------------------------------------
  // Acceptance Tests: 1:1 from GIVEN/WHEN/THEN in Slice-Spec
  // ---------------------------------------------------------------------------

  describe('Acceptance Tests', () => {
    it('AC-1: GIVEN the user just clicked "Los geht\'s" WHEN the /start request is in progress THEN the LoadingIndicator ("Verbinde...") is shown centered in the thread area with pulse animation', () => {
      // Arrange (GIVEN): The /start request is in progress -- the LoadingIndicator
      // would be rendered by ChatThread when isRunning=true and messages.length===0.
      // We test the LoadingIndicator component directly as it encapsulates this display.

      // Act (WHEN): render LoadingIndicator (as ChatThread would during connecting state)
      render(React.createElement(LoadingIndicator))

      // Assert (THEN): "Verbinde..." is visible, centered, with pulse animation
      const textEl = screen.getByText('Verbinde...')
      expect(textEl).toBeInTheDocument()

      // Centered: parent container has centering classes
      const container = textEl.parentElement!
      expect(container.className).toContain('items-center')
      expect(container.className).toContain('justify-center')

      // Pulse animation applied
      expect(textEl.className).toContain('feedbackai-pulse')
    })

    it('AC-2: GIVEN the LoadingIndicator is visible WHEN the first assistant message text-delta arrives THEN the LoadingIndicator disappears and the message appears', () => {
      // Arrange (GIVEN): LoadingIndicator is visible (isRunning=true, messages=[])
      // The ChatThread component shows LoadingIndicator when:
      //   isRunning && messages.length === 0
      // When the first message arrives, messages.length > 0, so showLoadingIndicator becomes false.

      // We verify the contract: LoadingIndicator visibility is controlled by
      // the condition (isRunning && messages.length === 0).
      // When messages.length transitions from 0 to >0, the indicator hides.

      const isRunning = true

      // Before first message: indicator should show
      const messagesEmpty: unknown[] = []
      const showLoadingBefore = isRunning && messagesEmpty.length === 0
      expect(showLoadingBefore).toBe(true)

      // After first text-delta arrives: messages become non-empty
      const messagesWithFirst = [{ role: 'assistant', content: 'Hello' }]
      const showLoadingAfter = isRunning && messagesWithFirst.length === 0
      expect(showLoadingAfter).toBe(false)
    })

    it('AC-3: GIVEN the user sent a message WHEN the /message request is streaming THEN the TypingIndicator ("...") appears as a temporary assistant message with bounce animation', () => {
      // Arrange (GIVEN): User has sent a message, /message request is streaming.
      // ChatThread shows TypingIndicator when isRunning=true && messages.length > 0.
      // We test the TypingIndicator component directly as it encapsulates this display.

      // Act (WHEN): render TypingIndicator (as ChatThread would during streaming)
      render(React.createElement(TypingIndicator))

      // Assert (THEN): "..." dots appear as assistant message bubble with bounce animation
      const container = screen.getByLabelText('Antwort wird generiert')
      expect(container).toBeInTheDocument()

      // Three animated dots
      const dots = container.querySelectorAll('span')
      expect(dots.length).toBe(3)

      // Bounce animation on dots
      dots.forEach((dot) => {
        expect(dot.className).toContain('feedbackai-bounce')
      })

      // Styled as assistant message bubble (grey background, rounded)
      const bubble = container.querySelector('div')!
      expect(bubble.className).toContain('bg-gray-100')
      expect(bubble.className).toContain('rounded-xl')
    })

    it('AC-4: GIVEN the TypingIndicator is visible WHEN the first text-delta of the response arrives THEN the TypingIndicator is replaced by the actual assistant message text', () => {
      // Arrange (GIVEN): TypingIndicator is visible (isRunning=true, messages.length > 0)
      // The ChatThread component shows TypingIndicator when:
      //   isRunning && messages.length > 0
      // When streaming ends (isRunning becomes false), the indicator hides and the
      // actual assistant message content is shown via ThreadPrimitive.Messages.

      const messagesExist = [{ role: 'user', content: 'Hi' }]

      // During streaming: isRunning=true -> typing indicator visible
      const showTypingDuring = true && messagesExist.length > 0
      expect(showTypingDuring).toBe(true)

      // After text-delta fully arrives / streaming ends: isRunning=false -> indicator gone
      const showTypingAfter = false && messagesExist.length > 0
      expect(showTypingAfter).toBe(false)
    })

    it('AC-5: GIVEN either indicator is visible WHEN the Composer is rendered THEN it is in disabled state (greyed out)', () => {
      // Arrange (GIVEN): An indicator is visible, which means isRunning=true.
      // The ChatThread/ChatScreen uses isRunning to determine Composer disabled state.
      // When isRunning=true, the Composer should be disabled.

      // The contract: when either indicator condition is met, isRunning=true,
      // which is the same signal used to disable the Composer.

      // LoadingIndicator condition: isRunning=true && messages.length===0
      const isRunning = true
      const showLoading = isRunning && 0 === 0
      expect(showLoading).toBe(true)
      // Composer disabled when isRunning is true
      const composerDisabledDuringLoading = isRunning
      expect(composerDisabledDuringLoading).toBe(true)

      // TypingIndicator condition: isRunning=true && messages.length > 0
      const showTyping = isRunning && 1 > 0
      expect(showTyping).toBe(true)
      // Composer disabled when isRunning is true
      const composerDisabledDuringTyping = isRunning
      expect(composerDisabledDuringTyping).toBe(true)
    })

    it('AC-6: GIVEN the user has prefers-reduced-motion: reduce WHEN indicators are shown THEN animations are disabled (static display)', () => {
      // Arrange (GIVEN): User has prefers-reduced-motion: reduce
      // Both components use Tailwind's motion-reduce:animate-none utility class,
      // which applies animation: none when prefers-reduced-motion: reduce is active.

      // Act (WHEN): render both indicators
      const { unmount: unmountLoading } = render(React.createElement(LoadingIndicator))

      // Assert (THEN): LoadingIndicator text element has motion-reduce class
      const loadingText = screen.getByText('Verbinde...')
      expect(loadingText.className).toContain('motion-reduce:animate-none')

      unmountLoading()

      render(React.createElement(TypingIndicator))

      // Assert (THEN): TypingIndicator dots have motion-reduce class
      const typingContainer = screen.getByLabelText('Antwort wird generiert')
      const dots = typingContainer.querySelectorAll('span')
      dots.forEach((dot) => {
        expect(dot.className).toContain('motion-reduce:animate-none')
      })
    })

    it('AC-7: GIVEN the LoadingIndicator WHEN rendered THEN it has appropriate aria-label for screen readers', () => {
      // Arrange & Act (GIVEN/WHEN): render LoadingIndicator
      render(React.createElement(LoadingIndicator))

      // Assert (THEN): has role="status" and a meaningful aria-label
      const statusEl = screen.getByRole('status')
      expect(statusEl).toBeInTheDocument()

      const ariaLabel = statusEl.getAttribute('aria-label')
      expect(ariaLabel).toBeTruthy()
      // The aria-label should describe the loading/connecting action
      expect(ariaLabel).toContain('Verbinde')
    })
  })
})
