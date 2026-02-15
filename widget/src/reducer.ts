export type WidgetScreen = 'consent' | 'chat' | 'thankyou'

export interface WidgetState {
  panelOpen: boolean
  screen: WidgetScreen
}

export const initialState: WidgetState = {
  panelOpen: false,
  screen: 'consent'
}

export type WidgetAction =
  | { type: 'OPEN_PANEL' }
  | { type: 'CLOSE_PANEL' }
  | { type: 'GO_TO_CHAT' }
  | { type: 'GO_TO_THANKYOU' }
  | { type: 'CLOSE_AND_RESET' }

export function widgetReducer(state: WidgetState, action: WidgetAction): WidgetState {
  switch (action.type) {
    case 'OPEN_PANEL':
      return {
        ...state,
        panelOpen: true
        // screen bleibt unverändert
      }

    case 'CLOSE_PANEL':
      return {
        ...state,
        panelOpen: false
        // screen bleibt unverändert
      }

    case 'GO_TO_CHAT':
      return {
        ...state,
        screen: 'chat'
        // panelOpen bleibt unverändert
      }

    case 'GO_TO_THANKYOU':
      return {
        ...state,
        screen: 'thankyou'
        // panelOpen bleibt unverändert
      }

    case 'CLOSE_AND_RESET':
      return {
        panelOpen: false,
        screen: 'consent'
        // Reset für neues Interview
      }

    default:
      return state
  }
}
