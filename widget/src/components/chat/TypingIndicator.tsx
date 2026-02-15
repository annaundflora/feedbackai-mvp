export function TypingIndicator() {
  return (
    <div className="flex items-start gap-2 px-4 py-2" aria-label="Antwort wird generiert">
      <div className="bg-gray-100 rounded-xl px-4 py-3 flex gap-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-2 h-2 bg-gray-400 rounded-full animate-[feedbackai-bounce_1s_ease-in-out_infinite] motion-reduce:animate-none"
            style={{ animationDelay: `${i * 0.2}s` }}
          />
        ))}
      </div>
    </div>
  )
}
