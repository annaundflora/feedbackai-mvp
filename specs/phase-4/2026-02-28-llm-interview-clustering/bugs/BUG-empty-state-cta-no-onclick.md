# Bug: Empty State CTA Button öffnet kein Modal

**Entdeckt:** 2026-03-01
**Status:** ✅ Gefixt
**Priority:** 🟡 Mittel
**Location:** `dashboard/app/projects/page.tsx:13` + `dashboard/components/empty-state.tsx:95`

---

## Problembeschreibung

Auf der `/projects` Seite gibt es zwei "+ New Project" Buttons:
1. **Oben links** (`NewProjectDialog` Trigger) → öffnet Modal ✅
2. **Mitte der Seite** (`EmptyState` CTA) → tut nichts ❌

Der Button in der Mitte ist deaktiviert — er hat keinen `onClick` Handler.

## Reproduktion

1. Als eingeloggter User mit 0 Projekten `/projects` aufrufen
2. Den Button "Create your first project" in der **Mitte der Seite** klicken
3. → Nichts passiert, Modal öffnet sich nicht

## Erwartetes Verhalten

- Klick auf "Create your first project" (EmptyState CTA) → öffnet das `NewProjectDialog` Modal

## Tatsächliches Verhalten

- Button ist visuell vorhanden aber hat keinen `onClick` Handler
- Nur der "+ New Project" Button oben links öffnet das Modal

## Root Cause

`projects/page.tsx` ist ein **Server Component** und kann keine `onClick`-Callback an `EmptyStateLegacy` übergeben. `EmptyStateLegacy` rendert einen `<button>` ohne `onClick`, weil die Legacy-API (`message` + `ctaLabel`) keinen `onClick`-Prop unterstützt.

Die `NewProjectDialog` Komponente hält ihren `open`-State intern — es gibt keine geteilte State-Brücke zwischen EmptyState und Dialog.

## Fix-Vorschlag

**Option A (empfohlen):** `CustomEvent` Pattern
```tsx
// In EmptyStateLegacy — button dispatches custom event
<button onClick={() => document.dispatchEvent(new CustomEvent('open-new-project-dialog'))}>
  {ctaLabel}
</button>

// In NewProjectDialog — useEffect lauscht auf event
useEffect(() => {
  const handler = () => setOpen(true)
  document.addEventListener('open-new-project-dialog', handler)
  return () => document.removeEventListener('open-new-project-dialog', handler)
}, [])
```

**Option B:** Projects Page zu Client Component refactoren mit geteiltem Modal-State.

## Test-Evidenz

- `dashboard/app/projects/page.tsx:13` — EmptyState ohne `onClick`
- `dashboard/components/empty-state.tsx:95` — Button-Render ohne `onClick` Prop
- `dashboard/components/new-project-dialog.tsx:9` — `open` State ist isoliert in dieser Komponente

## Nächste Schritte

1. [ ] CustomEvent in `EmptyStateLegacy` dispatchen
2. [ ] `NewProjectDialog` lauscht auf `open-new-project-dialog` Event
3. [ ] Testen: Klick auf EmptyState CTA öffnet Modal
