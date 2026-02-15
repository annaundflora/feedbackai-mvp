import type { ErrorAction } from '../../lib/error-utils'

interface ErrorDisplayProps {
  message: string
  action: ErrorAction
  onRetry?: () => void
  onRestart?: () => void
}

export function ErrorDisplay({ message, action, onRetry, onRestart }: ErrorDisplayProps) {
  return (
    <div
      role="alert"
      className="mx-4 my-2 p-4 rounded-lg border border-red-700 bg-red-50"
    >
      <div className="flex items-start gap-3">
        <svg
          className="w-5 h-5 text-red-700 flex-shrink-0 mt-0.5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div className="flex-1">
          <p className="text-sm font-medium text-red-900">{message}</p>
          <div className="mt-3">
            {action === 'retry' && onRetry && (
              <button
                onClick={onRetry}
                className="text-sm font-medium text-red-700 border border-red-700 rounded-md px-3 py-1.5 hover:bg-red-100 transition-colors focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
              >
                Erneut versuchen
              </button>
            )}
            {action === 'restart' && onRestart && (
              <button
                onClick={onRestart}
                className="text-sm font-medium text-red-700 border border-red-700 rounded-md px-3 py-1.5 hover:bg-red-100 transition-colors focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
              >
                Neu starten
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
