'use client'

import { useState, useEffect } from 'react'

interface UndoToastProps {
  message: string
  expiresAt: string   // ISO 8601 datetime string
  onUndo: () => Promise<void>
  onDismiss: () => void
}

export function UndoToast({ message, expiresAt, onUndo, onDismiss }: UndoToastProps) {
  const [secondsLeft, setSecondsLeft] = useState(() => {
    const ms = new Date(expiresAt).getTime() - Date.now()
    return Math.max(0, Math.ceil(ms / 1000))
  })
  const [isUndoing, setIsUndoing] = useState(false)

  useEffect(() => {
    if (secondsLeft <= 0) {
      onDismiss()
      return
    }
    const timer = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          clearInterval(timer)
          onDismiss()
          return 0
        }
        return s - 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [secondsLeft, onDismiss])

  async function handleUndo() {
    setIsUndoing(true)
    try {
      await onUndo()
    } finally {
      setIsUndoing(false)
      onDismiss()
    }
  }

  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 bg-gray-900 text-white px-4 py-3 rounded-lg shadow-lg text-sm"
      data-testid="undo-toast"
    >
      <span>{message}</span>
      <button
        onClick={handleUndo}
        disabled={isUndoing || secondsLeft <= 0}
        className="font-medium text-blue-400 hover:text-blue-300 disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-blue-400"
        data-testid="undo-btn"
      >
        {isUndoing ? 'Undoing...' : `Undo (${secondsLeft}s)`}
      </button>
    </div>
  )
}
