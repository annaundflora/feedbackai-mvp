export type WidgetLang = 'de' | 'en'

export interface WidgetTexts {
  panelTitle: string
  consentHeadline: string
  consentBody: string
  consentCta: string
  thankYouHeadline: string
  thankYouBody: string
  composerPlaceholder: string
}

export interface WidgetConfig {
  apiUrl: string | null
  lang: WidgetLang
  texts: WidgetTexts
}

const DEFAULT_TEXTS_DE: WidgetTexts = {
  panelTitle: 'Feedback',
  consentHeadline: 'Ihr Feedback zählt!',
  consentBody: 'Wir möchten Ihnen ein paar kurze Fragen stellen. Dauert ca. 5 Minuten.',
  consentCta: 'Los geht\'s',
  thankYouHeadline: 'Vielen Dank!',
  thankYouBody: 'Ihr Feedback hilft uns, besser zu werden.',
  composerPlaceholder: 'Nachricht eingeben...'
}

const DEFAULT_TEXTS_EN: WidgetTexts = {
  panelTitle: 'Feedback',
  consentHeadline: 'Your Feedback Matters!',
  consentBody: 'We\'d like to ask you a few quick questions. Takes about 5 minutes.',
  consentCta: 'Let\'s start',
  thankYouHeadline: 'Thank You!',
  thankYouBody: 'Your feedback helps us improve.',
  composerPlaceholder: 'Type a message...'
}

export function parseConfig(scriptTag: HTMLScriptElement): WidgetConfig {
  const apiUrl = scriptTag.getAttribute('data-api-url') || null
  const lang = (scriptTag.getAttribute('data-lang') || 'de') as WidgetLang

  // Fallback to de if invalid lang
  const validLang: WidgetLang = ['de', 'en'].includes(lang) ? lang : 'de'

  const texts = validLang === 'en' ? DEFAULT_TEXTS_EN : DEFAULT_TEXTS_DE

  return {
    apiUrl,
    lang: validLang,
    texts
  }
}

export function findWidgetScript(): HTMLScriptElement | null {
  const scripts = document.querySelectorAll('script[src*="widget.js"]')
  return scripts.length > 0 ? (scripts[0] as HTMLScriptElement) : null
}
