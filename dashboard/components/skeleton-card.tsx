interface SkeletonCardProps {
  'data-testid'?: string
}

export function SkeletonCard({ 'data-testid': testId }: SkeletonCardProps) {
  return (
    <div
      data-testid={testId ?? 'skeleton-card'}
      className="rounded-xl border bg-white p-5 shadow-sm animate-pulse"
      aria-hidden="true"
    >
      <div className="h-5 bg-gray-200 rounded w-3/4 mb-3" />
      <div className="flex gap-4 mb-3">
        <div className="h-4 bg-gray-200 rounded w-24" />
        <div className="h-4 bg-gray-200 rounded w-20" />
      </div>
      <div className="h-3 bg-gray-200 rounded w-1/2" />
    </div>
  )
}
