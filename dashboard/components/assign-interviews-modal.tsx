// dashboard/components/assign-interviews-modal.tsx
"use client";

import { useEffect, useState } from "react";
import type { AvailableInterview } from "@/lib/types";
import { clientFetch } from "@/lib/client-api";

interface AssignInterviewsModalProps {
  projectId: string;
  onClose: () => void;
  onAssigned: () => void;
}

export function AssignInterviewsModal({
  projectId,
  onClose,
  onAssigned,
}: AssignInterviewsModalProps): JSX.Element {
  const [available, setAvailable] = useState<AvailableInterview[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [isAssigning, setIsAssigning] = useState(false);

  useEffect(() => {
    async function load(): Promise<void> {
      const data = await clientFetch<AvailableInterview[]>(
        `/api/projects/${projectId}/interviews/available`,
      );
      setAvailable(data);
      setIsLoading(false);
    }
    void load();
  }, [projectId]);

  function toggleSelection(id: string): void {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  async function handleAssign(): Promise<void> {
    if (selected.size === 0) return;
    setIsAssigning(true);
    try {
      await clientFetch(`/api/projects/${projectId}/interviews`, {
        method: "POST",
        body: JSON.stringify({ interview_ids: Array.from(selected) }),
      });
      onAssigned();
    } finally {
      setIsAssigning(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="assign-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
      data-testid="assign-interviews-modal"
    >
      <div className="bg-white rounded-xl border border-gray-200 shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 id="assign-modal-title" className="text-base font-semibold text-gray-900">
            Assign Interviews
          </h3>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="text-gray-400 hover:text-gray-600 focus-visible:ring-1 focus-visible:ring-gray-400 rounded transition-colors"
            data-testid="assign-modal-close"
          >
            ✕
          </button>
        </div>

        <div className="px-6 py-4 max-h-80 overflow-y-auto overscroll-contain">
          {isLoading ? (
            <div className="text-sm text-gray-500 text-center py-4">Loading interviews…</div>
          ) : available.length === 0 ? (
            <div className="text-sm text-gray-500 text-center py-4">
              No unassigned interviews available.
            </div>
          ) : (
            <div className="space-y-2">
              {available.map((interview) => (
                <label
                  key={interview.session_id}
                  className="flex items-start gap-3 cursor-pointer p-2 rounded-lg hover:bg-gray-50 transition-colors"
                  data-testid={`assign-checkbox-${interview.session_id}`}
                >
                  <input
                    type="checkbox"
                    checked={selected.has(interview.session_id)}
                    onChange={() => toggleSelection(interview.session_id)}
                    className="mt-0.5 cursor-pointer"
                  />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900">
                      {new Date(interview.created_at).toLocaleDateString("en-US", {
                        year: "numeric", month: "short", day: "numeric",
                      })}
                    </p>
                    {interview.summary_preview !== null && (
                      <p className="text-xs text-gray-500 truncate">{interview.summary_preview}</p>
                    )}
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-100">
          <span className="text-sm text-gray-500">
            {selected.size > 0 ? `${selected.size} selected` : ""}
          </span>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isAssigning}
              className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 text-sm font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors"
              data-testid="assign-modal-cancel"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleAssign}
              disabled={selected.size === 0 || isAssigning}
              className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              data-testid="assign-modal-confirm"
            >
              {isAssigning ? "Assigning…" : "Assign Selected"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
