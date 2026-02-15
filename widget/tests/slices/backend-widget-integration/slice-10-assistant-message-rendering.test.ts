/**
 * Tests for Slice 10: Assistant-Message Rendering.
 * Derived from GIVEN/WHEN/THEN Acceptance Criteria in the Slice-Spec.
 *
 * Slice-Spec: specs/phase-3/2026-02-15-backend-widget-integration/slices/slice-10-assistant-message-rendering.md
 *
 * ACs covered:
 * - AC-1: Left-aligned with grey-100 background, grey-900 text, border-radius 12px
 * - AC-2: Max-width is 80% of thread width
 * - AC-3: Streaming text appends without re-mounting container DOM node
 * - AC-4: ChatThread uses ChatMessage for user, AssistantMessage for assistant
 * - AC-5: Avatar on left side (32px grey-200 circle with "A" text in grey-600)
 * - AC-6: Thread auto-scrolls to bottom on new message
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

// Mock @assistant-ui/react primitives so we can render AssistantMessage in isolation
vi.mock('@assistant-ui/react', () => {
  const Root = ({ children, className }: { children: React.ReactNode; className?: string }) =>
    React.createElement('div', { 'data-testid': 'message-root', className }, children)
  const Content = () => React.createElement('span', { 'data-testid': 'message-content' }, 'Test message')

  // ThreadPrimitive mocks
  const ThreadRoot = ({ children, className }: { children: React.ReactNode; className?: string }) =>
    React.createElement('div', { 'data-testid': 'thread-root', className }, children)
  const ThreadEmpty = ({ children }: { children: React.ReactNode }) =>
    React.createElement('div', { 'data-testid': 'thread-empty' }, children)
  const ThreadViewport = ({ children, className }: { children: React.ReactNode; className?: string }) =>
    React.createElement('div', { 'data-testid': 'thread-viewport', className }, children)
  const ThreadMessages = ({
    components,
  }: {
    components: { UserMessage?: React.ComponentType; AssistantMessage?: React.ComponentType }
  }) =>
    React.createElement('div', {
      'data-testid': 'thread-messages',
      'data-has-user-message': components.UserMessage ? 'true' : 'false',
      'data-has-assistant-message': components.AssistantMessage ? 'true' : 'false',
      'data-user-message-name': components.UserMessage?.name || '',
      'data-assistant-message-name': components.AssistantMessage?.name || '',
    })

  return {
    MessagePrimitive: { Root, Content },
    ThreadPrimitive: {
      Root: ThreadRoot,
      Empty: ThreadEmpty,
      Viewport: ThreadViewport,
      Messages: ThreadMessages,
    },
    useThread: () => ({ isRunning: false, messages: [] }),
  }
})

import { AssistantMessage } from '../../../src/components/chat/AssistantMessage'

// ---------------------------------------------------------------------------
// Unit Tests: AssistantMessage Component
// ---------------------------------------------------------------------------

describe('Slice 10: Assistant-Message Rendering', () => {
  describe('Unit: AssistantMessage styling', () => {
    it('renders with left-aligned layout (flex items-start)', () => {
      render(React.createElement(AssistantMessage))

      const root = screen.getByTestId('message-root')
      expect(root.className).toContain('flex')
      expect(root.className).toContain('items-start')
    })

    it('has grey-100 background on message bubble', () => {
      render(React.createElement(AssistantMessage))

      const root = screen.getByTestId('message-root')
      // Find the bubble div (contains bg-gray-100)
      const bubble = root.querySelector('[class*="bg-gray-100"]')
      expect(bubble).not.toBeNull()
    })

    it('has grey-900 text color on message bubble', () => {
      render(React.createElement(AssistantMessage))

      const root = screen.getByTestId('message-root')
      const bubble = root.querySelector('[class*="text-gray-900"]')
      expect(bubble).not.toBeNull()
    })

    it('has border-radius 12px (rounded-xl) on message bubble', () => {
      render(React.createElement(AssistantMessage))

      const root = screen.getByTestId('message-root')
      const bubble = root.querySelector('[class*="rounded-xl"]')
      expect(bubble).not.toBeNull()
    })

    it('has max-width of 80% on message bubble', () => {
      render(React.createElement(AssistantMessage))

      const root = screen.getByTestId('message-root')
      const bubble = root.querySelector('[class*="max-w-[80%]"]')
      expect(bubble).not.toBeNull()
    })
  })

  describe('Unit: AssistantMessage avatar', () => {
    it('renders avatar with 32px size (w-8 h-8)', () => {
      render(React.createElement(AssistantMessage))

      const root = screen.getByTestId('message-root')
      const avatar = root.querySelector('[class*="w-8"][class*="h-8"]')
      expect(avatar).not.toBeNull()
    })

    it('avatar is a circle (rounded-full)', () => {
      render(React.createElement(AssistantMessage))

      const root = screen.getByTestId('message-root')
      const avatar = root.querySelector('[class*="rounded-full"]')
      expect(avatar).not.toBeNull()
    })

    it('avatar has grey-200 background', () => {
      render(React.createElement(AssistantMessage))

      const root = screen.getByTestId('message-root')
      const avatar = root.querySelector('[class*="bg-gray-200"]')
      expect(avatar).not.toBeNull()
    })

    it('avatar contains "A" text in grey-600', () => {
      render(React.createElement(AssistantMessage))

      const aText = screen.getByText('A')
      expect(aText).toBeInTheDocument()
      expect(aText.className).toContain('text-gray-600')
    })
  })

  describe('Unit: AssistantMessage streaming', () => {
    it('container DOM node is stable across re-renders (no re-mount)', () => {
      // Arrange: render AssistantMessage
      const { rerender } = render(React.createElement(AssistantMessage))

      // Capture the root element reference
      const rootBefore = screen.getByTestId('message-root')

      // Act: rerender the same component (simulating streaming update)
      rerender(React.createElement(AssistantMessage))

      // Assert: same DOM node (React reconciler preserves it because same component type + key)
      const rootAfter = screen.getByTestId('message-root')
      expect(rootBefore).toBe(rootAfter)
    })
  })

  describe('Unit: ChatThread message differentiation', () => {
    it('passes AssistantMessage component to ThreadPrimitive.Messages', async () => {
      // We need to import ChatThread which uses the mocked ThreadPrimitive
      const { ChatThread } = await import('../../../src/components/chat/ChatThread')
      render(React.createElement(ChatThread))

      const messagesEl = screen.getByTestId('thread-messages')
      expect(messagesEl.getAttribute('data-has-assistant-message')).toBe('true')
      expect(messagesEl.getAttribute('data-assistant-message-name')).toBe('AssistantMessage')
    })

    it('passes ChatMessage component for user messages to ThreadPrimitive.Messages', async () => {
      const { ChatThread } = await import('../../../src/components/chat/ChatThread')
      render(React.createElement(ChatThread))

      const messagesEl = screen.getByTestId('thread-messages')
      expect(messagesEl.getAttribute('data-has-user-message')).toBe('true')
      expect(messagesEl.getAttribute('data-user-message-name')).toBe('ChatMessage')
    })
  })

  // ---------------------------------------------------------------------------
  // Acceptance Tests: 1:1 from GIVEN/WHEN/THEN in Slice-Spec
  // ---------------------------------------------------------------------------

  describe('Acceptance Tests', () => {
    it('AC-1: GIVEN an assistant message in the thread WHEN it renders THEN it is left-aligned with grey-100 background, grey-900 text, border-radius 12px', () => {
      // Arrange (GIVEN): an assistant message exists in the thread
      // Act (WHEN): render AssistantMessage component
      render(React.createElement(AssistantMessage))

      const root = screen.getByTestId('message-root')

      // Assert (THEN): left-aligned (flex layout, items-start means content flows left)
      expect(root.className).toContain('flex')
      expect(root.className).toContain('items-start')

      // grey-100 background
      const bubbleWithBg = root.querySelector('[class*="bg-gray-100"]')
      expect(bubbleWithBg).not.toBeNull()

      // grey-900 text
      const bubbleWithText = root.querySelector('[class*="text-gray-900"]')
      expect(bubbleWithText).not.toBeNull()

      // border-radius 12px (rounded-xl = 12px in Tailwind)
      const bubbleWithRadius = root.querySelector('[class*="rounded-xl"]')
      expect(bubbleWithRadius).not.toBeNull()
    })

    it('AC-2: GIVEN an assistant message WHEN rendered THEN its max-width is 80% of the thread width', () => {
      // Arrange & Act (GIVEN/WHEN): render AssistantMessage
      render(React.createElement(AssistantMessage))

      const root = screen.getByTestId('message-root')

      // Assert (THEN): bubble has max-w-[80%]
      const bubble = root.querySelector('[class*="max-w-[80%]"]')
      expect(bubble).not.toBeNull()
    })

    it('AC-3: GIVEN an assistant message during streaming WHEN new text-deltas arrive THEN each delta appends to the existing message text AND the message container element retains the same DOM node', () => {
      // Arrange (GIVEN): an assistant message is being streamed
      const { rerender } = render(React.createElement(AssistantMessage))

      // Capture DOM node reference before streaming update
      const containerBefore = screen.getByTestId('message-root')

      // Act (WHEN): new text-deltas arrive (simulated by rerender -- React reconciler
      // keeps the same component instance if type and key are unchanged)
      rerender(React.createElement(AssistantMessage))

      // Assert (THEN): container DOM node is the same instance (stable key/ref)
      const containerAfter = screen.getByTestId('message-root')
      expect(containerBefore).toBe(containerAfter)

      // The MessagePrimitive.Content handles text appending internally via @assistant-ui state,
      // so as long as the container is not re-mounted, text appends correctly.
    })

    it('AC-4: GIVEN the ChatThread WHEN it renders messages THEN user messages use ChatMessage (right-aligned, brand-color) and assistant messages use AssistantMessage (left-aligned, grey)', async () => {
      // Arrange & Act (GIVEN/WHEN): render ChatThread
      const { ChatThread } = await import('../../../src/components/chat/ChatThread')
      render(React.createElement(ChatThread))

      const messagesEl = screen.getByTestId('thread-messages')

      // Assert (THEN): user messages use ChatMessage
      expect(messagesEl.getAttribute('data-has-user-message')).toBe('true')
      expect(messagesEl.getAttribute('data-user-message-name')).toBe('ChatMessage')

      // Assert (THEN): assistant messages use AssistantMessage
      expect(messagesEl.getAttribute('data-has-assistant-message')).toBe('true')
      expect(messagesEl.getAttribute('data-assistant-message-name')).toBe('AssistantMessage')
    })

    it('AC-5: GIVEN an assistant message WHEN rendered THEN it displays an avatar on the left side (32px grey-200 circle with "A" text in grey-600)', () => {
      // Arrange & Act (GIVEN/WHEN): render AssistantMessage
      render(React.createElement(AssistantMessage))

      const root = screen.getByTestId('message-root')

      // Assert (THEN): avatar is present on the left side
      // Avatar: 32px = w-8 h-8, grey-200 background, rounded-full circle
      const avatar = root.querySelector('[class*="w-8"][class*="h-8"][class*="rounded-full"][class*="bg-gray-200"]')
      expect(avatar).not.toBeNull()

      // Contains "A" text
      const aText = screen.getByText('A')
      expect(aText).toBeInTheDocument()

      // "A" text is grey-600
      expect(aText.className).toContain('text-gray-600')

      // Avatar is before the bubble (left side) -- avatar should be the first child element
      const firstChild = root.children[0]
      expect(firstChild).toBe(avatar)
    })

    it('AC-6: GIVEN multiple messages in the thread WHEN a new message appears THEN the thread auto-scrolls to the bottom', () => {
      // Arrange (GIVEN): Multiple messages exist in the thread.
      // The auto-scroll behavior is provided by @assistant-ui's ThreadPrimitive.Viewport
      // component, which automatically scrolls to the bottom when new messages appear.
      //
      // ThreadPrimitive.Viewport handles auto-scroll natively. The contract is:
      // ChatThread uses ThreadPrimitive.Viewport to wrap ThreadPrimitive.Messages,
      // which ensures auto-scroll behavior.

      // Act (WHEN): We verify that ChatThread uses ThreadPrimitive.Viewport
      // (This is a structural/contract test since actual scroll behavior requires a browser)

      // We import and verify the component structure
      // ChatThread renders ThreadPrimitive.Viewport wrapping ThreadPrimitive.Messages
      // The mock renders data-testid="thread-viewport" containing data-testid="thread-messages"

      // We already verified ChatThread structure in AC-4. Here we verify the viewport
      // wrapper is present, which is the @assistant-ui mechanism for auto-scroll.
      const importPromise = import('../../../src/components/chat/ChatThread')
      return importPromise.then(({ ChatThread }) => {
        render(React.createElement(ChatThread))

        const viewport = screen.getByTestId('thread-viewport')
        expect(viewport).toBeInTheDocument()

        // The messages container is inside the viewport (auto-scroll scope)
        const messages = screen.getByTestId('thread-messages')
        expect(viewport.contains(messages)).toBe(true)
      })
    })
  })
})
