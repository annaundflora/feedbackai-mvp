/**
 * Unit Tests for widget/src/config.ts
 * Tests parseConfig() and findWidgetScript() in isolation.
 * All DOM interactions are mocked via jsdom.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { parseConfig, findWidgetScript, type WidgetConfig, type WidgetLang } from '../../src/config'

describe('unit: parseConfig', () => {
  /**
   * Helper to create a mock script element with optional data attributes.
   */
  function createScriptTag(attrs: Record<string, string> = {}): HTMLScriptElement {
    const script = document.createElement('script')
    script.src = 'widget.js'
    for (const [key, value] of Object.entries(attrs)) {
      script.setAttribute(key, value)
    }
    return script
  }

  it('should return default config when no data attributes are set', () => {
    const script = createScriptTag()
    const config = parseConfig(script)

    expect(config.apiUrl).toBeNull()
    expect(config.lang).toBe('de')
    expect(config.texts.panelTitle).toBe('Feedback')
  })

  it('should parse data-api-url attribute', () => {
    const script = createScriptTag({ 'data-api-url': 'https://api.example.com' })
    const config = parseConfig(script)

    expect(config.apiUrl).toBe('https://api.example.com')
  })

  it('should parse data-lang="en" and return English texts', () => {
    const script = createScriptTag({ 'data-lang': 'en' })
    const config = parseConfig(script)

    expect(config.lang).toBe('en')
    expect(config.texts.consentHeadline).toBe('Your Feedback Matters!')
    expect(config.texts.consentCta).toBe("Let's start")
    expect(config.texts.composerPlaceholder).toBe('Type a message...')
  })

  it('should parse data-lang="de" and return German texts', () => {
    const script = createScriptTag({ 'data-lang': 'de' })
    const config = parseConfig(script)

    expect(config.lang).toBe('de')
    expect(config.texts.consentHeadline).toBe('Ihr Feedback z\u00e4hlt!')
    expect(config.texts.consentCta).toBe("Los geht's")
    expect(config.texts.composerPlaceholder).toBe('Nachricht eingeben...')
  })

  it('should fallback to "de" for invalid lang values', () => {
    const script = createScriptTag({ 'data-lang': 'fr' })
    const config = parseConfig(script)

    expect(config.lang).toBe('de')
    expect(config.texts.consentHeadline).toBe('Ihr Feedback z\u00e4hlt!')
  })

  it('should return correct WidgetConfig shape', () => {
    const script = createScriptTag({
      'data-api-url': 'https://test.com',
      'data-lang': 'en',
    })
    const config = parseConfig(script)

    // Verify full shape
    expect(config).toHaveProperty('apiUrl')
    expect(config).toHaveProperty('lang')
    expect(config).toHaveProperty('texts')
    expect(config.texts).toHaveProperty('panelTitle')
    expect(config.texts).toHaveProperty('consentHeadline')
    expect(config.texts).toHaveProperty('consentBody')
    expect(config.texts).toHaveProperty('consentCta')
    expect(config.texts).toHaveProperty('thankYouHeadline')
    expect(config.texts).toHaveProperty('thankYouBody')
    expect(config.texts).toHaveProperty('composerPlaceholder')
  })
})

describe('unit: findWidgetScript', () => {
  beforeEach(() => {
    // Clean up any script tags from previous tests
    document.querySelectorAll('script').forEach((s) => s.remove())
  })

  it('should find a script tag with src containing "widget.js"', () => {
    const script = document.createElement('script')
    script.src = '/dist/widget.js'
    document.head.appendChild(script)

    const found = findWidgetScript()
    expect(found).not.toBeNull()
    expect(found?.src).toContain('widget.js')
  })

  it('should return null when no widget.js script is present', () => {
    const found = findWidgetScript()
    expect(found).toBeNull()
  })

  it('should return the first matching script when multiple exist', () => {
    const script1 = document.createElement('script')
    script1.src = '/dist/widget.js'
    script1.setAttribute('data-lang', 'de')
    document.head.appendChild(script1)

    const script2 = document.createElement('script')
    script2.src = '/other/widget.js'
    script2.setAttribute('data-lang', 'en')
    document.head.appendChild(script2)

    const found = findWidgetScript()
    expect(found).not.toBeNull()
    expect(found?.getAttribute('data-lang')).toBe('de')
  })
})
