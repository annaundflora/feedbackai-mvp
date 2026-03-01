interface ProgressIndicatorProps {
  step: "extracting" | "assigning" | "validating" | "summarizing";
  completed: number;
  total: number;
}

const STEP_LABELS: Record<ProgressIndicatorProps["step"], string> = {
  extracting: "Extracting facts",
  assigning: "Assigning to clusters",
  validating: "Validating quality",
  summarizing: "Generating summaries",
};

export function ProgressIndicator({ step, completed, total }: ProgressIndicatorProps) {
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
  const label = `${STEP_LABELS[step]}... ${completed}/${total}`;

  return (
    <div
      role="status"
      aria-live="polite"
      aria-label={label}
      data-testid="progress-indicator"
      className="mb-4"
    >
      <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-1">
        <span data-testid="progress-label">{label}</span>
        <span data-testid="progress-pct" className="tabular-nums">{pct}%</span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden"
      >
        <div
          data-testid="progress-bar-fill"
          className="h-full bg-blue-500 rounded-full transition-[width] duration-300 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
