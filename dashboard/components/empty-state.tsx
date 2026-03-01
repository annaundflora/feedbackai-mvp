// dashboard/components/empty-state.tsx

// ─── Variant-based API (Slice 8) ─────────────────────────────────────────────

interface EmptyStateVariantProps {
  variant: "projects" | "clusters" | "facts" | "interviews";
  onAction?: () => void;
  'data-testid'?: string;
}

const EMPTY_STATE_CONFIG = {
  projects: {
    icon: "📋",
    title: "No projects yet",
    description: "Create your first project to start analyzing interview insights.",
    action: "Create Project",
  },
  clusters: {
    icon: "🔍",
    title: "No clusters yet",
    description: "Assign interviews to this project to start generating insights.",
    action: "Assign Interviews",
  },
  facts: {
    icon: "💡",
    title: "No facts extracted yet",
    description: "Facts will appear here once interview processing is complete.",
    action: null,
  },
  interviews: {
    icon: "🎙",
    title: "No interviews assigned",
    description: "Assign interviews to start extracting insights for this project.",
    action: "Assign Interviews",
  },
} as const;

function EmptyStateVariant({ variant, onAction, 'data-testid': testId }: EmptyStateVariantProps): JSX.Element {
  const config = EMPTY_STATE_CONFIG[variant];

  return (
    <div
      className="flex flex-col items-center justify-center py-16 px-4 text-center"
      data-testid={testId ?? `empty-state-${variant}`}
    >
      <span className="text-5xl mb-4" role="img" aria-hidden="true">
        {config.icon}
      </span>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{config.title}</h3>
      <p className="text-sm text-gray-500 max-w-xs mb-6">{config.description}</p>
      {config.action !== null && onAction !== undefined && (
        <button
          onClick={onAction}
          className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 transition-colors touch-action-manipulation"
          data-testid={`empty-state-${variant}-action`}
        >
          {config.action}
        </button>
      )}
    </div>
  );
}

// ─── Legacy message-based API (Slice 4/5/6) ──────────────────────────────────

interface EmptyStateLegacyProps {
  message: string;
  ctaLabel?: string;
  ctaHref?: string;
  'data-testid'?: string;
}

function EmptyStateLegacy({
  message,
  ctaLabel,
  ctaHref,
  'data-testid': testId,
}: EmptyStateLegacyProps): JSX.Element {
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
            onClick={() => document.dispatchEvent(new CustomEvent('open-new-project-dialog'))}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 text-sm font-medium transition-colors"
          >
            {ctaLabel}
          </button>
        )
      )}
    </div>
  );
}

// ─── Unified EmptyState (supports both APIs) ──────────────────────────────────

type EmptyStateProps = EmptyStateVariantProps | EmptyStateLegacyProps;

export function EmptyState(props: EmptyStateProps): JSX.Element {
  if ('variant' in props) {
    return <EmptyStateVariant {...props} />;
  }
  return <EmptyStateLegacy {...props} />;
}
