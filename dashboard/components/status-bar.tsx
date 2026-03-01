interface StatusBarProps {
  interviewCount: number;
  factCount: number;
  clusterCount: number;
}

// Live-Updates: Counts werden als Props von der Page uebergeben.
// Page haelt lokalen State (optimistic) und aktualisiert via useProjectEvents.
export function StatusBar({ interviewCount, factCount, clusterCount }: StatusBarProps) {
  return (
    <div
      data-testid="status-bar"
      className="flex gap-6 text-sm text-gray-600 dark:text-gray-400 py-3 border-b border-gray-200 dark:border-gray-700 tabular-nums"
    >
      <span data-testid="status-interview-count">
        <strong className="text-gray-900 dark:text-gray-100">{interviewCount}</strong> Interviews
      </span>
      <span data-testid="status-fact-count">
        <strong className="text-gray-900 dark:text-gray-100">{factCount}</strong> Facts
      </span>
      <span data-testid="status-cluster-count">
        <strong className="text-gray-900 dark:text-gray-100">{clusterCount}</strong> Clusters
      </span>
    </div>
  );
}
