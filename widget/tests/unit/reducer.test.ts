/**
 * Unit Tests for widget/src/reducer.ts
 *
 * Tests the widgetReducer state machine in isolation.
 * Covers all 5 actions, initial state, and state dimension independence.
 *
 * Derived from Slice-03 Acceptance Criteria (AC-8 especially):
 *   "GIVEN State-Transitions WHEN Actions dispatched werden
 *    THEN Nur die relevante State-Dimension aendert sich"
 */
import { describe, it, expect } from 'vitest'
import {
  widgetReducer,
  initialState,
  type WidgetState,
  type WidgetAction,
} from '../../src/reducer'

describe('unit: widgetReducer', () => {
  describe('initialState', () => {
    it('should have panelOpen=false and screen=consent', () => {
      expect(initialState).toEqual({
        panelOpen: false,
        screen: 'consent',
      })
    })
  })

  describe('OPEN_PANEL action', () => {
    it('should set panelOpen to true', () => {
      const state: WidgetState = { panelOpen: false, screen: 'consent' }
      const result = widgetReducer(state, { type: 'OPEN_PANEL' })
      expect(result.panelOpen).toBe(true)
    })

    it('should NOT change screen when opening panel', () => {
      const state: WidgetState = { panelOpen: false, screen: 'chat' }
      const result = widgetReducer(state, { type: 'OPEN_PANEL' })
      expect(result.screen).toBe('chat')
      expect(result.panelOpen).toBe(true)
    })

    it('should preserve screen=thankyou when opening panel', () => {
      const state: WidgetState = { panelOpen: false, screen: 'thankyou' }
      const result = widgetReducer(state, { type: 'OPEN_PANEL' })
      expect(result.screen).toBe('thankyou')
    })
  })

  describe('CLOSE_PANEL action', () => {
    it('should set panelOpen to false', () => {
      const state: WidgetState = { panelOpen: true, screen: 'consent' }
      const result = widgetReducer(state, { type: 'CLOSE_PANEL' })
      expect(result.panelOpen).toBe(false)
    })

    it('should NOT change screen when closing panel', () => {
      const state: WidgetState = { panelOpen: true, screen: 'chat' }
      const result = widgetReducer(state, { type: 'CLOSE_PANEL' })
      expect(result.screen).toBe('chat')
      expect(result.panelOpen).toBe(false)
    })

    it('should preserve screen=consent when closing panel', () => {
      const state: WidgetState = { panelOpen: true, screen: 'consent' }
      const result = widgetReducer(state, { type: 'CLOSE_PANEL' })
      expect(result.screen).toBe('consent')
    })
  })

  describe('GO_TO_CHAT action', () => {
    it('should set screen to chat', () => {
      const state: WidgetState = { panelOpen: true, screen: 'consent' }
      const result = widgetReducer(state, { type: 'GO_TO_CHAT' })
      expect(result.screen).toBe('chat')
    })

    it('should NOT change panelOpen', () => {
      const state: WidgetState = { panelOpen: true, screen: 'consent' }
      const result = widgetReducer(state, { type: 'GO_TO_CHAT' })
      expect(result.panelOpen).toBe(true)
    })

    it('should NOT change panelOpen even when panel is closed', () => {
      const state: WidgetState = { panelOpen: false, screen: 'consent' }
      const result = widgetReducer(state, { type: 'GO_TO_CHAT' })
      expect(result.panelOpen).toBe(false)
      expect(result.screen).toBe('chat')
    })
  })

  describe('GO_TO_THANKYOU action', () => {
    it('should set screen to thankyou', () => {
      const state: WidgetState = { panelOpen: true, screen: 'chat' }
      const result = widgetReducer(state, { type: 'GO_TO_THANKYOU' })
      expect(result.screen).toBe('thankyou')
    })

    it('should NOT change panelOpen', () => {
      const state: WidgetState = { panelOpen: true, screen: 'chat' }
      const result = widgetReducer(state, { type: 'GO_TO_THANKYOU' })
      expect(result.panelOpen).toBe(true)
    })
  })

  describe('CLOSE_AND_RESET action', () => {
    it('should set panelOpen to false AND screen to consent', () => {
      const state: WidgetState = { panelOpen: true, screen: 'thankyou' }
      const result = widgetReducer(state, { type: 'CLOSE_AND_RESET' })
      expect(result).toEqual({
        panelOpen: false,
        screen: 'consent',
      })
    })

    it('should reset from chat screen as well', () => {
      const state: WidgetState = { panelOpen: true, screen: 'chat' }
      const result = widgetReducer(state, { type: 'CLOSE_AND_RESET' })
      expect(result.panelOpen).toBe(false)
      expect(result.screen).toBe('consent')
    })

    it('should be idempotent when already in initial state', () => {
      const result = widgetReducer(initialState, { type: 'CLOSE_AND_RESET' })
      expect(result).toEqual(initialState)
    })
  })

  describe('unknown action', () => {
    it('should return current state for unknown action type', () => {
      const state: WidgetState = { panelOpen: true, screen: 'chat' }
      // @ts-expect-error - testing unknown action type
      const result = widgetReducer(state, { type: 'UNKNOWN_ACTION' })
      expect(result).toEqual(state)
    })
  })

  describe('state dimension independence (AC-8)', () => {
    it('OPEN_PANEL and CLOSE_PANEL only affect panelOpen, never screen', () => {
      const screens = ['consent', 'chat', 'thankyou'] as const
      for (const screen of screens) {
        const openResult = widgetReducer(
          { panelOpen: false, screen },
          { type: 'OPEN_PANEL' }
        )
        expect(openResult.screen).toBe(screen)

        const closeResult = widgetReducer(
          { panelOpen: true, screen },
          { type: 'CLOSE_PANEL' }
        )
        expect(closeResult.screen).toBe(screen)
      }
    })

    it('GO_TO_CHAT and GO_TO_THANKYOU only affect screen, never panelOpen', () => {
      for (const panelOpen of [true, false]) {
        const chatResult = widgetReducer(
          { panelOpen, screen: 'consent' },
          { type: 'GO_TO_CHAT' }
        )
        expect(chatResult.panelOpen).toBe(panelOpen)

        const thankyouResult = widgetReducer(
          { panelOpen, screen: 'chat' },
          { type: 'GO_TO_THANKYOU' }
        )
        expect(thankyouResult.panelOpen).toBe(panelOpen)
      }
    })

    it('only CLOSE_AND_RESET changes both dimensions simultaneously', () => {
      const state: WidgetState = { panelOpen: true, screen: 'thankyou' }
      const result = widgetReducer(state, { type: 'CLOSE_AND_RESET' })
      // Both dimensions changed
      expect(result.panelOpen).not.toBe(state.panelOpen)
      expect(result.screen).not.toBe(state.screen)
    })
  })

  describe('full user flow transitions', () => {
    it('should support consent -> chat -> thankyou -> reset flow', () => {
      let state = initialState

      // Open panel
      state = widgetReducer(state, { type: 'OPEN_PANEL' })
      expect(state).toEqual({ panelOpen: true, screen: 'consent' })

      // Accept consent -> go to chat
      state = widgetReducer(state, { type: 'GO_TO_CHAT' })
      expect(state).toEqual({ panelOpen: true, screen: 'chat' })

      // Interview ends -> go to thankyou
      state = widgetReducer(state, { type: 'GO_TO_THANKYOU' })
      expect(state).toEqual({ panelOpen: true, screen: 'thankyou' })

      // Auto-close and reset
      state = widgetReducer(state, { type: 'CLOSE_AND_RESET' })
      expect(state).toEqual({ panelOpen: false, screen: 'consent' })
    })

    it('should persist screen state across panel close/reopen', () => {
      let state: WidgetState = { panelOpen: true, screen: 'chat' }

      // Close panel
      state = widgetReducer(state, { type: 'CLOSE_PANEL' })
      expect(state).toEqual({ panelOpen: false, screen: 'chat' })

      // Reopen panel - screen should still be chat
      state = widgetReducer(state, { type: 'OPEN_PANEL' })
      expect(state).toEqual({ panelOpen: true, screen: 'chat' })
    })
  })
})
