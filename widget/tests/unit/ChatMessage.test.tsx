/**
 * Unit Tests for ChatMessage component.
 *
 * Tests rendering of user message bubbles with mocked @assistant-ui primitives.
 * The component uses MessagePrimitive.If and MessagePrimitive.Content from @assistant-ui.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

// Mock @assistant-ui/react primitives
vi.mock('@assistant-ui/react', () => ({
  MessagePrimitive: {
    If: ({ user, children }: { user?: boolean; assistant?: boolean; children: React.ReactNode }) => {
      // Simulate: only render children when the condition matches
      if (user) return <>{children}</>
      return null
    },
    Content: ({ components }: { components: { Text: React.FC<{ part: { text: string } }> } }) => {
      // Render the Text component with mock text
      const TextComponent = components.Text
      return <TextComponent part={{ text: 'Test message content' }} />
    },
  },
}))

import { ChatMessage } from '../../src/components/chat/ChatMessage'

describe('unit: ChatMessage', () => {
  it('renders user message bubble with correct styling classes', () => {
    const { container } = render(<ChatMessage />)

    // ChatMessage renders inside MessagePrimitive.If user
    const bubble = container.querySelector('.chat-message')
    expect(bubble).not.toBeNull()

    // User message should be right-aligned
    expect(bubble?.className).toContain('justify-end')
  })

  it('renders message text content via MessagePrimitive.Content', () => {
    render(<ChatMessage />)

    // The mocked Content component renders our test text
    expect(screen.getByText('Test message content')).toBeInTheDocument()
  })

  it('message bubble has max-w-[80%] for readable width', () => {
    const { container } = render(<ChatMessage />)

    const bubble = container.querySelector('.max-w-\\[80\\%\\]')
    expect(bubble).not.toBeNull()
  })

  it('message bubble has rounded-2xl corners', () => {
    const { container } = render(<ChatMessage />)

    const bubble = container.querySelector('.rounded-2xl')
    expect(bubble).not.toBeNull()
  })

  it('user message has brand background color', () => {
    const { container } = render(<ChatMessage />)

    const bubble = container.querySelector('.bg-brand')
    expect(bubble).not.toBeNull()
  })

  it('text has whitespace-pre-wrap for line breaks', () => {
    const { container } = render(<ChatMessage />)

    const textElement = container.querySelector('.whitespace-pre-wrap')
    expect(textElement).not.toBeNull()
  })
})
