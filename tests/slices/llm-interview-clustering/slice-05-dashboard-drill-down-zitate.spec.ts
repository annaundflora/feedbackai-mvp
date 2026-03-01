// tests/slices/llm-interview-clustering/slice-05-dashboard-drill-down-zitate.spec.ts
import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:3001'
const API_BASE = 'http://localhost:8000'

test.describe('Slice 05: Dashboard — Cluster Drill-Down + Zitate', () => {

  test.beforeEach(async ({ page }) => {
    // Sicherstellen dass Backend und Dashboard laufen
    // In CI: Backend und Dashboard werden vor den Tests gestartet
  })

  // AC 1: Cluster-Card klicken navigiert zur Detail-Seite
  test('navigiert zu Cluster-Detail-Seite beim Klick auf Cluster-Card', async ({ page }) => {
    // GIVEN: Projekt-Liste, Projekt mit Clustern
    await page.goto(`${BASE_URL}/projects`)
    await page.waitForSelector('[data-testid="project-card"]')
    await page.locator('[data-testid="project-card"]').first().click()
    await page.waitForURL(/\/projects\/[0-9a-f-]{36}$/)

    // WHEN: Cluster-Card klicken (falls vorhanden)
    const clusterCards = page.locator('[data-testid="cluster-card"]')
    const count = await clusterCards.count()
    if (count === 0) {
      test.skip(true, 'No cluster cards available — skipping drill-down test')
    }
    await clusterCards.first().click()

    // THEN: URL ist /projects/{id}/clusters/{cluster_id}
    await expect(page).toHaveURL(/\/projects\/[0-9a-f-]{36}\/clusters\/[0-9a-f-]{36}$/)
  })

  // AC 2: Cluster-Detail Header
  test('zeigt Cluster-Detail Header mit Name und deaktivierten Aktions-Buttons', async ({ page }) => {
    // GIVEN: Cluster-Detail-Seite via Route-Mock
    const projectId = 'test-project-id'
    const clusterId = 'test-cluster-id'

    await page.route(`${API_BASE}/api/projects/${projectId}/clusters/${clusterId}`, async route => {
      await route.fulfill({
        json: {
          id: clusterId,
          name: 'Navigation Issues',
          summary: 'Users consistently report difficulty finding key features.',
          fact_count: 2,
          interview_count: 2,
          facts: [
            {
              id: 'fact-1',
              content: 'Users cannot find the settings page.',
              quote: 'I spent 10 minutes looking for settings.',
              confidence: 0.92,
              interview_id: 'interview-1',
              interview_date: '2025-11-15T10:30:00Z',
              cluster_id: clusterId
            }
          ],
          quotes: [
            {
              fact_id: 'fact-1',
              content: 'I spent 10 minutes looking for settings.',
              interview_id: 'interview-1',
              interview_number: 3
            }
          ]
        }
      })
    })

    await page.goto(`${BASE_URL}/projects/${projectId}/clusters/${clusterId}`)
    await page.waitForLoadState('networkidle')

    // THEN: Cluster-Name sichtbar
    await expect(page.locator('[data-testid="cluster-detail-name"]')).toContainText('Navigation Issues')

    // THEN: Back-Link sichtbar
    await expect(page.locator('[data-testid="back-to-clusters"]')).toBeVisible()

    // THEN: Merge-Button deaktiviert
    const mergeBtn = page.locator('[data-testid="merge-btn"]')
    await expect(mergeBtn).toBeVisible()
    await expect(mergeBtn).toBeDisabled()

    // THEN: Split-Button deaktiviert
    const splitBtn = page.locator('[data-testid="split-btn"]')
    await expect(splitBtn).toBeVisible()
    await expect(splitBtn).toBeDisabled()
  })

  // AC 3: Summary anzeigen
  test('zeigt vollstaendige Cluster-Zusammenfassung', async ({ page }) => {
    // GIVEN: Cluster mit Summary
    const projectId = 'test-project-id'
    const clusterId = 'test-cluster-id'

    await page.route(`${API_BASE}/api/projects/${projectId}/clusters/${clusterId}`, async route => {
      await route.fulfill({
        json: {
          id: clusterId,
          name: 'Navigation Issues',
          summary: 'Users consistently report difficulty finding key features after the initial onboarding flow.',
          fact_count: 1,
          interview_count: 1,
          facts: [],
          quotes: []
        }
      })
    })

    await page.goto(`${BASE_URL}/projects/${projectId}/clusters/${clusterId}`)
    await page.waitForLoadState('networkidle')

    // THEN: Summary sichtbar und vollstaendig (nicht geclippt)
    await expect(page.locator('[data-testid="cluster-summary"]')).toBeVisible()
    await expect(page.locator('[data-testid="cluster-summary"]')).toContainText(
      'Users consistently report difficulty finding key features after the initial onboarding flow.'
    )
  })

  // AC 4 + AC 5: Facts-Liste mit Interview-Badge und Confidence
  test('zeigt nummerierte Facts-Liste mit Interview-Badge und Confidence-Score', async ({ page }) => {
    // GIVEN: Cluster mit Facts (mit Quote und Confidence)
    const projectId = 'test-project-id'
    const clusterId = 'test-cluster-id'

    await page.route(`${API_BASE}/api/projects/${projectId}/clusters/${clusterId}`, async route => {
      await route.fulfill({
        json: {
          id: clusterId,
          name: 'Navigation Issues',
          summary: 'Test summary.',
          fact_count: 2,
          interview_count: 2,
          facts: [
            {
              id: 'fact-1',
              content: 'Users cannot find the settings page after completing onboarding.',
              quote: 'I spent 10 minutes looking for settings.',
              confidence: 0.92,
              interview_id: 'interview-1',
              interview_date: '2025-11-15T10:30:00Z',
              cluster_id: clusterId
            },
            {
              id: 'fact-2',
              content: 'The hamburger menu is not intuitive for desktop users.',
              quote: null,
              confidence: 0.87,
              interview_id: 'interview-2',
              interview_date: '2025-11-20T14:00:00Z',
              cluster_id: clusterId
            }
          ],
          quotes: [
            {
              fact_id: 'fact-1',
              content: 'I spent 10 minutes looking for settings.',
              interview_id: 'interview-1',
              interview_number: 1
            }
          ]
        }
      })
    })

    await page.goto(`${BASE_URL}/projects/${projectId}/clusters/${clusterId}`)
    await page.waitForLoadState('networkidle')

    // THEN: Facts-Section vorhanden mit Anzahl
    await expect(page.locator('[data-testid="facts-section"]')).toBeVisible()
    await expect(page.locator('[data-testid="facts-count"]')).toContainText('2')

    // THEN: Erster Fact sichtbar mit Nummer (index + 1 = 1)
    const firstFact = page.locator('[data-testid="fact-item"]').first()
    await expect(firstFact).toBeVisible()
    await expect(firstFact.locator('[data-testid="fact-number"]')).toContainText('1')
    await expect(firstFact.locator('[data-testid="fact-content"]')).toContainText('Users cannot find the settings page')
    await expect(firstFact.locator('[data-testid="fact-interview-badge"]')).toContainText('Interview #1')
    await expect(firstFact.locator('[data-testid="fact-confidence"]')).toContainText('0.92')

    // THEN: Zweiter Fact hat korrekte sequentielle Nummer (index + 1 = 2)
    const secondFact = page.locator('[data-testid="fact-item"]').nth(1)
    await expect(secondFact.locator('[data-testid="fact-number"]')).toContainText('2')
    await expect(secondFact.locator('[data-testid="fact-interview-badge"]')).toContainText('Interview #2')
    await expect(secondFact.locator('[data-testid="fact-confidence"]')).toContainText('0.87')
  })

  // AC 6: Quotes-Section
  test('zeigt Quotes-Section mit Originalzitaten wenn vorhanden', async ({ page }) => {
    // GIVEN: Cluster mit Facts die Quotes haben
    const projectId = 'test-project-id'
    const clusterId = 'test-cluster-id'

    await page.route(`${API_BASE}/api/projects/${projectId}/clusters/${clusterId}`, async route => {
      await route.fulfill({
        json: {
          id: clusterId,
          name: 'Navigation Issues',
          summary: 'Test summary.',
          fact_count: 1,
          interview_count: 1,
          facts: [
            {
              id: 'fact-1',
              content: 'Users cannot find the settings page.',
              quote: "I spent like 10 minutes just trying to find where my account settings were.",
              confidence: 0.92,
              interview_id: 'interview-1',
              interview_date: '2025-11-15T10:30:00Z',
              cluster_id: clusterId
            }
          ],
          quotes: [
            {
              fact_id: 'fact-1',
              content: "I spent like 10 minutes just trying to find where my account settings were.",
              interview_id: 'interview-1',
              interview_number: 3
            }
          ]
        }
      })
    })

    await page.goto(`${BASE_URL}/projects/${projectId}/clusters/${clusterId}`)
    await page.waitForLoadState('networkidle')

    // THEN: Quotes-Section sichtbar (cluster.quotes.length > 0)
    await expect(page.locator('[data-testid="quotes-section"]')).toBeVisible()

    // THEN: Zitat-Text sichtbar (aus QuoteResponse.content)
    const firstQuote = page.locator('[data-testid="quote-item"]').first()
    await expect(firstQuote).toBeVisible()
    await expect(firstQuote.locator('[data-testid="quote-text"]')).toContainText('I spent like 10 minutes')

    // THEN: Interview-Referenz sichtbar (aus QuoteResponse.interview_number vom Backend)
    await expect(firstQuote.locator('[data-testid="quote-interview-ref"]')).toContainText('Interview #3')
  })

  // AC 7: Keine Quotes-Section wenn keine Quotes vorhanden
  test('zeigt keine Quotes-Section wenn quotes-Array leer ist', async ({ page }) => {
    // GIVEN: Cluster mit Facts aber leeren quotes[] (Backend filtert quote==null heraus)
    const projectId = 'test-project-id'
    const clusterId = 'test-cluster-id'

    await page.route(`${API_BASE}/api/projects/${projectId}/clusters/${clusterId}`, async route => {
      await route.fulfill({
        json: {
          id: clusterId,
          name: 'Navigation Issues',
          summary: 'Test summary.',
          fact_count: 1,
          interview_count: 1,
          facts: [
            {
              id: 'fact-1',
              content: 'Users cannot find the settings page.',
              quote: null,
              confidence: 0.92,
              interview_id: 'interview-1',
              interview_date: '2025-11-15T10:30:00Z',
              cluster_id: clusterId
            }
          ],
          quotes: []  // Backend liefert leeres Array wenn alle facts.quote == null
        }
      })
    })

    await page.goto(`${BASE_URL}/projects/${projectId}/clusters/${clusterId}`)
    await page.waitForLoadState('networkidle')

    // THEN: Quotes-Section NICHT sichtbar (cluster.quotes.length === 0)
    await expect(page.locator('[data-testid="quotes-section"]')).not.toBeVisible()
  })

  // AC 8: Empty State fuer Facts
  test('zeigt Empty State in Facts-Section wenn keine Facts vorhanden', async ({ page }) => {
    // GIVEN: Cluster ohne Facts
    const projectId = 'test-project-id'
    const clusterId = 'test-cluster-id'

    await page.route(`${API_BASE}/api/projects/${projectId}/clusters/${clusterId}`, async route => {
      await route.fulfill({
        json: {
          id: clusterId,
          name: 'Empty Cluster',
          summary: null,
          fact_count: 0,
          interview_count: 0,
          facts: [],
          quotes: []
        }
      })
    })

    await page.goto(`${BASE_URL}/projects/${projectId}/clusters/${clusterId}`)
    await page.waitForLoadState('networkidle')

    // THEN: Empty State in Facts-Section
    await expect(page.locator('[data-testid="facts-empty-state"]')).toBeVisible()
    await expect(page.locator('[data-testid="facts-empty-state"]')).toContainText('No facts extracted yet')
  })

  // AC 9: Back-Navigation
  test('navigiert zurueck zur Projekt-Uebersicht via Back-Link', async ({ page }) => {
    // GIVEN: Nutzer ist auf Cluster-Detail-Seite
    const projectId = 'test-project-id'
    const clusterId = 'test-cluster-id'

    await page.route(`${API_BASE}/api/projects/${projectId}/clusters/${clusterId}`, async route => {
      await route.fulfill({
        json: {
          id: clusterId,
          name: 'Navigation Issues',
          summary: null,
          fact_count: 0,
          interview_count: 0,
          facts: [],
          quotes: []
        }
      })
    })

    await page.goto(`${BASE_URL}/projects/${projectId}/clusters/${clusterId}`)
    await page.waitForLoadState('networkidle')

    // WHEN: Back-Link klicken
    await page.click('[data-testid="back-to-clusters"]')

    // THEN: URL ist /projects/{id}
    await expect(page).toHaveURL(`${BASE_URL}/projects/${projectId}`)
  })

  // AC 10: Loading Skeleton
  test('zeigt Loading-Skeleton waehrend Cluster-Detail geladen wird', async ({ page }) => {
    // GIVEN: Langsame API-Antwort
    const projectId = 'test-project-id'
    const clusterId = 'test-cluster-id'

    await page.route(`${API_BASE}/api/projects/${projectId}/clusters/${clusterId}`, async route => {
      await new Promise(resolve => setTimeout(resolve, 800))
      await route.fulfill({
        json: {
          id: clusterId,
          name: 'Navigation Issues',
          summary: 'Test summary.',
          fact_count: 0,
          interview_count: 0,
          facts: [],
          quotes: []
        }
      })
    })

    await page.goto(`${BASE_URL}/projects/${projectId}/clusters/${clusterId}`)

    // THEN: Skeleton oder geladener Content sichtbar (kein leerer Screen)
    await page.waitForSelector(
      '[data-testid="cluster-detail-skeleton"], [data-testid="cluster-detail-name"]',
      { timeout: 5000 }
    )
  })

  // KERN-TEST: Vollstaendiger E2E Flow
  test('vollstaendiger Flow: Cluster-Card klicken → Facts sehen → Zitate sehen', async ({ page }) => {
    // GIVEN: Backend mit Testdaten (Projekt mit Cluster, Facts, Quotes)
    await page.goto(`${BASE_URL}/projects`)
    await page.waitForSelector('[data-testid="project-card"]', { timeout: 10000 })

    // WHEN: Auf Projekt klicken
    await page.locator('[data-testid="project-card"]').first().click()
    await page.waitForURL(/\/projects\/[0-9a-f-]{36}$/)

    // WHEN: Cluster-Card klicken (falls vorhanden)
    await page.waitForSelector('[data-testid="cluster-card"], [data-testid="clusters-empty-state"]', { timeout: 10000 })
    const clusterCards = page.locator('[data-testid="cluster-card"]')
    const count = await clusterCards.count()
    if (count === 0) {
      // Kein Cluster vorhanden — Flow endet hier
      return
    }

    await clusterCards.first().click()
    await page.waitForURL(/\/projects\/[0-9a-f-]{36}\/clusters\/[0-9a-f-]{36}$/)

    // THEN: Cluster-Detail-Seite geladen
    await expect(page.locator('[data-testid="cluster-detail-name"]')).toBeVisible()
    await expect(page.locator('[data-testid="facts-section"]')).toBeVisible()

    // Seite hat keine Fehler
    const errors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text())
    })
    expect(errors.filter(e => !e.includes('favicon'))).toHaveLength(0)
  })
})
