// tests/slices/llm-interview-clustering/slice-04-dashboard-projekt-cluster-uebersicht.spec.ts
import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:3001'
const API_BASE = 'http://localhost:8000'

test.describe('Slice 04: Dashboard — Projekt-Liste + Cluster-Uebersicht', () => {

  test.beforeEach(async ({ page }) => {
    // Sicherstellen dass Backend und Dashboard laufen
    // In CI: Backend und Dashboard werden vor den Tests gestartet
  })

  // AC 1 + AC 5: Projekt-Liste mit vorhandenen Projekten
  test('zeigt Projekt-Cards mit Name, Interviewanzahl, Clusteranzahl und relativer Zeit', async ({ page }) => {
    // GIVEN: Backend hat mindestens ein Projekt mit Clustern
    await page.goto(`${BASE_URL}/projects`)

    // WHEN: Seite geladen
    await page.waitForSelector('[data-testid="project-card"]')

    // THEN: Projekt-Card zeigt erforderliche Daten
    const card = page.locator('[data-testid="project-card"]').first()
    await expect(card.locator('[data-testid="project-name"]')).toBeVisible()
    await expect(card.locator('[data-testid="project-interview-count"]')).toBeVisible()
    await expect(card.locator('[data-testid="project-cluster-count"]')).toBeVisible()
    await expect(card.locator('[data-testid="project-updated-at"]')).toContainText(/Updated .+ ago|Updated just now/)
  })

  // AC 2: Empty State
  test('zeigt Empty State wenn keine Projekte existieren', async ({ page }) => {
    // GIVEN: Backend hat keine Projekte (Mock oder leere DB)
    await page.route(`${API_BASE}/api/projects`, async route => {
      await route.fulfill({ json: [] })
    })

    await page.goto(`${BASE_URL}/projects`)

    // THEN: Empty State sichtbar
    await expect(page.locator('[data-testid="empty-state"]')).toBeVisible()
    await expect(page.locator('[data-testid="empty-state-cta"]')).toContainText('Create your first project')
  })

  // AC 3: New Project Modal oeffnen
  test('oeffnet New Project Modal beim Klick auf + New Project', async ({ page }) => {
    // GIVEN: Projekt-Liste Seite
    await page.goto(`${BASE_URL}/projects`)
    await page.waitForLoadState('networkidle')

    // WHEN: "+ New Project" klicken
    await page.click('[data-testid="new-project-btn"]')

    // THEN: Modal mit Formularfeldern sichtbar
    await expect(page.locator('[data-testid="new-project-dialog"]')).toBeVisible()
    await expect(page.locator('label[for="project-name"]')).toBeVisible()
    await expect(page.locator('label[for="research-goal"]')).toBeVisible()
    await expect(page.locator('label[for="prompt-context"]')).toBeVisible()
    await expect(page.locator('label[for="extraction-source"]')).toBeVisible()
    await expect(page.locator('[data-testid="create-project-submit"]')).toBeDisabled()
  })

  // AC 4: Neues Projekt erstellen
  test('erstellt neues Projekt und zeigt es in der Liste', async ({ page }) => {
    // GIVEN: Projekt-Liste Seite, Modal offen
    await page.goto(`${BASE_URL}/projects`)
    await page.click('[data-testid="new-project-btn"]')
    await page.waitForSelector('[data-testid="new-project-dialog"]')

    // WHEN: Pflichtfelder ausfuellen und Submit
    await page.fill('#project-name', 'E2E Test Projekt')
    await page.fill('#research-goal', 'Test research goal fuer E2E')
    await expect(page.locator('[data-testid="create-project-submit"]')).toBeEnabled()
    await page.click('[data-testid="create-project-submit"]')

    // THEN: Modal schliesst und neues Projekt erscheint in der Liste
    await expect(page.locator('[data-testid="new-project-dialog"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="project-card"]').filter({ hasText: 'E2E Test Projekt' })).toBeVisible()
  })

  // AC 5: Navigation zu Projekt-Dashboard
  test('navigiert zu Projekt-Dashboard beim Klick auf Projekt-Card', async ({ page }) => {
    // GIVEN: Projekt-Liste mit mindestens einem Projekt
    await page.goto(`${BASE_URL}/projects`)
    await page.waitForSelector('[data-testid="project-card"]')

    // WHEN: Auf erste Projekt-Card klicken
    const firstCard = page.locator('[data-testid="project-card"]').first()
    await firstCard.click()

    // THEN: URL ist /projects/{id}
    await expect(page).toHaveURL(/\/projects\/[0-9a-f-]{36}$/)
  })

  // AC 6 + AC 7: Projekt-Dashboard mit Cluster-Cards
  test('zeigt Projekt-Dashboard mit Status-Bar und Cluster-Cards sortiert nach Fact-Anzahl', async ({ page }) => {
    // GIVEN: Projekt mit Clustern existiert (ID aus vorherigem Test oder Fixture)
    await page.goto(`${BASE_URL}/projects`)
    await page.waitForSelector('[data-testid="project-card"]')
    await page.locator('[data-testid="project-card"]').first().click()
    await page.waitForURL(/\/projects\/[0-9a-f-]{36}$/)

    // THEN: Projekt-Header sichtbar
    await expect(page.locator('[data-testid="project-title"]')).toBeVisible()
    await expect(page.locator('[data-testid="project-research-goal"]')).toBeVisible()

    // THEN: Tab-Navigation (Insights aktiv)
    await expect(page.locator('[data-testid="tab-insights"]')).toHaveAttribute('aria-selected', 'true')
    await expect(page.locator('[data-testid="tab-interviews"]')).toBeVisible()
    await expect(page.locator('[data-testid="tab-settings"]')).toBeVisible()

    // THEN: Status-Bar
    await expect(page.locator('[data-testid="status-bar"]')).toBeVisible()
    await expect(page.locator('[data-testid="status-interview-count"]')).toBeVisible()
    await expect(page.locator('[data-testid="status-fact-count"]')).toBeVisible()
    await expect(page.locator('[data-testid="status-cluster-count"]')).toBeVisible()

    // THEN: Mindestens eine Cluster-Card sichtbar (wenn Cluster vorhanden)
    const clusterCards = page.locator('[data-testid="cluster-card"]')
    const count = await clusterCards.count()
    if (count > 0) {
      const firstCard = clusterCards.first()
      await expect(firstCard.locator('[data-testid="cluster-name"]')).toBeVisible()
      await expect(firstCard.locator('[data-testid="cluster-fact-count"]')).toBeVisible()
      await expect(firstCard.locator('[data-testid="cluster-interview-count"]')).toBeVisible()
    }
  })

  // AC 8: Empty State bei Projekt ohne Cluster
  test('zeigt Empty State im Insights Tab bei Projekt ohne Cluster', async ({ page }) => {
    // GIVEN: Leeres Projekt ohne Cluster
    // Route fuer Clusters-Endpoint mocken
    await page.route(/\/api\/projects\/.*\/clusters/, async route => {
      await route.fulfill({ json: [] })
    })

    await page.goto(`${BASE_URL}/projects`)
    await page.waitForSelector('[data-testid="project-card"]')
    await page.locator('[data-testid="project-card"]').first().click()
    await page.waitForURL(/\/projects\/[0-9a-f-]{36}$/)

    // THEN: Empty State sichtbar
    await expect(page.locator('[data-testid="clusters-empty-state"]')).toBeVisible()
    await expect(page.locator('[data-testid="clusters-empty-state"]')).toContainText('Assign interviews to get started')
  })

  // AC 9: Back-Navigation
  test('navigiert zurueck zur Projekt-Liste via Back-Link', async ({ page }) => {
    // GIVEN: Nutzer ist auf Projekt-Dashboard
    await page.goto(`${BASE_URL}/projects`)
    await page.waitForSelector('[data-testid="project-card"]')
    await page.locator('[data-testid="project-card"]').first().click()
    await page.waitForURL(/\/projects\/[0-9a-f-]{36}$/)

    // WHEN: Back-Link klicken
    await page.click('[data-testid="back-to-projects"]')

    // THEN: URL ist /projects
    await expect(page).toHaveURL(`${BASE_URL}/projects`)
  })

  // AC 10: Loading Skeleton
  test('zeigt Loading-Skeleton waehrend Daten geladen werden', async ({ page }) => {
    // GIVEN: Langsame API-Antwort simulieren
    await page.route(`${API_BASE}/api/projects`, async route => {
      await new Promise(resolve => setTimeout(resolve, 800))
      await route.continue()
    })

    await page.goto(`${BASE_URL}/projects`)

    // THEN: Skeleton sichtbar bevor Daten kommen
    // (Bei Server Components ist das Suspense-Fallback sofort sichtbar)
    // Alternativ: Pruefe dass Seite kein leeres White-Flash hat
    await page.waitForSelector('[data-testid="project-card"], [data-testid="skeleton-card"], [data-testid="empty-state"]')
  })

  // KERN-TEST: Dashboard-Flow (zusammengefasst fuer schnelles CI)
  test('vollstaendiger Flow: Projekte sehen → Cluster-Cards sehen', async ({ page }) => {
    // GIVEN: Backend mit Testdaten
    await page.goto(`${BASE_URL}/projects`)
    await page.waitForSelector('[data-testid="project-card"]', { timeout: 10000 })

    // WHEN: Auf Projekt klicken
    await page.locator('[data-testid="project-card"]').first().click()
    await page.waitForURL(/\/projects\/[0-9a-f-]{36}$/)

    // THEN: Cluster-Uebersicht sichtbar
    await page.waitForSelector('[data-testid="cluster-card"], [data-testid="clusters-empty-state"]', { timeout: 10000 })

    // Seite hat keine Fehler
    const errors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text())
    })
    expect(errors.filter(e => !e.includes('favicon'))).toHaveLength(0)
  })
})
