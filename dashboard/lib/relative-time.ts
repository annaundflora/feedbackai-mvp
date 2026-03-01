export function formatRelativeTime(isoString: string): string {
  const now = Date.now()
  const then = new Date(isoString).getTime()
  const diffMs = now - then
  const diffMin = Math.floor(diffMs / 60_000)
  const diffHours = Math.floor(diffMs / 3_600_000)
  const diffDays = Math.floor(diffMs / 86_400_000)
  const diffMonths = Math.floor(diffDays / 30)

  if (diffMin < 1) return 'Updated just now'
  if (diffMin < 60) return `Updated ${diffMin}m ago`
  if (diffHours < 24) return `Updated ${diffHours}h ago`
  if (diffDays < 30) return `Updated ${diffDays}d ago`
  return `Updated ${diffMonths} month${diffMonths > 1 ? 's' : ''} ago`
}
