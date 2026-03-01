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
      className="flex gap-6 py-3 border-b border-gray-200"
    >
      <span data-testid="status-interview-count" className="text-sm text-gray-500">
        <span className="font-semibold text-gray-900 tabular-nums">{interviewCount}</span>
        {" "}Interviews
      </span>
      <span data-testid="status-fact-count" className="text-sm text-gray-500">
        <span className="font-semibold text-gray-900 tabular-nums">{factCount}</span>
        {" "}Facts
      </span>
      <span data-testid="status-cluster-count" className="text-sm text-gray-500">
        <span className="font-semibold text-gray-900 tabular-nums">{clusterCount}</span>
        {" "}Clusters
      </span>
    </div>
  );
}
