# Bug: StatusBar zeigt blaue Badges statt sauberem Text

**Entdeckt:** 2026-03-01
**Status:** ✅ Gefixt
**Priority:** 🟡 Mittel
**Location:** `dashboard/components/status-bar.tsx`

---

## Problembeschreibung

Die StatusBar ("6 Interviews · 25 Facts · 8 Clusters") hat blaue Hintergrund-Boxen um jeden Stat-Wert angezeigt statt plain Text.

## Root Cause

`<strong className="text-gray-900 dark:text-gray-100">` — Browser-Default-Styling für `<strong>` in Kombination mit Dark-Mode-Klassen und `tabular-nums` hat zu unerwünschten blauen Highlights geführt.

## Fix

- `<strong>` durch `<span>` ersetzt (kein Browser-Default-Styling)
- Dark-Mode-Varianten entfernt (konsistentes Light-Mode-Design)
- `tabular-nums` nur auf die Zahl-Spans angewendet
- Zahlen: `font-semibold text-gray-900`, Labels: `text-gray-500`
