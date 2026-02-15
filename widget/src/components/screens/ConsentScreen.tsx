interface ConsentScreenProps {
  headline: string
  body: string
  ctaLabel: string
  onAccept: () => void
}

export function ConsentScreen({ headline, body, ctaLabel, onAccept }: ConsentScreenProps) {
  return (
    <div className="flex flex-col h-full screen-container">
      {/* Content Area */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-8 text-center">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          {headline}
        </h2>
        <p className="text-base text-gray-600 leading-relaxed max-w-md">
          {body}
        </p>
      </div>

      {/* CTA Button Area */}
      <div className="p-6 border-t border-gray-200">
        <button
          onClick={onAccept}
          className="
            w-full px-6 py-3 rounded-lg
            bg-brand text-white
            font-medium text-base
            hover:bg-brand-hover
            active:scale-95
            transition-all duration-200
            focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2
            touch-action-manipulation
          "
        >
          {ctaLabel}
        </button>
      </div>
    </div>
  )
}
