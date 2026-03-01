'use client'

import { useState, useRef, useEffect } from 'react'

interface InlineRenameProps {
  initialName: string
  onSave: (name: string) => Promise<void>
  onCancel: () => void
  isLoading?: boolean
}

export function InlineRename({
  initialName,
  onSave,
  onCancel,
  isLoading = false,
}: InlineRenameProps) {
  const [value, setValue] = useState(initialName)
  const inputRef = useRef<HTMLInputElement>(null)
  const isValid = value.trim().length >= 1 && value.trim().length <= 200

  useEffect(() => {
    inputRef.current?.focus()
    inputRef.current?.select()
  }, [])

  async function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && isValid && !isLoading) {
      await onSave(value.trim())
    } else if (e.key === 'Escape') {
      onCancel()
    }
  }

  return (
    <div className="flex flex-col gap-1" data-testid="inline-rename">
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isLoading}
        aria-label="Cluster name"
        maxLength={200}
        className="px-2 py-1 text-sm border border-blue-400 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        data-testid="rename-input"
      />
      <div className="flex gap-2">
        <button
          onClick={() => isValid && !isLoading && onSave(value.trim())}
          disabled={!isValid || isLoading}
          aria-label="Save cluster name"
          className="px-2 py-0.5 text-xs bg-blue-600 text-white rounded disabled:opacity-50 hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500"
          data-testid="rename-save"
        >
          {isLoading ? 'Saving...' : 'Save'}
        </button>
        <button
          onClick={onCancel}
          disabled={isLoading}
          aria-label="Cancel rename"
          className="px-2 py-0.5 text-xs border border-gray-300 rounded hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-gray-400"
          data-testid="rename-cancel"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}
