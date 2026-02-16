/**
 * Unit Tests for ChatScreen component.
 *
 * Tests the screen composition: ChatThread and ChatComposer,
 * with config prop passed through. AssistantRuntimeProvider is now
 * at the Widget level (main.tsx), not inside ChatScreen.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

// Mock @assistant-ui/react
vi.mock('@assistant-ui/react', () => ({
  ThreadPrimitive: {
    Root: ({ children, className }: { children: React.ReactNode; className?: string }) => (
      <div data-testid="thread-root" className={className}>{children}</div>
    ),
    Empty: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    Viewport: ({ children, className }: { children: React.ReactNode; className?: string }) => (
      <div className={className}>{children}</div>
    ),
    Messages: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  },
  MessagePrimitive: {
    Root: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    If: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    Content: () => <div>Mock message</div>,
  },
  ComposerPrimitive: {
    Root: ({ children, className }: { children: React.ReactNode; className?: string }) => (
      <form className={className}>{children}</form>
    ),
    Input: (props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) => (
      <textarea data-testid="composer-input" placeholder={props.placeholder} />
    ),
    Send: ({ children, ...rest }: React.ButtonHTMLAttributes<HTMLButtonElement> & { children: React.ReactNode }) => (
      <button aria-label={rest['aria-label']}>{children}</button>
    ),
  },
  useThread: vi.fn(() => ({ isRunning: false, messages: [] })),
  useThreadRuntime: vi.fn(() => ({
    subscribe: vi.fn(() => vi.fn()),
    getState: vi.fn(() => ({ messages: [] })),
    cancelRun: vi.fn(),
    startRun: vi.fn(),
  })),
}))

import { ChatScreen } from '../../src/components/screens/ChatScreen'
import type { WidgetConfig } from '../../src/config'

const TEST_CONFIG: WidgetConfig = {
  apiUrl: null,
  lang: 'de',
  texts: {
    panelTitle: 'Feedback',
    consentHeadline: 'Ihr Feedback zaehlt!',
    consentBody: 'Test body',
    consentCta: "Los geht's",
    thankYouHeadline: 'Vielen Dank!',
    thankYouBody: 'Test thank you',
    composerPlaceholder: 'Nachricht eingeben...',
  },
}

const mockControls = {
  endInterview: vi.fn(),
  hasActiveSession: vi.fn(() => false),
}

describe('unit: ChatScreen', () => {
  it('renders ChatThread inside thread area', () => {
    render(<ChatScreen config={TEST_CONFIG} controls={mockControls} onRestart={vi.fn()} onRedirectToThankYou={vi.fn()} />)

    const threadRoot = screen.getByTestId('thread-root')
    expect(threadRoot).toBeInTheDocument()
  })

  it('renders ChatComposer with placeholder from config', () => {
    render(<ChatScreen config={TEST_CONFIG} controls={mockControls} onRestart={vi.fn()} onRedirectToThankYou={vi.fn()} />)

    const input = screen.getByTestId('composer-input')
    expect(input).toHaveAttribute('placeholder', 'Nachricht eingeben...')
  })

  it('passes custom composerPlaceholder from config to ChatComposer', () => {
    const enConfig: WidgetConfig = {
      ...TEST_CONFIG,
      lang: 'en',
      texts: { ...TEST_CONFIG.texts, composerPlaceholder: 'Type a message...' },
    }

    render(<ChatScreen config={enConfig} controls={mockControls} onRestart={vi.fn()} onRedirectToThankYou={vi.fn()} />)

    const input = screen.getByTestId('composer-input')
    expect(input).toHaveAttribute('placeholder', 'Type a message...')
  })

  it('has flex layout with thread area (flex-1) and composer area (border-t)', () => {
    const { container } = render(<ChatScreen config={TEST_CONFIG} controls={mockControls} onRestart={vi.fn()} onRedirectToThankYou={vi.fn()} />)

    const layoutDiv = container.querySelector('.flex.flex-col.h-full')
    expect(layoutDiv).not.toBeNull()

    const threadArea = container.querySelector('.flex-1.overflow-y-auto')
    expect(threadArea).not.toBeNull()

    const composerArea = container.querySelector('.border-t')
    expect(composerArea).not.toBeNull()
  })
})
