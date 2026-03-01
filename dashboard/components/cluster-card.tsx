"use client";

import { useState, useEffect, memo } from "react";
import type { ClusterResponse } from "@/lib/types";

interface ClusterCardProps {
  cluster: ClusterResponse;
  hasLiveUpdate?: boolean;
  onClick: () => void;
}

// live_update_badge: pulsierender Dot (3s Animation, dann ausblenden)
// Wireframe Annotation: "Pulse animation on cluster card when new fact is added (not shown at rest)"
export const ClusterCard = memo(function ClusterCard({
  cluster,
  hasLiveUpdate = false,
  onClick,
}: ClusterCardProps) {
  const [showBadge, setShowBadge] = useState(false);

  useEffect(() => {
    if (hasLiveUpdate) {
      setShowBadge(true);
      const timer = setTimeout(() => setShowBadge(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [hasLiveUpdate]);

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`Cluster: ${cluster.name}, ${cluster.fact_count} facts`}
      data-testid="cluster-card"
      onClick={onClick}
      onKeyDown={(e) => e.key === "Enter" && onClick()}
      className="relative p-4 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-500 touch-action-manipulation"
    >
      {/* live_update_badge: pulsierender Dot -- nur sichtbar waehrend 3s Animation */}
      {showBadge && (
        <span
          aria-label="New fact added"
          aria-live="polite"
          data-testid="live-update-badge"
          className="absolute top-3 right-3 w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse"
        />
      )}

      <div className="flex items-start justify-between gap-2 mb-2">
        <h3
          data-testid="cluster-card-name"
          className="font-semibold text-gray-900 dark:text-gray-100 text-wrap-balance"
        >
          {cluster.name}
        </h3>
      </div>

      <div className="flex gap-4 text-sm text-gray-600 dark:text-gray-400 mb-3 tabular-nums">
        <span data-testid="cluster-fact-count">{cluster.fact_count} Facts</span>
        <span data-testid="cluster-interview-count">{cluster.interview_count} Interviews</span>
      </div>

      {cluster.summary !== null ? (
        <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-3">
          {cluster.summary}
        </p>
      ) : (
        <p className="text-sm text-gray-400 mt-2 italic">
          Generating summary...
        </p>
      )}
    </div>
  );
});
