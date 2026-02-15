/**
 * Unit Tests for ChatThread component.
 *
 * Tests the thread container with welcome/empty state and message list,
 * using mocked @assistant-ui primitives.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

// Mock @assistant-ui/react primitives
vi.mock('@assistant-ui/react', () => ({
  ThreadPrimitive: {
    Root: ({ children, className }: { children: React.ReactNode; className?: string }) => (
      <div data-testid="thread-root" className={className}>
        {children}
      </div>
    ),
    Empty: ({ children }: { children: React.ReactNode }) => (
      // Simulate empty state (no messages)
      <div data-testid="thread-empty">{children}</div>
    ),
    Viewport: ({ children, className }: { children: React.ReactNode; className?: string }) => (
      <div data-testid="thread-viewport" className={className}>
        {children}
      </div>
    ),
    Messages: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="thread-messages">{children}</div>
    ),
  },
  MessagePrimitive: {
    Root: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="message-root">{children}</div>
    ),
    If: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    Content: () => <div data-testid="message-content">Mock message</div>,
  },
}))

// Must import after mocks
import { ChatThread } from '../../src/components/chat/ChatThread'

describe('unit: ChatThread', () => {
  it('renders ThreadPrimitive.Root with h-full class', () => {
    render(<ChatThread />)

    const root = screen.getByTestId('thread-root')
    expect(root).toBeInTheDocument()
    expect(root.className).toContain('h-full')
  })

  it('renders welcome/empty state with "Bereit fuer Ihr Feedback" heading', () => {
    render(<ChatThread />)

    expect(screen.getByText('Bereit für Ihr Feedback')).toBeInTheDocument()
  })

  it('renders welcome state with descriptive subtext', () => {
    render(<ChatThread />)

    expect(
      screen.getByText('Stellen Sie Ihre Frage oder teilen Sie uns Ihre Gedanken mit.')
    ).toBeInTheDocument()
  })

  it('welcome state contains a chat icon (SVG with aria-hidden)', () => {
    const { container } = render(<ChatThread />)

    const emptyState = screen.getByTestId('thread-empty')
    const svg = emptyState.querySelector('svg[aria-hidden="true"]')
    expect(svg).not.toBeNull()
  })

  it('renders ThreadPrimitive.Viewport for message list', () => {
    render(<ChatThread />)

    const viewport = screen.getByTestId('thread-viewport')
    expect(viewport).toBeInTheDocument()
    expect(viewport.className).toContain('px-4')
    expect(viewport.className).toContain('py-2')
  })

  it('renders ThreadPrimitive.Messages container', () => {
    render(<ChatThread />)

    const messages = screen.getByTestId('thread-messages')
    expect(messages).toBeInTheDocument()
  })
})
