// dashboard/components/reset-source-modal.tsx
// Note: This component is also included inline in settings-form.tsx.
// This file exports it as a standalone module for import flexibility.
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { ProjectResponse } from "@/lib/types";
import { clientFetch } from "@/lib/client-api";

interface ResetSourceModalProps {
  project: ProjectResponse;
  onClose: () => void;
}

export function ResetSourceModal({ project, onClose }: ResetSourceModalProps): JSX.Element {
  const router = useRouter();
  const otherSource = project.extraction_source === "summary" ? "transcript" : "summary";
  const [newSource, setNewSource] = useState<"summary" | "transcript">(otherSource);
  const [reExtract, setReExtract] = useState(false);
  const [isChanging, setIsChanging] = useState(false);

  async function handleChange(): Promise<void> {
    setIsChanging(true);
    try {
      await clientFetch(`/api/projects/${project.id}/extraction-source`, {
        method: "PUT",
        body: JSON.stringify({ extraction_source: newSource, re_extract: reExtract }),
      });
      router.refresh();
      onClose();
    } finally {
      setIsChanging(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      data-testid="reset-source-modal"
    >
      <div className="bg-white rounded-xl shadow-xl max-w-sm w-full p-6">
        <h3 className="text-base font-semibold text-gray-900 mb-2">
          Change Extraction Source
        </h3>
        <p className="text-sm text-gray-600 mb-4">
          {project.fact_count} facts were extracted from{" "}
          <strong>{project.extraction_source}s</strong>. Changing to a different
          source will only affect future interviews. Existing facts remain unchanged.
        </p>
        <div className="mb-3">
          <label
            htmlFor="reset-source-select"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            New Extraction Source
          </label>
          <select
            id="reset-source-select"
            value={newSource}
            onChange={(e) => setNewSource(e.target.value as "summary" | "transcript")}
            className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            data-testid="new-source-select"
          >
            <option value="summary">Summary</option>
            <option value="transcript">Transcript</option>
          </select>
        </div>
        <label className="flex items-center gap-2 mb-4 cursor-pointer">
          <input
            type="checkbox"
            checked={reExtract}
            onChange={(e) => setReExtract(e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            data-testid="re-extract-checkbox"
          />
          <span className="text-sm text-gray-700">
            Also re-extract all existing facts with the new source
          </span>
        </label>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 text-sm text-gray-700 hover:text-gray-900"
            data-testid="reset-source-cancel"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleChange}
            disabled={isChanging}
            className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
            data-testid="reset-source-confirm"
          >
            {isChanging ? "Changing…" : "Change Source"}
          </button>
        </div>
      </div>
    </div>
  );
}
