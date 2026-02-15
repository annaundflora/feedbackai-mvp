/**
 * Unit Tests for ChatScreen component.
 *
 * Tests the screen composition: AssistantRuntimeProvider wrapping
 * ChatThread and ChatComposer, with config prop passed through.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

// Mock the chat runtime hook
vi.mock('../../src/lib/chat-runtime', () => ({
  useWidgetChatRuntime: vi.fn(() => ({ _type: 'mocked-runtime' })),
}))

// Mock @assistant-ui/react
vi.mock('@assistant-ui/react', () => ({
  AssistantRuntimeProvider: ({ children, runtime }: { children: React.ReactNode; runtime: unknown }) => (
    <div data-testid="runtime-provider" data-runtime={JSON.stringify(runtime)}>
      {children}
    </div>
  ),
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

describe('unit: ChatScreen', () => {
  it('wraps content in AssistantRuntimeProvider', () => {
    render(<ChatScreen config={TEST_CONFIG} />)

    const provider = screen.getByTestId('runtime-provider')
    expect(provider).toBeInTheDocument()
  })

  it('passes runtime from useWidgetChatRuntime to provider', () => {
    render(<ChatScreen config={TEST_CONFIG} />)

    const provider = screen.getByTestId('runtime-provider')
    const runtimeData = JSON.parse(provider.getAttribute('data-runtime') || '{}')
    expect(runtimeData._type).toBe('mocked-runtime')
  })

  it('renders ChatThread inside thread area', () => {
    render(<ChatScreen config={TEST_CONFIG} />)

    // ChatThread renders thread-root
    const threadRoot = screen.getByTestId('thread-root')
    expect(threadRoot).toBeInTheDocument()
  })

  it('renders ChatComposer with placeholder from config', () => {
    render(<ChatScreen config={TEST_CONFIG} />)

    const input = screen.getByTestId('composer-input')
    expect(input).toHaveAttribute('placeholder', 'Nachricht eingeben...')
  })

  it('passes custom composerPlaceholder from config to ChatComposer', () => {
    const enConfig: WidgetConfig = {
      ...TEST_CONFIG,
      lang: 'en',
      texts: { ...TEST_CONFIG.texts, composerPlaceholder: 'Type a message...' },
    }

    render(<ChatScreen config={enConfig} />)

    const input = screen.getByTestId('composer-input')
    expect(input).toHaveAttribute('placeholder', 'Type a message...')
  })

  it('has flex layout with thread area (flex-1) and composer area (border-t)', () => {
    const { container } = render(<ChatScreen config={TEST_CONFIG} />)

    // The outer layout div
    const layoutDiv = container.querySelector('.flex.flex-col.h-full')
    expect(layoutDiv).not.toBeNull()

    // Thread area: flex-1 overflow-y-auto
    const threadArea = container.querySelector('.flex-1.overflow-y-auto')
    expect(threadArea).not.toBeNull()

    // Composer area: border-t
    const composerArea = container.querySelector('.border-t')
    expect(composerArea).not.toBeNull()
  })
})
