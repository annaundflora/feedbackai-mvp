// dashboard/components/skeleton-card.tsx

interface SkeletonCardProps {
  variant?: "project" | "cluster" | "fact" | "row";
  'data-testid'?: string;
}

export function SkeletonCard({ variant = "project", 'data-testid': testId }: SkeletonCardProps): JSX.Element {
  if (variant === "row") {
    return (
      <div className="flex items-center gap-4 p-3 animate-pulse" data-testid={testId ?? "skeleton-row"}>
        <div className="h-4 w-12 bg-gray-200 rounded" />
        <div className="h-4 w-24 bg-gray-200 rounded" />
        <div className="h-4 flex-1 bg-gray-200 rounded" />
        <div className="h-4 w-8 bg-gray-200 rounded" />
        <div className="h-6 w-16 bg-gray-200 rounded-full" />
      </div>
    );
  }

  if (variant === "fact") {
    return (
      <div className="p-4 border border-gray-100 rounded-lg animate-pulse" data-testid={testId ?? "skeleton-fact"}>
        <div className="h-4 bg-gray-200 rounded w-full mb-2" />
        <div className="h-4 bg-gray-200 rounded w-3/4" />
        <div className="flex gap-2 mt-3">
          <div className="h-5 w-20 bg-gray-200 rounded-full" />
          <div className="h-5 w-16 bg-gray-200 rounded-full" />
        </div>
      </div>
    );
  }

  if (variant === "cluster") {
    return (
      <div className="p-5 border border-gray-200 rounded-xl animate-pulse" data-testid={testId ?? "skeleton-cluster"}>
        <div className="flex justify-between mb-3">
          <div className="h-5 bg-gray-200 rounded w-40" />
          <div className="h-5 w-5 bg-gray-200 rounded" />
        </div>
        <div className="flex gap-2 mb-3">
          <div className="h-5 w-16 bg-gray-200 rounded-full" />
          <div className="h-5 w-20 bg-gray-200 rounded-full" />
        </div>
        <div className="space-y-2">
          <div className="h-4 bg-gray-200 rounded w-full" />
          <div className="h-4 bg-gray-200 rounded w-5/6" />
          <div className="h-4 bg-gray-200 rounded w-4/6" />
        </div>
      </div>
    );
  }

  // variant === "project" (default)
  return (
    <div className="p-5 border border-gray-200 rounded-xl animate-pulse" data-testid={testId ?? "skeleton-project"}>
      <div className="h-5 bg-gray-200 rounded w-40 mb-3" />
      <div className="flex gap-3">
        <div className="h-4 w-24 bg-gray-200 rounded" />
        <div className="h-4 w-20 bg-gray-200 rounded" />
      </div>
      <div className="h-3 w-28 bg-gray-200 rounded mt-3" />
    </div>
  );
}

export function SkeletonGrid({ count = 3, variant = "project" }: { count?: number; variant?: SkeletonCardProps["variant"] }): JSX.Element {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="skeleton-grid">
      {Array.from({ length: count }, (_, i) => (
        <SkeletonCard key={i} variant={variant} />
      ))}
    </div>
  );
}
