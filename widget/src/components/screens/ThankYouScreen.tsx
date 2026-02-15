import React, { useEffect } from 'react'

interface ThankYouScreenProps {
  headline: string
  body: string
  onAutoClose: () => void
  autoCloseDelay?: number // in ms, default 5000
}

export function ThankYouScreen({
  headline,
  body,
  onAutoClose,
  autoCloseDelay = 5000
}: ThankYouScreenProps) {
  // Auto-close Timer
  useEffect(() => {
    const timer = setTimeout(() => {
      onAutoClose()
    }, autoCloseDelay)

    // Cleanup on unmount
    return () => clearTimeout(timer)
  }, [onAutoClose, autoCloseDelay])

  return (
    <div className="flex flex-col items-center justify-center h-full px-6 py-8 text-center screen-container">
      {/* Success Icon */}
      <div className="w-20 h-20 mb-6 rounded-full bg-green-100 flex items-center justify-center">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="w-10 h-10 text-green-600"
          aria-hidden="true"
        >
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </div>

      {/* Headline */}
      <h2 className="text-2xl font-bold text-gray-900 mb-4">
        {headline}
      </h2>

      {/* Body */}
      <p className="text-base text-gray-600 leading-relaxed max-w-md mb-6">
        {body}
      </p>

      {/* Auto-close Hint */}
      <p className="text-sm text-gray-400">
        Schließt automatisch in wenigen Sekunden...
      </p>
    </div>
  )
}
