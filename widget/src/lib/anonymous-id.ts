const STORAGE_KEY = 'feedbackai_anonymous_id'

export function getOrCreateAnonymousId(): string {
  try {
    const existing = localStorage.getItem(STORAGE_KEY)
    if (existing) return existing

    const id = crypto.randomUUID()
    localStorage.setItem(STORAGE_KEY, id)
    return id
  } catch {
    // localStorage blocked (SecurityError) - generate without persistence
    return crypto.randomUUID()
  }
}
