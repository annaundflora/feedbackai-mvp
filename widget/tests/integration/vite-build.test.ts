/**
 * Integration Tests for Vite Build Configuration.
 * Validates that vite.config.ts produces correct build output.
 * These tests read actual config files and validate structure.
 */
import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'

const WIDGET_ROOT = path.resolve(__dirname, '..', '..')

describe('integration: Vite Build Config', () => {
  it('should have vite.config.ts with IIFE lib mode configuration', async () => {
    const configPath = path.join(WIDGET_ROOT, 'vite.config.ts')
    expect(fs.existsSync(configPath)).toBe(true)

    const content = fs.readFileSync(configPath, 'utf-8')
    // Must use lib mode
    expect(content).toContain('lib:')
    // Must output IIFE format
    expect(content).toContain("'iife'")
    // Must output widget.js
    expect(content).toContain("'widget.js'")
    // Must inline dynamic imports (no code splitting)
    expect(content).toContain('inlineDynamicImports: true')
    // Must not code-split CSS
    expect(content).toContain('cssCodeSplit: false')
  })

  it('should have tsconfig.json with React JSX and strict mode', () => {
    const tsconfigPath = path.join(WIDGET_ROOT, 'tsconfig.json')
    expect(fs.existsSync(tsconfigPath)).toBe(true)

    // tsconfig.json may contain comments (JSONC), so we validate via string matching
    const content = fs.readFileSync(tsconfigPath, 'utf-8')
    expect(content).toContain('"react-jsx"')
    expect(content).toContain('"strict": true')
    expect(content).toContain('"ES2020"')
  })

  it('should have widget.css with Tailwind v4 import and scoped styles', () => {
    const cssPath = path.join(WIDGET_ROOT, 'src', 'styles', 'widget.css')
    expect(fs.existsSync(cssPath)).toBe(true)

    const content = fs.readFileSync(cssPath, 'utf-8')
    // Tailwind v4 CSS-First config
    expect(content).toContain('@import "tailwindcss"')
    // Design tokens via @theme
    expect(content).toContain('@theme')
    // CSS scoping container
    expect(content).toContain('.feedbackai-widget')
    // CSS reset
    expect(content).toContain('all: initial')
  })

  it('should have main.tsx as IIFE entry point with singleton check', () => {
    const mainPath = path.join(WIDGET_ROOT, 'src', 'main.tsx')
    expect(fs.existsSync(mainPath)).toBe(true)

    const content = fs.readFileSync(mainPath, 'utf-8')
    // IIFE pattern
    expect(content).toContain('(function()')
    // Singleton check
    expect(content).toContain('.feedbackai-widget')
    // React mount
    expect(content).toContain('createRoot')
    // Config parsing
    expect(content).toContain('parseConfig')
  })

  it('should have test.html referencing dist/widget.js', () => {
    const testHtmlPath = path.join(WIDGET_ROOT, 'test.html')
    expect(fs.existsSync(testHtmlPath)).toBe(true)

    const content = fs.readFileSync(testHtmlPath, 'utf-8')
    expect(content).toContain('widget.js')
    expect(content).toContain('data-api-url')
    expect(content).toContain('data-lang')
  })
})
