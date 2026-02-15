# Gate 0: Discovery <-> Wireframe Compliance

**Discovery:** `discovery.md`
**Wireframes:** `wireframes.md`
**Prufdatum:** 2026-02-15

---

## Summary

| Status | Count |
|--------|-------|
| Pass | 22 |
| Auto-Fixed | 0 |
| Blocking | 0 |

**Verdict:** APPROVED

**100% Compliance:** Keine Warnings - alle Items gepruft und bestanden.

---

## A) Discovery -> Wireframe

### User Flow Coverage

| Discovery Flow | Steps | Wireframe Screens | Status |
|----------------|-------|-------------------|--------|
| Host-Page laedt, Floating Button erscheint | 1 | Floating Button Screen | Pass |
| Carrier klickt Floating Button, Panel Slide-Up | 2 | Panel Container (Open) + Slide-Up annotation | Pass |
| Carrier liest Consent, klickt "Los geht's" | 3 | Consent Screen mit CTA | Pass |
| Carrier sieht Chat-UI (Phase 2: leer) | 4 | Chat Screen mit empty state | Pass |
| Interview endet, Danke-Screen (Phase 3+) | 5 | Danke Screen | Pass |
| Danke Auto-Close nach ~5s, Reset auf consent | 6 | Danke State Variations: closing state | Pass |
| X-Button schliesst Panel, screen bleibt | 7 | Panel State Variations + close-button annotation | Pass |
| Nach Danke + Reopen: Consent-Screen | 8 | User Flow Overview Diagramm zeigt Reset | Pass |

### UI State Coverage

| Component | Discovery States | Wireframe States | Missing | Status |
|-----------|------------------|------------------|---------|--------|
| `floating-button` | visible, hidden | default, hover, panel open | -- | Pass |
| `panel` | open, closed | open (slide-up 300ms), closed (slide-down 300ms) | -- | Pass |
| `close-button` | default, hover | Annotated in Panel Header | -- | Pass |
| `consent-cta` | default, hover, active | default, hover (CTA) | -- | Pass |
| `chat-thread` | empty, active | empty (Phase 2), active (Phase 3) | -- | Pass |
| `chat-composer` | empty, typing | visible/open, typing | -- | Pass |

### Interactive Elements

| Discovery Element | Wireframe Location | Annotation | Status |
|-------------------|-------------------|------------|--------|
| `floating-button` | Floating Button Screen | Annotation 1 | Pass |
| `close-button` | Panel Container | Annotation 3 | Pass |
| `consent-cta` | Consent Screen | Annotation 3 | Pass |
| `chat-thread` | Chat Screen | Annotation 1 | Pass |
| `chat-composer` | Chat Screen | Annotation 2 | Pass |
| `panel-header` | Panel Container | Annotation 2 | Pass |
| `panel` (body) | Panel Container | Annotation 4 | Pass |

---

## B) Wireframe -> Discovery (Auto-Fix Ruckfluss)

### Visual Specs - Already Present

| Wireframe Spec | Value | Discovery Section | Status |
|----------------|-------|-------------------|--------|
| Floating Button Size | 48-56px | UI Layout: Floating Button (line 111) | Pass - Already Present |
| Floating Button Position | Fixed, bottom-right, 16px | UI Layout: Floating Button (line 107) | Pass - Already Present |
| Panel Dimensions (Desktop) | ~400x600px | Scope & Boundaries (line 33), UI Layout (line 117) | Pass - Already Present |
| Panel Position | Fixed, bottom-right, 16px | UI Layout: Panel Container (line 117) | Pass - Already Present |
| Mobile Breakpoint | <=768px Fullscreen | Business Rules (line 222) | Pass - Already Present |
| Slide-Up Animation | 300ms | UI Components (line 160), Transitions (lines 199-204) | Pass - Already Present |
| Slide-Down Animation | 300ms | UI Components (line 160), Transitions (lines 201-204) | Pass - Already Present |
| CTA Button Width | Full-width | UI Layout: Consent (line 133) | Pass - Already Present |
| Configurable Texts | Headline, Intro, CTA, Danke | Scope (line 42), Business Rules (line 226) | Pass - Already Present |

### Implicit Constraints - Already Present

| Wireframe Shows | Implied Constraint | Discovery Section | Status |
|-----------------|-------------------|-------------------|--------|
| Chat Composer always visible | Composer open without backend in Phase 2 | UI Components (line 165), Q&A #17 | Pass - Already Present |
| Empty message list in Phase 2 | No welcome text, no mock data | Q&A #13, Scope (line 36) | Pass - Already Present |
| Panel replaces floating button | Button hidden when panel open | UI Components (line 159) | Pass - Already Present |
| X-Button preserves screen state | panelOpen independent of screen | State Machine (lines 173-180) | Pass - Already Present |
| Danke closing resets to consent | screen = consent after auto-close | Transitions (lines 203-204) | Pass - Already Present |
| Mobile fullscreen layout | 100vw x 100vh on <=768px | UI Layout (line 124), Business Rules (line 222) | Pass - Already Present |

---

## C) Auto-Fix Summary

### Discovery Updates Applied

Keine Updates notwendig. Discovery ist vollstaendig.

### Wireframe Updates Needed (Blocking)

Keine Blocking Issues. Wireframes decken alle Discovery-Anforderungen ab.

---

## Blocking Issues

Keine.

---

## Verdict

**Status:** APPROVED

**Blocking Issues:** 0
**Required Discovery Updates:** 0
**Required Wireframe Updates:** 0

**Next Steps:**
- [ ] Proceed to Architecture phase (Gate 0 passed)
