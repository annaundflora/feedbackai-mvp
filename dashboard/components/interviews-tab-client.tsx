// dashboard/components/interviews-tab-client.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { InterviewAssignment } from "@/lib/types";
import { EmptyState } from "@/components/empty-state";
import { AssignInterviewsModal } from "@/components/assign-interviews-modal";
import { clientFetch } from "@/lib/client-api";

interface InterviewsTabClientProps {
  projectId: string;
  initialInterviews: InterviewAssignment[];
}

const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  completed: { label: "analyzed", className: "bg-green-100 text-green-700" },
  pending: { label: "pending", className: "bg-yellow-100 text-yellow-700" },
  running: { label: "pending", className: "bg-yellow-100 text-yellow-700" },
  failed: { label: "failed", className: "bg-red-100 text-red-700" },
};

type FilterStatus = "all" | "analyzed" | "pending" | "failed";
type FilterDateRange = "all" | "last-7-days" | "last-30-days";

export function InterviewsTabClient({
  projectId,
  initialInterviews,
}: InterviewsTabClientProps): JSX.Element {
  const router = useRouter();
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<FilterStatus>("all");
  const [filterDateRange, setFilterDateRange] = useState<FilterDateRange>("all");

  const filteredInterviews = initialInterviews.filter((iv) => {
    if (filterStatus !== "all") {
      const badge = STATUS_BADGE[iv.clustering_status] ?? STATUS_BADGE.pending;
      if (badge.label !== filterStatus) return false;
    }
    if (filterDateRange !== "all") {
      const days = filterDateRange === "last-7-days" ? 7 : 30;
      const cutoff = new Date();
      cutoff.setDate(cutoff.getDate() - days);
      if (new Date(iv.date) < cutoff) return false;
    }
    return true;
  });

  async function handleRetry(interviewId: string): Promise<void> {
    setRetryingId(interviewId);
    try {
      await clientFetch(`/api/projects/${projectId}/interviews/${interviewId}/retry`, {
        method: "POST",
      });
      router.refresh();
    } finally {
      setRetryingId(null);
    }
  }

  if (initialInterviews.length === 0) {
    return (
      <div>
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-base font-semibold text-gray-900">Interviews</h2>
          <button
            onClick={() => setShowAssignModal(true)}
            className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 transition-colors"
            data-testid="assign-interviews-button"
          >
            + Assign Interviews
          </button>
        </div>
        <EmptyState variant="interviews" onAction={() => setShowAssignModal(true)} />
        {showAssignModal && (
          <AssignInterviewsModal
            projectId={projectId}
            onClose={() => setShowAssignModal(false)}
            onAssigned={() => { setShowAssignModal(false); router.refresh(); }}
          />
        )}
      </div>
    );
  }

  return (
    <div data-testid="interviews-tab">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-base font-semibold text-gray-900">Interviews</h2>
        <div className="flex items-center gap-2">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as FilterStatus)}
            className="px-2 py-1.5 rounded-lg border border-gray-300 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            data-testid="interview-filter-status"
            aria-label="Filter by status"
          >
            <option value="all">All Statuses</option>
            <option value="analyzed">Analyzed</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
          </select>
          <select
            value={filterDateRange}
            onChange={(e) => setFilterDateRange(e.target.value as FilterDateRange)}
            className="px-2 py-1.5 rounded-lg border border-gray-300 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            data-testid="interview-filter-date"
            aria-label="Filter by date range"
          >
            <option value="all">All Time</option>
            <option value="last-7-days">Last 7 Days</option>
            <option value="last-30-days">Last 30 Days</option>
          </select>
          <button
            onClick={() => setShowAssignModal(true)}
            className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 transition-colors"
            data-testid="assign-interviews-button"
          >
            + Assign Interviews
          </button>
        </div>
      </div>

      <div className="border border-gray-200 rounded-xl overflow-hidden">
        <table className="w-full text-sm" data-testid="interviews-table">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">#</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Date</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Summary</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Facts</th>
              <th scope="col" className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filteredInterviews.map((interview, index) => {
              const badge = STATUS_BADGE[interview.clustering_status] ?? STATUS_BADGE.pending;
              const isFailed = interview.extraction_status === "failed" || interview.clustering_status === "failed";
              return (
                <tr
                  key={interview.interview_id}
                  className="hover:bg-gray-50 transition-colors cursor-pointer"
                  role="link"
                  tabIndex={0}
                  onClick={() => router.push(`/projects/${projectId}/interviews/${interview.interview_id}`)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      router.push(`/projects/${projectId}/interviews/${interview.interview_id}`);
                    }
                  }}
                >
                  <td className="px-4 py-3 text-gray-500 tabular-nums">#{index + 1}</td>
                  <td className="px-4 py-3 text-gray-600 whitespace-nowrap">
                    {new Date(interview.date).toLocaleDateString("en-US", {
                      year: "numeric", month: "short", day: "numeric",
                    })}
                  </td>
                  <td className="px-4 py-3 text-gray-700 max-w-xs">
                    <span className="line-clamp-2">{interview.summary_preview ?? "—"}</span>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-600 tabular-nums">{interview.fact_count}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${badge.className}`}
                        data-testid={`interview-status-${interview.interview_id}`}
                      >
                        {badge.label}
                      </span>
                      {isFailed && (
                        <button
                          onClick={(e) => { e.stopPropagation(); void handleRetry(interview.interview_id); }}
                          disabled={retryingId === interview.interview_id}
                          aria-label="Retry processing"
                          className="text-gray-400 hover:text-gray-600 focus-visible:ring-1 focus-visible:ring-gray-400 rounded disabled:opacity-50 transition-colors"
                          data-testid={`retry-button-${interview.interview_id}`}
                        >
                          {retryingId === interview.interview_id ? "↻…" : "↻"}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-xs text-gray-400">
        Status: analyzed = fully processed &nbsp;·&nbsp; pending = in queue &nbsp;·&nbsp; failed = processing error
      </p>

      {showAssignModal && (
        <AssignInterviewsModal
          projectId={projectId}
          onClose={() => setShowAssignModal(false)}
          onAssigned={() => { setShowAssignModal(false); router.refresh(); }}
        />
      )}
    </div>
  );
}
