// dashboard/components/model-config-form.tsx
"use client";

import { useState } from "react";
import type { ProjectResponse } from "@/lib/types";
import { clientFetch } from "@/lib/client-api";

interface ModelConfigFormProps {
  project: ProjectResponse;
}

const MODEL_FIELDS = [
  { key: "model_interviewer", label: "Interviewer Model" },
  { key: "model_extraction", label: "Fact Extraction Model" },
  { key: "model_clustering", label: "Clustering Model" },
  { key: "model_summary", label: "Summary Model" },
] as const;

type ModelKey = typeof MODEL_FIELDS[number]["key"];

export function ModelConfigForm({ project }: ModelConfigFormProps): JSX.Element {
  const [models, setModels] = useState<Record<ModelKey, string>>({
    model_interviewer: project.model_interviewer,
    model_extraction: project.model_extraction,
    model_clustering: project.model_clustering,
    model_summary: project.model_summary,
  });
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const isValid = Object.values(models).every((v) => v.trim().length > 0);

  async function handleSave(): Promise<void> {
    if (!isValid || !isDirty) return;
    setIsSaving(true);
    try {
      await clientFetch(`/api/projects/${project.id}/models`, {
        method: "PUT",
        body: JSON.stringify(models),
      });
      setIsDirty(false);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="space-y-4" data-testid="model-config-form">
      {MODEL_FIELDS.map(({ key, label }) => (
        <div key={key}>
          <label htmlFor={key} className="block text-sm font-medium text-gray-700 mb-1">
            {label}
          </label>
          <input
            id={key}
            type="text"
            value={models[key]}
            onChange={(e) => {
              setModels((m) => ({ ...m, [key]: e.target.value }));
              setIsDirty(true);
            }}
            spellCheck={false}
            placeholder="provider/model-name…"
            className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
            data-testid={`model-${key}-input`}
          />
          <p className="mt-1 text-xs text-gray-400">Format: provider/model-name</p>
        </div>
      ))}

      <div className="flex justify-end">
        <button
          type="button"
          onClick={handleSave}
          disabled={!isValid || !isDirty || isSaving}
          className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          data-testid="model-config-save-button"
        >
          {isSaving ? "Saving…" : "Save Changes"}
        </button>
      </div>
    </div>
  );
}
