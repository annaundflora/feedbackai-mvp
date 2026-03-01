// dashboard/components/danger-zone.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { clientFetch } from "@/lib/client-api";

interface DangerZoneProps {
  projectId: string;
  projectName: string;
}

export function DangerZone({ projectId, projectName }: DangerZoneProps): JSX.Element {
  const router = useRouter();
  const [showModal, setShowModal] = useState(false);
  const [confirmInput, setConfirmInput] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  const isConfirmed = confirmInput === projectName;

  async function handleDelete(): Promise<void> {
    if (!isConfirmed) return;
    setIsDeleting(true);
    try {
      await clientFetch(`/api/projects/${projectId}`, { method: "DELETE" });
      router.replace("/projects");
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <div
      className="border border-red-200 rounded-xl p-5 bg-red-50"
      data-testid="danger-zone"
    >
      <p className="text-sm text-gray-700 mb-3">
        Delete this project and all its clusters and facts. This action cannot be undone.
      </p>
      <button
        type="button"
        onClick={() => setShowModal(true)}
        className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-500 transition-colors"
        data-testid="delete-project-button"
      >
        Delete Project
      </button>

      {showModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
          data-testid="delete-confirm-modal"
        >
          <div className="bg-white rounded-xl border border-gray-200 shadow-xl w-full max-w-md p-6">
            <h3 id="delete-modal-title" className="text-base font-semibold text-gray-900 mb-1">
              Delete Project
            </h3>
            <p className="text-sm text-red-600 font-medium mb-3">This action is permanent</p>

            <p className="text-sm text-gray-600 mb-4">
              Type the project name to confirm deletion of <strong>{projectName}</strong>:
            </p>

            <input
              type="text"
              value={confirmInput}
              onChange={(e) => setConfirmInput(e.target.value)}
              placeholder={projectName}
              aria-label="Type project name to confirm"
              className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-red-500 mb-4"
              data-testid="delete-confirm-input"
            />

            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => { setShowModal(false); setConfirmInput(""); }}
                disabled={isDeleting}
                className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 text-sm font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors"
                data-testid="delete-cancel-button"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDelete}
                disabled={!isConfirmed || isDeleting}
                className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                data-testid="delete-confirm-button"
              >
                {isDeleting ? "Deleting…" : "Delete Project"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
