# Bug: SSE /events Endpoint gibt 404 zurück

**Entdeckt:** 2026-03-01
**Status:** ✅ Gefixt
**Priority:** 🔴 Hoch
**Location:** `dashboard/app/api/projects/[id]/events/route.ts` (fehlte)

---

## Problembeschreibung

Der `useProjectEvents` Hook verbindet sich via `EventSource` mit `/api/projects/{id}/events?token=...`. Next.js hat diese Route nicht gekannt und mit 404 geantwortet. Dadurch kamen keine SSE Live-Updates im Frontend an.

## Reproduktion

1. Projekt-Insights-Seite öffnen
2. Browser-Netzwerk-Tab: `GET /api/projects/{id}/events?token=... 404`
3. Kein Status-Update im UI während Extraction/Clustering läuft

## Root Cause

`useProjectEvents` ruft eine relative URL `/api/projects/${id}/events` auf — diese geht durch Next.js. Das FastAPI-Backend hat den Endpoint korrekt implementiert (`backend/app/api/sse_routes.py`), aber es fehlte der Next.js Proxy-Route, der die SSE-Verbindung an das Backend weiterleitet.

Next.js hatte nur `app/api/projects/route.ts` (für `POST /api/projects`), kein `[id]/events`.

## Fix

Neuen Next.js Streaming-Proxy erstellt: `dashboard/app/api/projects/[id]/events/route.ts`

```ts
export async function GET(request, { params }) {
  const upstream = await fetch(`${API_BASE}/api/projects/${id}/events?token=...`)
  return new Response(upstream.body, {
    headers: { 'Content-Type': 'text/event-stream', ... }
  })
}
```

Der Response-Body wird direkt als Stream an den Browser weitergeleitet.
