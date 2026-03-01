# Bug: Cluster Cards nicht klickbar + Cluster-Name unsichtbar im Dark Mode

**Entdeckt:** 2026-03-01
**Status:** ✅ Gefixt
**Priority:** 🔴 Hoch
**Location:** `dashboard/app/projects/[id]/insights-client.tsx:312-373`

---

## Problembeschreibung

1. **Cards nicht klickbar**: Nur der Cluster-Name (h3) war in `<Link>` gewrapped. Klick auf Summary-Text, Facts-Count oder sonstigen Card-Bereich → keine Navigation.

2. **Cluster-Name unsichtbar (Dark Mode)**: h3 hatte `text-gray-900` ohne `dark:`-Variante. Im Dark Mode: dunkler Text auf dunklem `bg-gray-900` Hintergrund → Cluster-Name unsichtbar.

## Reproduktion

1. Insights-Tab aufrufen mit existierenden Clustern
2. Auf Summary-Text einer Card klicken → nichts passiert
3. System Dark Mode aktiv: Cluster-Name fehlt komplett in Card

## Root Cause

```tsx
// ALT: Nur h3 in Link gewrapped
<article className="bg-white dark:bg-gray-900 ...">
  <div className="flex items-start justify-between">
    <Link href="...">          ← nur der Name ist klickbar
      <h3 className="text-gray-900">  ← kein dark: Variant
        {cluster.name}
      </h3>
    </Link>
    <ClusterContextMenu />
  </div>
  <div>Facts count...</div>   ← nicht klickbar
  <p>Summary...</p>           ← nicht klickbar
</article>
```

## Fix

- Gesamte Card in `<Link>` gewrapped (alle Bereiche klickbar)
- `ClusterContextMenu` absolut positioniert außerhalb des Links (verhindert verschachtelte interaktive Elemente)
- Dark-Mode-Klassen entfernt → einheitliches Light-Mode-Styling
- h3 `text-gray-900` immer sichtbar (kein `dark:` Chaos)

## Nächste Schritte

- [x] Link wrapp gesamte Card
- [x] ClusterContextMenu absolut positioniert
- [x] Dark-Mode Styling vereinfacht
