export function InterviewDetailSkeleton() {
  return (
    <div data-testid="interview-detail-skeleton" aria-busy="true">
      {/* Header skeleton */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="h-7 bg-gray-200 rounded w-40 animate-pulse mb-2" />
          <div className="flex gap-2">
            <div className="h-5 bg-gray-200 rounded w-24 animate-pulse" />
            <div className="h-5 bg-gray-200 rounded w-20 animate-pulse" />
            <div className="h-5 bg-gray-200 rounded w-20 animate-pulse" />
          </div>
        </div>
      </div>

      {/* Summary skeleton */}
      <section className="mb-8">
        <div className="h-5 bg-gray-200 rounded w-24 mb-3 animate-pulse" />
        <div className="space-y-2">
          <div className="h-4 bg-gray-200 rounded w-full animate-pulse" />
          <div className="h-4 bg-gray-200 rounded w-full animate-pulse" />
          <div className="h-4 bg-gray-200 rounded w-3/4 animate-pulse" />
        </div>
      </section>

      <hr className="border-gray-200 mb-8" />

      {/* Transcript skeleton */}
      <section className="mb-8">
        <div className="h-5 bg-gray-200 rounded w-28 mb-4 animate-pulse" />
        <div className="space-y-3">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className={`flex ${i % 2 === 0 ? 'justify-end' : 'justify-start'}`}>
              <div className="h-16 bg-gray-200 rounded-lg w-3/4 animate-pulse" />
            </div>
          ))}
        </div>
      </section>

      <hr className="border-gray-200 mb-8" />

      {/* Facts skeleton */}
      <section>
        <div className="h-5 bg-gray-200 rounded w-20 mb-4 animate-pulse" />
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="space-y-2">
                <div className="h-4 bg-gray-200 rounded w-full animate-pulse" />
                <div className="h-4 bg-gray-200 rounded w-2/3 animate-pulse" />
                <div className="h-5 bg-gray-200 rounded w-24 animate-pulse" />
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
