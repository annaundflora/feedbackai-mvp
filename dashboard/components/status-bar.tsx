interface StatusBarProps {
  interviewCount: number
  factCount: number
  clusterCount: number
}

export function StatusBar({ interviewCount, factCount, clusterCount }: StatusBarProps) {
  return (
    <div
      data-testid="status-bar"
      className="flex gap-6 text-sm text-gray-600 border-b pb-3 mb-6"
    >
      <span data-testid="status-interview-count">{interviewCount} Interviews</span>
      <span data-testid="status-fact-count">{factCount} Facts</span>
      <span data-testid="status-cluster-count">{clusterCount} Clusters</span>
    </div>
  )
}
