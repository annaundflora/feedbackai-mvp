import React from 'react'
import { ChatBubbleIcon } from './icons/ChatBubbleIcon'

interface FloatingButtonProps {
  onClick: () => void
  visible: boolean
}

export function FloatingButton({ onClick, visible }: FloatingButtonProps) {
  if (!visible) return null

  return (
    <button
      onClick={onClick}
      aria-label="Feedback geben"
      className="
        fixed bottom-4 right-4
        w-14 h-14 rounded-full
        bg-brand hover:bg-brand-hover
        shadow-floating-button
        flex items-center justify-center
        transition-all duration-200
        hover:scale-110 active:scale-95
        touch-action-manipulation
        focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2
        z-[9999]
      "
      style={{
        animation: visible ? 'fade-in 200ms ease-out' : 'fade-out 200ms ease-in'
      }}
    >
      <ChatBubbleIcon className="w-6 h-6 text-white" />
    </button>
  )
}
