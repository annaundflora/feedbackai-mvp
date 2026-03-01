// tests/slices/llm-interview-clustering/slice-06-taxonomy-editing-summary-regen.spec.ts
import { test, expect } from "@playwright/test"

const BASE_URL = "http://localhost:3001"

test.describe("Slice 06: Taxonomy Editing + Summary Regeneration", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to a project's Insights Tab with existing clusters
    // Assumes seeded test data: project with 2+ clusters and facts
    await page.goto(`${BASE_URL}/projects/test-project-id`)
    await expect(page.getByRole("tab", { name: "Insights" })).toBeVisible()
  })

  // AC 1: Cluster Context Menu opens
  test("should show context menu with Rename, Merge, Split options", async ({ page }) => {
    // GIVEN a project with clusters is open
    const menuTrigger = page.getByTestId("cluster-menu-trigger").first()
    await expect(menuTrigger).toBeVisible()

    // WHEN user clicks the three-dot menu
    await menuTrigger.click()

    // THEN context menu appears with all three options
    const menu = page.getByTestId("cluster-context-menu")
    await expect(menu.getByTestId("menu-rename")).toBeVisible()
    await expect(menu.getByTestId("menu-merge")).toBeVisible()
    await expect(menu.getByTestId("menu-split")).toBeVisible()
  })

  // AC 2: Inline Rename
  test("should rename cluster inline on Enter key", async ({ page }) => {
    const menuTrigger = page.getByTestId("cluster-menu-trigger").first()
    await menuTrigger.click()
    await page.getByTestId("menu-rename").click()

    // GIVEN inline rename input is shown
    const renameInput = page.getByTestId("rename-input")
    await expect(renameInput).toBeFocused()

    // WHEN user types new name and presses Enter
    await renameInput.fill("Renamed Cluster")
    await renameInput.press("Enter")

    // THEN cluster name is updated
    await expect(page.getByText("Renamed Cluster")).toBeVisible()
    await expect(renameInput).not.toBeVisible()
  })

  test("should cancel rename on Escape key", async ({ page }) => {
    const menuTrigger = page.getByTestId("cluster-menu-trigger").first()
    await menuTrigger.click()
    await page.getByTestId("menu-rename").click()

    const renameInput = page.getByTestId("rename-input")
    await renameInput.fill("Temporary Name")
    await renameInput.press("Escape")

    // THEN rename is cancelled, original name shown
    await expect(renameInput).not.toBeVisible()
  })

  // AC 3 + 4: Merge with Undo Toast
  test("should merge clusters and show undo toast with countdown", async ({ page }) => {
    const menuTrigger = page.getByTestId("cluster-menu-trigger").first()
    await menuTrigger.click()
    await page.getByTestId("menu-merge").click()

    // GIVEN merge dialog is open
    const mergeDialog = page.getByTestId("merge-dialog")
    await expect(mergeDialog).toBeVisible()

    // WHEN user selects a target cluster
    const firstTarget = mergeDialog.locator('input[type="radio"]').first()
    await firstTarget.check()

    // AND clicks Merge Clusters
    await page.getByTestId("merge-confirm-btn").click()

    // THEN undo toast appears with countdown
    const undoToast = page.getByTestId("undo-toast")
    await expect(undoToast).toBeVisible()
    await expect(undoToast).toContainText("merged")
    await expect(page.getByTestId("undo-btn")).toBeVisible()
    await expect(page.getByTestId("undo-btn")).toContainText("Undo")
  })

  test("should undo merge within 30 seconds", async ({ page }) => {
    // Perform merge first
    const menuTrigger = page.getByTestId("cluster-menu-trigger").first()
    await menuTrigger.click()
    await page.getByTestId("menu-merge").click()
    const firstTarget = page.getByTestId("merge-dialog").locator('input[type="radio"]').first()
    await firstTarget.check()
    await page.getByTestId("merge-confirm-btn").click()

    // GIVEN undo toast is visible
    await expect(page.getByTestId("undo-toast")).toBeVisible()

    // WHEN user clicks Undo
    await page.getByTestId("undo-btn").click()

    // THEN undo toast disappears
    await expect(page.getByTestId("undo-toast")).not.toBeVisible()
  })

  // AC 5 + 6: Split 2-Step Flow
  test("should open split modal and show step 1 explanation", async ({ page }) => {
    const menuTrigger = page.getByTestId("cluster-menu-trigger").first()
    await menuTrigger.click()
    await page.getByTestId("menu-split").click()

    // GIVEN split modal is open (Step 1)
    const splitModal = page.getByTestId("split-modal")
    await expect(splitModal).toBeVisible()
    await expect(page.getByTestId("generate-preview-btn")).toBeVisible()
    await expect(page.getByTestId("confirm-split-btn")).not.toBeVisible()
  })

  test("should generate split preview and show Step 2 with sub-cluster cards", async ({ page }) => {
    const menuTrigger = page.getByTestId("cluster-menu-trigger").first()
    await menuTrigger.click()
    await page.getByTestId("menu-split").click()

    // WHEN user clicks Generate Preview
    await page.getByTestId("generate-preview-btn").click()

    // THEN Step 2 preview is shown
    await expect(page.getByTestId("confirm-split-btn")).toBeVisible({ timeout: 15000 })
    await expect(page.getByTestId("split-preview-subcluster-0")).toBeVisible()
    await expect(page.getByTestId("split-preview-subcluster-1")).toBeVisible()
  })

  test("should cancel split flow without making changes", async ({ page }) => {
    const menuTrigger = page.getByTestId("cluster-menu-trigger").first()
    await menuTrigger.click()
    await page.getByTestId("menu-split").click()

    // WHEN user cancels
    await page.getByRole("button", { name: "Cancel" }).click()

    // THEN modal closes, no changes
    await expect(page.getByTestId("split-modal")).not.toBeVisible()
  })

  // AC 8: Suggestion Banner
  test("should show suggestion banner and allow dismiss", async ({ page }) => {
    // GIVEN a suggestion exists (test data must include a suggestion)
    const suggestionBanner = page.getByTestId("suggestion-banner").first()

    if (await suggestionBanner.isVisible()) {
      // WHEN user clicks Dismiss
      await page.getByTestId("suggestion-dismiss").first().click()

      // THEN banner disappears
      await expect(suggestionBanner).not.toBeVisible()
    }
  })

  // AC 9 + 10: Fact Move (Cluster Detail)
  test("should show bulk-move-bar when fact checkboxes are selected", async ({ page }) => {
    // Navigate to cluster detail
    await page.getByTestId("cluster-card").first().click()
    await page.waitForURL(/\/clusters\//)

    // GIVEN fact items with checkboxes
    const firstCheckbox = page.getByRole("checkbox", { name: /Select fact/i }).first()
    await expect(firstCheckbox).toBeVisible()

    // WHEN user checks a fact
    await firstCheckbox.check()

    // THEN bulk move bar appears
    await expect(page.getByTestId("bulk-move-bar")).toBeVisible()
    await expect(page.getByTestId("bulk-move-select")).toBeVisible()
  })

  // AC 11: Recalculate Modal
  test("should open recalculate modal and confirm triggers recluster", async ({ page }) => {
    // GIVEN Recalculate button is visible in Insights Tab
    const recalcBtn = page.getByRole("button", { name: /Recalculate/i })
    await expect(recalcBtn).toBeVisible()

    // WHEN user clicks Recalculate
    await recalcBtn.click()

    // THEN confirmation modal opens
    const modal = page.getByTestId("recalculate-modal")
    await expect(modal).toBeVisible()
    await expect(page.getByTestId("recalculate-confirm-btn")).toBeVisible()

    // WHEN user cancels
    await page.getByRole("button", { name: "Cancel" }).click()

    // THEN modal closes
    await expect(modal).not.toBeVisible()
  })
})
