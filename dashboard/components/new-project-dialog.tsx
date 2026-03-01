'use client'

import { useRouter } from 'next/navigation'
import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '@/lib/api-client'

export function NewProjectDialog() {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [researchGoal, setResearchGoal] = useState('')
  const [promptContext, setPromptContext] = useState('')
  const [extractionSource, setExtractionSource] = useState<'summary' | 'transcript'>('summary')

  const isValid = name.trim().length > 0 && researchGoal.trim().length > 0

  const handleClose = useCallback(() => {
    setOpen(false)
    setError(null)
    setName('')
    setResearchGoal('')
    setPromptContext('')
    setExtractionSource('summary')
  }, [])

  // Close on Escape key
  useEffect(() => {
    if (!open) return
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') handleClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, handleClose])

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!isValid) return
    setSaving(true)
    setError(null)
    try {
      await apiClient.createProject({
        name: name.trim(),
        research_goal: researchGoal.trim(),
        prompt_context: promptContext.trim() || undefined,
        extraction_source: extractionSource,
      })
      router.refresh()
      handleClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <button
        type="button"
        data-testid="new-project-btn"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 text-sm font-medium transition-colors"
      >
        + New Project
      </button>

      {open && (
        // Backdrop — close on click outside
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={e => { if (e.target === e.currentTarget) handleClose() }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="dialog-title"
            data-testid="new-project-dialog"
            className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 p-6"
          >
            <h2 id="dialog-title" className="text-xl font-bold text-gray-900 mb-6">
              New Project
            </h2>

            <form data-testid="new-project-form" onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="project-name"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Project Name <span aria-hidden="true">*</span>
                </label>
                <input
                  id="project-name"
                  name="name"
                  data-testid="project-name-input"
                  type="text"
                  required
                  maxLength={200}
                  placeholder="e.g. Onboarding UX Research"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  disabled={saving}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none disabled:bg-gray-50"
                />
              </div>

              <div>
                <label
                  htmlFor="research-goal"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Research Goal <span aria-hidden="true">*</span>
                </label>
                <textarea
                  id="research-goal"
                  name="research_goal"
                  data-testid="research-goal-input"
                  required
                  maxLength={2000}
                  rows={3}
                  placeholder="e.g. Understand why users drop off during onboarding"
                  value={researchGoal}
                  onChange={e => setResearchGoal(e.target.value)}
                  disabled={saving}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none disabled:bg-gray-50 resize-y"
                />
              </div>

              <div>
                <label
                  htmlFor="prompt-context"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Prompt Context <span className="text-gray-400">(optional)</span>
                </label>
                <textarea
                  id="prompt-context"
                  name="prompt_context"
                  data-testid="prompt-context-input"
                  maxLength={5000}
                  rows={3}
                  placeholder="Additional context for the LLM clustering model"
                  value={promptContext}
                  onChange={e => setPromptContext(e.target.value)}
                  disabled={saving}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none disabled:bg-gray-50 resize-y"
                />
              </div>

              <div>
                <label
                  htmlFor="extraction-source"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Fact Extraction Source
                </label>
                <select
                  id="extraction-source"
                  name="extraction_source"
                  data-testid="extraction-source-select"
                  value={extractionSource}
                  onChange={e => setExtractionSource(e.target.value as 'summary' | 'transcript')}
                  disabled={saving}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none disabled:bg-gray-50"
                >
                  <option value="summary">Summary</option>
                  <option value="transcript">Transcript</option>
                </select>
              </div>

              {error !== null && (
                <p role="alert" className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">
                  {error}
                </p>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleClose}
                  disabled={saving}
                  className="px-4 py-2 text-sm text-gray-700 hover:text-gray-900 focus-visible:ring-2 focus-visible:ring-blue-500 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  data-testid="create-project-submit"
                  disabled={!isValid || saving}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? (
                    <>
                      <svg
                        className="animate-spin h-4 w-4"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                        />
                      </svg>
                      Creating…
                    </>
                  ) : (
                    'Create Project'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}
