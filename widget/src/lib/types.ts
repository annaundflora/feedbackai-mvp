/** SSE Event types from backend */
export type SSEEvent =
  | { type: 'metadata'; session_id: string }
  | { type: 'text-delta'; content: string }
  | { type: 'text-done' }
  | { type: 'error'; message: string }

/** Response from POST /api/interview/end */
export interface EndResponse {
  summary: string
  message_count: number
}

/** API error with status code */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly detail?: string
  ) {
    super(message)
    this.name = 'ApiError'
  }
}
