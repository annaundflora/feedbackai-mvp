export function ClusterDetailSkeleton() {
  return (
    <div data-testid="cluster-detail-skeleton" aria-busy="true">
      {/* Header skeleton */}
      <div className="flex items-center justify-between mb-6">
        <div className="h-8 bg-gray-200 rounded w-64 animate-pulse" />
        <div className="flex gap-2">
          <div className="h-9 bg-gray-200 rounded w-24 animate-pulse" />
          <div className="h-9 bg-gray-200 rounded w-20 animate-pulse" />
        </div>
      </div>

      {/* Summary skeleton */}
      <section aria-label="Cluster summary" className="mb-8">
        <div className="h-5 bg-gray-200 rounded w-24 mb-3 animate-pulse" />
        <div className="space-y-2">
          <div className="h-4 bg-gray-200 rounded w-full animate-pulse" />
          <div className="h-4 bg-gray-200 rounded w-full animate-pulse" />
          <div className="h-4 bg-gray-200 rounded w-3/4 animate-pulse" />
        </div>
      </section>

      <hr className="border-gray-200 mb-8" />

      {/* Facts skeleton */}
      <section aria-label="Facts" className="mb-8">
        <div className="h-5 bg-gray-200 rounded w-32 mb-4 animate-pulse" />
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-start gap-3">
                <div className="h-4 bg-gray-200 rounded w-4 animate-pulse shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-full animate-pulse" />
                  <div className="h-4 bg-gray-200 rounded w-2/3 animate-pulse" />
                  <div className="h-5 bg-gray-200 rounded w-24 animate-pulse" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <hr className="border-gray-200 mb-8" />

      {/* Quotes skeleton */}
      <section aria-label="Supporting quotes">
        <div className="h-5 bg-gray-200 rounded w-20 mb-4 animate-pulse" />
        <div className="space-y-3">
          {[1, 2].map(i => (
            <div key={i} className="bg-white rounded-lg border border-gray-200 border-l-4 border-l-blue-200 p-4">
              <div className="space-y-2">
                <div className="h-4 bg-gray-200 rounded w-full animate-pulse" />
                <div className="h-4 bg-gray-200 rounded w-4/5 animate-pulse" />
                <div className="h-3 bg-gray-200 rounded w-24 ml-auto animate-pulse" />
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
