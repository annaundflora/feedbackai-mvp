import { XIcon } from './icons/XIcon'

interface PanelHeaderProps {
  title: string
  onClose: () => void
}

export function PanelHeader({ title, onClose }: PanelHeaderProps) {
  return (
    <header
      className="
        flex items-center justify-between
        px-[var(--panel-padding)] py-4
        border-b border-gray-200
      "
    >
      <h2
        id="panel-title"
        className="text-lg font-semibold text-gray-900"
      >
        {title}
      </h2>
      <button
        onClick={onClose}
        aria-label="Panel schließen"
        className="
          w-8 h-8 rounded-lg
          flex items-center justify-center
          hover:bg-gray-100
          transition-colors
          focus-visible:ring-2 focus-visible:ring-gray-500
          touch-action-manipulation
        "
      >
        <XIcon className="w-5 h-5 text-gray-500" />
      </button>
    </header>
  )
}
