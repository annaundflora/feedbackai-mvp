export function LoadingIndicator() {
  return (
    <div
      className="flex flex-col items-center justify-center py-8"
      role="status"
      aria-label="Verbinde mit Server"
    >
      <div className="animate-[feedbackai-pulse_1.5s_ease-in-out_infinite] text-gray-500 text-sm motion-reduce:animate-none">
        Verbinde...
      </div>
    </div>
  )
}
