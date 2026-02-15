import '@testing-library/jest-dom/vitest'

// Polyfill ResizeObserver for @assistant-ui/react tests
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
