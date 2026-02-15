import { ComposerPrimitive } from '@assistant-ui/react'

interface ChatComposerProps {
  placeholder?: string
  disabled?: boolean
}

export function ChatComposer({ placeholder = 'Nachricht eingeben...', disabled = false }: ChatComposerProps) {
  return (
    <ComposerPrimitive.Root className="p-4">
      <div className="flex gap-2 items-end">
        {/* Input Field */}
        <ComposerPrimitive.Input
          placeholder={placeholder}
          disabled={disabled}
          className="
            flex-1 px-4 py-3 rounded-xl
            bg-gray-100 text-gray-900
            placeholder:text-gray-500
            text-sm
            resize-none
            focus:outline-none focus:ring-2 focus:ring-brand focus:bg-white
            transition-all duration-200
            max-h-32
            composer-input
            disabled:opacity-50 disabled:cursor-not-allowed
          "
          rows={1}
          autoFocus={false}
        />

        {/* Send Button */}
        <ComposerPrimitive.Send
          disabled={disabled}
          className="
            flex-shrink-0 w-10 h-10 rounded-xl
            bg-brand text-white
            flex items-center justify-center
            hover:bg-brand-hover
            active:scale-95
            transition-all duration-200
            disabled:opacity-50 disabled:cursor-not-allowed
            focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2
            touch-action-manipulation
          "
          aria-label="Nachricht senden"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="w-5 h-5"
            aria-hidden="true"
          >
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </ComposerPrimitive.Send>
      </div>
    </ComposerPrimitive.Root>
  )
}
