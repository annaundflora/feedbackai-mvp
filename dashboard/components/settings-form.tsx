// dashboard/components/settings-form.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { ProjectResponse } from "@/lib/types";
import { clientFetch } from "@/lib/client-api";

interface ResetSourceModalProps {
  project: ProjectResponse;
  onClose: () => void;
}

function ResetSourceModal({ project, onClose }: ResetSourceModalProps): JSX.Element {
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
            htmlFor="new-source-select"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            New Extraction Source
          </label>
          <select
            id="new-source-select"
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

interface SettingsFormProps {
  project: ProjectResponse;
}

export function SettingsForm({ project }: SettingsFormProps): JSX.Element {
  const [name, setName] = useState(project.name);
  const [researchGoal, setResearchGoal] = useState(project.research_goal);
  const [promptContext, setPromptContext] = useState(project.prompt_context ?? "");
  const [extractionSource, setExtractionSource] = useState<"summary" | "transcript">(project.extraction_source);
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showResetSourceModal, setShowResetSourceModal] = useState(false);

  const isValid = name.trim().length > 0 && researchGoal.trim().length > 0;

  async function handleSave(): Promise<void> {
    if (!isValid || !isDirty) return;
    setIsSaving(true);
    try {
      const promises: Promise<unknown>[] = [
        clientFetch(`/api/projects/${project.id}`, {
          method: "PUT",
          body: JSON.stringify({ name: name.trim(), research_goal: researchGoal.trim(), prompt_context: promptContext.trim() || null }),
        }),
      ];
      if (extractionSource !== project.extraction_source && !project.extraction_source_locked) {
        promises.push(
          clientFetch(`/api/projects/${project.id}/extraction-source`, {
            method: "PUT",
            body: JSON.stringify({ extraction_source: extractionSource }),
          }),
        );
      }
      await Promise.all(promises);
      setIsDirty(false);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="space-y-4" data-testid="settings-form">
      <div>
        <label htmlFor="project-name" className="block text-sm font-medium text-gray-700 mb-1">
          Project Name
        </label>
        <input
          id="project-name"
          type="text"
          value={name}
          onChange={(e) => { setName(e.target.value); setIsDirty(true); }}
          className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
          data-testid="settings-name-input"
        />
      </div>

      <div>
        <label htmlFor="research-goal" className="block text-sm font-medium text-gray-700 mb-1">
          Research Goal
        </label>
        <textarea
          id="research-goal"
          rows={3}
          value={researchGoal}
          onChange={(e) => { setResearchGoal(e.target.value); setIsDirty(true); }}
          className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
          data-testid="settings-research-goal-input"
        />
      </div>

      <div>
        <label htmlFor="prompt-context" className="block text-sm font-medium text-gray-700 mb-1">
          Prompt Context <span className="text-gray-400 font-normal">(optional)</span>
        </label>
        <textarea
          id="prompt-context"
          rows={4}
          value={promptContext}
          onChange={(e) => { setPromptContext(e.target.value); setIsDirty(true); }}
          className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
          data-testid="settings-prompt-context-input"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Fact Extraction Source
        </label>
        {project.extraction_source_locked ? (
          <div className="space-y-1">
            <div
              className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 bg-gray-50 text-gray-500 cursor-not-allowed"
              data-testid="extraction-source-locked"
            >
              <span className="flex-1 capitalize">{project.extraction_source}</span>
              <span aria-label="Locked" role="img">🔒</span>
            </div>
            <p className="text-xs text-gray-500">
              {project.fact_count} facts extracted with this source.{" "}
              <button
                type="button"
                onClick={() => setShowResetSourceModal(true)}
                className="text-blue-600 hover:underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-blue-500"
                data-testid="reset-source-link"
              >
                Reset &amp; Change Source
              </button>
            </p>
          </div>
        ) : (
          <select
            value={extractionSource}
            className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            data-testid="extraction-source-select"
            onChange={(e) => { setExtractionSource(e.target.value as "summary" | "transcript"); setIsDirty(true); }}
          >
            <option value="summary">Summary</option>
            <option value="transcript">Transcript</option>
          </select>
        )}
      </div>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={handleSave}
          disabled={!isValid || !isDirty || isSaving}
          className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          data-testid="settings-save-button"
        >
          {isSaving ? "Saving…" : "Save Changes"}
        </button>
      </div>

      {showResetSourceModal && (
        <ResetSourceModal
          project={project}
          onClose={() => setShowResetSourceModal(false)}
        />
      )}
    </div>
  );
}
