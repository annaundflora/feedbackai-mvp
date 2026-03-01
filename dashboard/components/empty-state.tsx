interface EmptyStateProps {
  message: string
  ctaLabel?: string
  ctaHref?: string
  'data-testid'?: string
}

export function EmptyState({
  message,
  ctaLabel,
  ctaHref,
  'data-testid': testId,
}: EmptyStateProps) {
  return (
    <div
      data-testid={testId}
      className="flex flex-col items-center justify-center py-16 text-center"
    >
      <p className="text-gray-500 mb-4">{message}</p>
      {ctaLabel !== undefined && (
        ctaHref !== undefined ? (
          <a
            href={ctaHref}
            data-testid="empty-state-cta"
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 text-sm font-medium transition-colors"
          >
            {ctaLabel}
          </a>
        ) : (
          <button
            type="button"
            data-testid="empty-state-cta"
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 text-sm font-medium transition-colors"
          >
            {ctaLabel}
          </button>
        )
      )}
    </div>
  )
}
