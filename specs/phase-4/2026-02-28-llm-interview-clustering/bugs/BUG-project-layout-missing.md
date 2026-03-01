# Bug: Interviews/Settings-Seiten ohne Projekt-Header und Tabs

**Entdeckt:** 2026-03-01
**Status:** ✅ Gefixt
**Priority:** 🔴 Hoch
**Location:** `dashboard/app/projects/[id]/interviews/page.tsx:1` + `dashboard/app/projects/[id]/settings/page.tsx:1`

---

## Problembeschreibung

Wenn der User auf "Interviews" oder "Settings" Tab klickt, navigiert er zu einer eigenständigen Seite (`/projects/{id}/interviews` bzw. `/projects/{id}/settings`). Diese Seiten rendern **ohne** Projekt-Header (Name + Research Goal) und **ohne** die Tab-Navigation (Insights | Interviews | Settings).

Der User sieht abrupt den Seiteninhalt ohne Kontext, ohne Back-Link und ohne Möglichkeit zu navigieren.

## Reproduktion

1. Auf `/projects/{id}` navigieren (Insights Tab sieht korrekt aus)
2. "Interviews" Tab klicken
3. → URL: `/projects/{id}/interviews` — nur die Interview-Tabelle, kein Header, keine Tabs
4. "Settings" Tab klicken
5. → URL: `/projects/{id}/settings` — nur das Settings-Formular, kein Header, keine Tabs

## Erwartetes Verhalten

Alle drei Tabs (Insights, Interviews, Settings) teilen sich den gleichen Projekt-Header:
```
← Projects
[Projekt-Name]
[Research Goal]
[Insights] [Interviews] [Settings]  ← Tab-Navigation immer sichtbar
----
[Tab-Inhalt]
```

## Tatsächliches Verhalten

- `Insights` Tab: ✅ Korrekt (Header + Tabs in `insights-client.tsx` gerendert)
- `Interviews` Tab: ❌ Nur `<InterviewsTabClient />` — kein Header, keine Tabs
- `Settings` Tab: ❌ Nur Settings-Formular — kein Header, keine Tabs

## Root Cause

Es fehlt eine `dashboard/app/projects/[id]/layout.tsx` die als gemeinsamer Wrapper für alle Sub-Seiten dient. Stattdessen rendert `insights-client.tsx` den Header + `ProjectTabs` selbst — was für die anderen Sub-Seiten nicht gilt.

## Fix-Vorschlag

Erstelle `dashboard/app/projects/[id]/layout.tsx`:

```tsx
// layout.tsx (Client Component wegen usePathname für activeTab)
'use client'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { ProjectTabs } from '@/components/project-tabs'

// Projekt-Daten via Server Component oder prop drilling
```

Oder alternativ: `interviews/page.tsx` und `settings/page.tsx` um Header + `ProjectTabs` erweitern.

## Test-Evidenz

- `dashboard/app/projects/[id]/insights-client.tsx:230-242` — Header + ProjectTabs nur in Insights
- `dashboard/app/projects/[id]/interviews/page.tsx:1-15` — kein Header, keine Tabs
- `dashboard/app/projects/[id]/settings/page.tsx:1-43` — kein Header, keine Tabs
- Screenshot: Interviews-Seite zeigt `#1 | Feb 28, 2026 | ... | failed` ohne Kontext

## Nächste Schritte

1. [ ] `dashboard/app/projects/[id]/layout.tsx` erstellen (Server + Client Component Mix)
2. [ ] Header + ProjectTabs aus `insights-client.tsx` entfernen (verhindert Duplizierung)
3. [ ] `interviews/page.tsx` und `settings/page.tsx` bleiben schlank (nur Inhalt)
4. [ ] `activeTab` dynamisch via `usePathname()` bestimmen
