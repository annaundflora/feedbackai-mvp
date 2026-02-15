import { ApiError } from './types'

export type ErrorAction = 'retry' | 'restart' | 'redirect_thankyou' | 'none'

export interface ClassifiedError {
  message: string
  action: ErrorAction
  status?: number
}

export function classifyError(error: unknown): ClassifiedError {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 404:
        return { message: 'Sitzung abgelaufen.', action: 'restart', status: 404 }
      case 409:
        return { message: 'Interview bereits beendet.', action: 'redirect_thankyou', status: 409 }
      default:
        return { message: 'Ein Fehler ist aufgetreten. Bitte später versuchen.', action: 'retry', status: error.status }
    }
  }

  if (error instanceof DOMException && error.name === 'AbortError') {
    return { message: 'Zeitüberschreitung. Server antwortet nicht.', action: 'retry' }
  }

  if (error instanceof TypeError && error.message.includes('fetch')) {
    return { message: 'Verbindung fehlgeschlagen. Bitte Netzwerk prüfen und erneut versuchen.', action: 'retry' }
  }

  return { message: 'Ein unerwarteter Fehler ist aufgetreten.', action: 'retry' }
}
