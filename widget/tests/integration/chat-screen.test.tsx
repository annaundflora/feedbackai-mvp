/**
 * Integration Tests for ChatScreen.
 *
 * Tests the full ChatScreen component with mocked @assistant-ui primitives,
 * verifying that ChatThread, ChatComposer, and the runtime provider
 * are correctly composed together.
 *
 * Note: True integration with @assistant-ui requires a browser runtime.
 * These tests verify component composition and prop passing through
 * the component tree with lightweight mocks of the primitives.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import React, { useReducer } from 'react'

// Mock @assistant-ui/react with functional primitives
vi.mock('@assistant-ui/react', () => ({
  ThreadPrimitive: {
    Root: ({ children, className }: { children: React.ReactNode; className?: string }) => (
      <div data-testid="thread-root" className={className} role="log" aria-live="polite">
        {children}
      </div>
    ),
    Empty: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="thread-empty">{children}</div>
    ),
    Viewport: ({ children, className }: { children: React.ReactNode; className?: string }) => (
      <div data-testid="thread-viewport" className={className}>{children}</div>
    ),
    Messages: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="thread-messages">{children}</div>
    ),
  },
  MessagePrimitive: {
    Root: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    If: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    Content: ({ components }: { components: { Text: React.FC<{ part: { text: string } }> } }) => {
      const TextComponent = components.Text
      return <TextComponent part={{ text: 'Test content' }} />
    },
  },
  ComposerPrimitive: {
    Root: ({ children, className }: { children: React.ReactNode; className?: string }) => (
      <form data-testid="composer-root" className={className}>{children}</form>
    ),
    Input: (props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) => (
      <textarea
        data-testid="composer-input"
        placeholder={props.placeholder}
        className={props.className}
        aria-label="Nachricht eingeben"
      />
    ),
    Send: ({ children, ...rest }: React.ButtonHTMLAttributes<HTMLButtonElement> & { children: React.ReactNode }) => (
      <button data-testid="composer-send" type="submit" aria-label={rest['aria-label']}>
        {children}
      </button>
    ),
  },
  useLocalRuntime: vi.fn(() => ({ _type: 'mocked-runtime' })),
  useThread: vi.fn(() => ({ isRunning: false, messages: [] })),
  useThreadRuntime: vi.fn(() => ({
    subscribe: vi.fn(() => vi.fn()),
    getState: vi.fn(() => ({ messages: [] })),
    cancelRun: vi.fn(),
    startRun: vi.fn(),
  })),
}))

import { ChatScreen } from '../../src/components/screens/ChatScreen'
import { ConsentScreen } from '../../src/components/screens/ConsentScreen'
import { widgetReducer, initialState, type WidgetScreen } from '../../src/reducer'
import type { WidgetConfig } from '../../src/config'

const mockControls = {
  endInterview: vi.fn(),
  hasActiveSession: vi.fn(() => false),
}

const TEST_CONFIG: WidgetConfig = {
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

describe('integration: ChatScreen composition', () => {
  it('ChatScreen renders thread and composer together', () => {
    render(<ChatScreen config={TEST_CONFIG} controls={mockControls} onRestart={vi.fn()} onRedirectToThankYou={vi.fn()} />)

    // Thread rendered
    const threadRoot = screen.getByTestId('thread-root')
    expect(threadRoot).toBeInTheDocument()

    // Composer rendered
    const composerRoot = screen.getByTestId('composer-root')
    expect(composerRoot).toBeInTheDocument()
  })

  it('ChatThread shows welcome state when thread is empty', () => {
    render(<ChatScreen config={TEST_CONFIG} controls={mockControls} onRestart={vi.fn()} onRedirectToThankYou={vi.fn()} />)

    // ThreadPrimitive.Empty renders the welcome message
    expect(screen.getByText('Bereit für Ihr Feedback')).toBeInTheDocument()
    expect(
      screen.getByText('Stellen Sie Ihre Frage oder teilen Sie uns Ihre Gedanken mit.')
    ).toBeInTheDocument()
  })

  it('ChatComposer receives placeholder from config.texts.composerPlaceholder', () => {
    render(<ChatScreen config={TEST_CONFIG} controls={mockControls} onRestart={vi.fn()} onRedirectToThankYou={vi.fn()} />)

    const input = screen.getByTestId('composer-input')
    expect(input).toHaveAttribute('placeholder', 'Nachricht eingeben...')
  })

  it('send button has aria-label for accessibility', () => {
    render(<ChatScreen config={TEST_CONFIG} controls={mockControls} onRestart={vi.fn()} onRedirectToThankYou={vi.fn()} />)

    const sendButton = screen.getByTestId('composer-send')
    expect(sendButton).toHaveAttribute('aria-label', 'Nachricht senden')
  })

  it('ChatScreen layout has thread area above and composer area below', () => {
    const { container } = render(<ChatScreen config={TEST_CONFIG} controls={mockControls} onRestart={vi.fn()} onRedirectToThankYou={vi.fn()} />)

    const flexContainer = container.querySelector('.flex.flex-col.h-full')
    expect(flexContainer).not.toBeNull()
    expect(flexContainer?.children.length).toBe(2)

    // First child: thread area (flex-1)
    const threadArea = flexContainer?.children[0]
    expect(threadArea?.className).toContain('flex-1')
    expect(threadArea?.className).toContain('overflow-y-auto')

    // Second child: composer area (border-t)
    const composerArea = flexContainer?.children[1]
    expect(composerArea?.className).toContain('border-t')
  })
})

describe('integration: ScreenRouter routes to ChatScreen', () => {
  /**
   * Simplified ScreenRouter for integration testing.
   * Mirrors the production ScreenRouter from main.tsx.
   */
  function TestScreenRouter({
    screenValue,
    config,
    onAcceptConsent,
  }: {
    screenValue: WidgetScreen
    config: WidgetConfig
    onAcceptConsent: () => void
  }) {
    switch (screenValue) {
      case 'consent':
        return (
          <ConsentScreen
            headline={config.texts.consentHeadline}
            body={config.texts.consentBody}
            ctaLabel={config.texts.consentCta}
            onAccept={onAcceptConsent}
          />
        )
      case 'chat':
        return <ChatScreen config={config} controls={mockControls} onRestart={() => {}} onRedirectToThankYou={() => {}} />
      default:
        return null
    }
  }

  it('ScreenRouter renders ChatScreen when screen is "chat"', () => {
    render(
      <TestScreenRouter
        screenValue="chat"
        config={TEST_CONFIG}
        onAcceptConsent={() => {}}
      />
    )

    // ChatScreen should be rendered with thread and composer
    expect(screen.getByTestId('thread-root')).toBeInTheDocument()
    expect(screen.getByTestId('composer-root')).toBeInTheDocument()
  })

  it('ScreenRouter passes config to ChatScreen so composer gets placeholder', () => {
    render(
      <TestScreenRouter
        screenValue="chat"
        config={TEST_CONFIG}
        onAcceptConsent={() => {}}
      />
    )

    const input = screen.getByTestId('composer-input')
    expect(input).toHaveAttribute('placeholder', TEST_CONFIG.texts.composerPlaceholder)
  })

  it('reducer GO_TO_CHAT transitions to chat screen for ScreenRouter', () => {
    const consentState = { panelOpen: true, screen: 'consent' as WidgetScreen }
    const result = widgetReducer(consentState, { type: 'GO_TO_CHAT' })
    expect(result.screen).toBe('chat')
    expect(result.panelOpen).toBe(true) // unchanged
  })
})
