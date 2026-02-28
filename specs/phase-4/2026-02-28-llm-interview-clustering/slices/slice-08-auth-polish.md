# Slice 8: Auth + Polish

> **Slice 8 von 8** fuer `LLM Interview Clustering`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-07-live-updates-sse.md` |
> | **Naechster:** | — |

---

## Metadata (fuer Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-08-auth-polish` |
| **Test** | `pnpm --filter dashboard test tests/slices/llm-interview-clustering/slice-08-auth-polish.test.ts` |
| **E2E** | `false` |
| **Dependencies** | `["slice-01-db-schema-projekt-crud", "slice-04-dashboard-projekt-cluster-uebersicht", "slice-07-live-updates-sse"]` |

**Erklaerung:**
- **ID**: Eindeutiger Identifier (wird fuer Commits und Evidence verwendet)
- **Test**: Vitest Unit Tests fuer Auth-Logic, Form-Validation, Middleware, Skeleton/Empty/Error-Components
- **E2E**: `false` — Vitest (`.test.ts`). Auth-Flow wird via MSW (Mock Service Worker) gemockt.
- **Dependencies**: Slice 1 (users-Tabelle + AuthService), Slice 4 (Dashboard-App, API-Client, alle Seiten), Slice 7 (SSE-Token-Uebergabe an `useProjectEvents`)

---

## Test-Strategy (fuer Orchestrator Pipeline)

> **Quelle:** Auto-detected basierend auf Repo-Indikatoren.
> Architecture.md spezifiziert: `dashboard/` als Next.js 16 App (App Router, Tailwind v4, TypeScript).
> Stack: `typescript-nextjs`. Unit/Integration Tests via Vitest + MSW.

| Key | Value |
|-----|-------|
| **Stack** | `typescript-nextjs` |
| **Test Command** | `pnpm --filter dashboard test tests/slices/llm-interview-clustering/slice-08-auth-polish.test.ts` |
| **Integration Command** | `pnpm --filter dashboard test:integration` |
| **Acceptance Command** | `pnpm --filter dashboard test tests/slices/llm-interview-clustering/slice-08-auth-polish.test.ts --reporter=verbose` |
| **Start Command** | `pnpm --filter dashboard dev` |
| **Health Endpoint** | `http://localhost:3001/api/health` |
| **Mocking Strategy** | `mock_external` |

**Erklaerung:**
- **Mocking Strategy:** Backend-Endpoints (`POST /api/auth/login`, `GET /api/auth/me`) werden via MSW gemockt. `next/navigation` (`useRouter`, `redirect`) wird via `vi.mock` gemockt. Cookies via `js-cookie` werden mit `vi.fn()` gemockt.
- **Backend-Tests:** `AuthService` (python-jose + passlib) und `auth_routes.py` werden separat via pytest getestet (nicht in diesem Slice-Test-File, sondern in `backend/tests/`).
- **Port 3001:** Dashboard laeuft auf Port 3001 (Slice 4 festgelegt).

---

## Slice-Uebersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | DB Schema + Projekt CRUD | **Ready** | `slice-01-db-schema-projekt-crud.md` |
| 2 | Fact Extraction Pipeline | **Ready** | `slice-02-fact-extraction-pipeline.md` |
| 3 | Clustering Pipeline + Agent | **Ready** | `slice-03-clustering-pipeline-agent.md` |
| 4 | Dashboard: Projekt-Liste + Cluster-Uebersicht | **Ready** | `slice-04-dashboard-projekt-cluster-uebersicht.md` |
| 5 | Dashboard: Drill-Down + Zitate | **Ready** | `slice-05-dashboard-drill-down.md` |
| 6 | Taxonomy-Editing + Summary-Regen | **Ready** | `slice-06-taxonomy-editing.md` |
| 7 | Live-Updates via SSE | **Ready** | `slice-07-live-updates-sse.md` |
| 8 | Auth + Polish | **Current** | `slice-08-auth-polish.md` |

---

## Kontext & Ziel

Das Dashboard laeuft bisher ohne Auth-Schutz. Alle Endpoints sind oeffentlich erreichbar. Dieser Slice macht das Dashboard production-ready:

1. **Auth:** JWT Login-Flow, geschuetzte Routes, Token-Weitergabe an API-Client und SSE-Hook
2. **Polish:** Loading Skeletons, Empty States, Error Boundaries, 404-Seite
3. **Settings Tab:** Vollstaendiges Einstellungs-Formular (General + Model Config + Danger Zone)
4. **Interviews Tab:** Vollstaendige Interview-Tabelle mit Status-Badges und Assign-Modal

**Was dieser Slice NICHT liefert:**
- Registrierungs-Flow (kein Self-Service — Admin-seitig erstellt)
- Role-based Access Control
- Passwort-Reset-Flow

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` → "Security" + "API Design → Endpoints — Auth" + "Migration Map → New Files"

```
Authentication Flow:
POST /api/auth/login  →  {email, password}  →  {access_token, token_type: "bearer"}
GET  /api/auth/me     →  Authorization: Bearer <token>  →  {id, email, created_at}

Token Storage: HttpOnly Cookie "auth_token" (set by Next.js Route Handler)
Token Usage:
  - API Client: Cookie → Authorization: Bearer <token> Header
  - SSE Hook:   Cookie → ?token=<token> Query-Parameter

Middleware (middleware.ts):
  - Matchers: /projects/:path* (all protected routes)
  - Check: Cookie "auth_token" vorhanden?
  - No token: redirect to /login
  - Token present: continue (Backend validiert beim API-Call)

Backend Auth (from architecture.md Security section):
  - JWT HS256, JWT_SECRET from env, 24h lifetime
  - python-jose[cryptography]==3.3.0
  - passlib[bcrypt]==1.7.4
  - bcrypt cost=12

Files (architecture.md Migration Map):
  - backend/app/auth/service.py       (AuthService: login, verify JWT)
  - backend/app/auth/middleware.py    (get_current_user FastAPI dependency)
  - backend/app/api/auth_routes.py    (POST /api/auth/login, GET /api/auth/me)
  - backend/app/main.py               (auth_router registrieren)
```

### 1. Architektur-Impact

| Layer | Aenderungen |
|-------|-------------|
| `backend/app/auth/service.py` | **Neu:** `AuthService.login()`, `AuthService.verify_token()` |
| `backend/app/auth/middleware.py` | **Neu:** `get_current_user()` FastAPI Dependency, `get_current_user_from_token()` (SSE) |
| `backend/app/api/auth_routes.py` | **Neu:** `POST /api/auth/login`, `GET /api/auth/me` |
| `backend/app/api/project_routes.py` | **Erweitert:** `Depends(get_current_user)` zu allen Projekt-Endpoints |
| `backend/app/api/cluster_routes.py` | **Erweitert:** `Depends(get_current_user)` zu allen Cluster-Endpoints |
| `backend/app/api/sse_routes.py` | **Unveraendert** (bereits `get_current_user_from_token` aus Slice 7) |
| `backend/app/main.py` | **Erweitert:** `auth_router` registrieren |
| `backend/requirements.txt` | **Erweitert:** `python-jose[cryptography]==3.3.0`, `passlib[bcrypt]==1.7.4` |
| `dashboard/app/login/page.tsx` | **Neu:** Login-Screen mit Email/Passwort-Form |
| `dashboard/app/api/auth/login/route.ts` | **Neu:** Next.js Route Handler — setzt HttpOnly Cookie |
| `dashboard/app/api/auth/logout/route.ts` | **Neu:** Next.js Route Handler — loescht Cookie |
| `dashboard/middleware.ts` | **Neu:** Next.js Middleware — schutzt `/projects/*` Routes |
| `dashboard/lib/api-client.ts` | **Erweitert:** `apiFetch()` — Server Component Auth-aware Fetch (liest HttpOnly Cookie via `next/headers`) |
| `dashboard/lib/auth.ts` | **Neu:** `getAuthToken()` Server-Helper |
| `dashboard/lib/client-api.ts` | **Neu:** `clientFetch()` — Client Component Fetch (leitet via Proxy, kein direkter Cookie-Zugriff) |
| `dashboard/app/api/proxy/[...path]/route.ts` | **Neu:** Catch-All Proxy Route Handler (liest auth_token Cookie, setzt Authorization-Header, leitet an FastAPI weiter) |
| `dashboard/components/UserAvatar.tsx` | **Neu:** Avatar mit Initialen + Logout-Dropdown |
| `dashboard/components/SkeletonCard.tsx` | **Erweitert:** Projekt-Karte, Cluster-Karte, Facts-Liste Varianten |
| `dashboard/components/EmptyState.tsx` | **Erweitert:** Varianten fuer Projects, Clusters, Facts, Interviews |
| `dashboard/components/ErrorBoundary.tsx` | **Neu:** React Error Boundary fuer Cluster-Detail und Projekt-Dashboard |
| `dashboard/app/not-found.tsx` | **Neu:** 404-Seite |
| `dashboard/app/projects/[id]/settings/page.tsx` | **Neu:** Settings Tab mit vollstaendigem Formular |
| `dashboard/app/projects/[id]/interviews/page.tsx` | **Erweitert:** Vollstaendige Interview-Tabelle + Assign-Modal |

### 2. Datenfluss

```
Login Flow:
Browser → POST /login (form submit)
  → dashboard/app/login/page.tsx (Client Component)
    → fetch("/api/auth/login", { method: "POST", body: {email, password} })
      → dashboard/app/api/auth/login/route.ts (Route Handler)
        → fetch("http://localhost:8000/api/auth/login", body)
          ← {access_token, token_type: "bearer"}
        → cookies().set("auth_token", access_token, { httpOnly: true, secure, sameSite: "lax" })
        ← {success: true, user: {id, email}}
      ← 200 OK
    → router.replace("/projects")

Protected Route Access:
Browser → GET /projects/[id]
  → middleware.ts
    → cookies().get("auth_token")
    → token vorhanden? continue : redirect("/login")
  → app/projects/[id]/page.tsx (Server Component)
    → apiClient.getClusters(id)  [with Authorization: Bearer <token>]
      → FastAPI GET /api/projects/{id}/clusters
        → Depends(get_current_user) validates JWT
        ← list[ClusterResponse]

SSE Token Passthrough (integration with Slice 7):
Server Component (page.tsx)
  → cookies().get("auth_token").value → token
  → pass token as prop to Client Component "ProjectDashboardClient"
    → useProjectEvents(projectId, token, callbacks)
      → new EventSource(`/api/projects/${projectId}/events?token=${token}`)

Logout:
UserAvatar → click "Log out"
  → fetch("/api/auth/logout", { method: "POST" })
    → dashboard/app/api/auth/logout/route.ts
      → cookies().delete("auth_token")
  → router.replace("/login")
```

### 3. Backend Auth-Implementierung

**AuthService (`backend/app/auth/service.py`):**

```python
# backend/app/auth/service.py
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


class AuthenticationError(Exception):
    """Raised when credentials are invalid."""


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def login(self, email: str, password: str) -> dict[str, Any]:
        """Validate credentials, return JWT access token."""
        from app.auth.repository import UserRepository

        repo = UserRepository(self._db)
        user = await repo.get_by_email(email.lower().strip())
        if user is None or not pwd_context.verify(password, user["password_hash"]):
            raise AuthenticationError("Invalid email or password")

        token = self._create_token(str(user["id"]))
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": str(user["id"]),
                "email": user["email"],
                "created_at": user["created_at"].isoformat(),
            },
        }

    def _create_token(self, user_id: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(hours=24)
        payload = {"sub": user_id, "exp": expire}
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    @staticmethod
    def decode_token(token: str) -> str:
        """Decode JWT, return user_id (sub claim). Raises JWTError on failure."""
        payload = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[get_settings().jwt_algorithm],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise JWTError("Missing sub claim")
        return user_id
```

**Auth Middleware (`backend/app/auth/middleware.py`):**

```python
# backend/app/auth/middleware.py
from fastapi import Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import AuthService
from app.database.connection import get_db_session

http_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """FastAPI Dependency: validates Bearer token, returns user dict."""
    try:
        user_id = AuthService.decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    from app.auth.repository import UserRepository

    user = await UserRepository(db).get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def get_current_user_from_token(
    token: str = Query(..., description="JWT token for SSE auth"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """FastAPI Dependency for SSE: validates ?token= query param."""
    try:
        user_id = AuthService.decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    from app.auth.repository import UserRepository

    user = await UserRepository(db).get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user
```

**Auth Routes (`backend/app/api/auth_routes.py`):**

```python
# backend/app/api/auth_routes.py
import time
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import get_current_user
from app.auth.service import AuthService, AuthenticationError
from app.database.connection import get_db_session

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory rate limiter: max 5 login attempts per minute per IP
_login_attempts: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(client_ip: str) -> None:
    now = time.monotonic()
    _login_attempts[client_ip] = [t for t in _login_attempts[client_ip] if now - t < 60]
    if len(_login_attempts[client_ip]) >= 5:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again in 1 minute.")
    _login_attempts[client_ip].append(now)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


@router.post("/login", response_model=AuthResponse)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
) -> Any:
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)
    try:
        result = await AuthService(db).login(body.email, body.password)
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return result


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: dict = Depends(get_current_user),
) -> Any:
    return {
        "id": str(current_user["id"]),
        "email": current_user["email"],
        "created_at": current_user["created_at"].isoformat(),
    }
```

> **Hinweis:** `get_current_user` wird als `from app.auth.middleware import get_current_user` importiert.

**Auth Repository (`backend/app/auth/repository.py`):**

```python
# backend/app/auth/repository.py
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        result = await self._db.execute(
            text("SELECT id, email, password_hash, created_at FROM users WHERE email = :email"),
            {"email": email},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        result = await self._db.execute(
            text("SELECT id, email, password_hash, created_at FROM users WHERE id = :id"),
            {"id": UUID(user_id)},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None
```

### 4. Frontend Auth-Implementierung

**Next.js Middleware (`dashboard/middleware.ts`):**

```typescript
// dashboard/middleware.ts
import { type NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest): NextResponse {
  const token = request.cookies.get("auth_token")?.value;

  if (!token) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("from", request.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/projects/:path*"],
};
```

**Route Handler Login (`dashboard/app/api/auth/login/route.ts`):**

```typescript
// dashboard/app/api/auth/login/route.ts
import { cookies } from "next/headers";
import { type NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest): Promise<NextResponse> {
  const body = await request.json();

  const backendResponse = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/api/auth/login`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );

  if (!backendResponse.ok) {
    const error = await backendResponse.json().catch(() => ({}));
    return NextResponse.json(
      { error: error.detail ?? "Invalid credentials" },
      { status: 401 },
    );
  }

  const data = await backendResponse.json();

  (await cookies()).set("auth_token", data.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 60 * 60 * 24, // 24h (matches backend JWT lifetime)
    path: "/",
  });

  return NextResponse.json({ success: true, user: data.user });
}
```

**Route Handler Logout (`dashboard/app/api/auth/logout/route.ts`):**

```typescript
// dashboard/app/api/auth/logout/route.ts
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export async function POST(): Promise<NextResponse> {
  (await cookies()).delete("auth_token");
  return NextResponse.json({ success: true });
}
```

**Auth Helper (`dashboard/lib/auth.ts`):**

```typescript
// dashboard/lib/auth.ts
import { cookies } from "next/headers";

export async function getAuthToken(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get("auth_token")?.value ?? null;
}
```

**API Client Erweiterung (`dashboard/lib/api-client.ts` — Ergaenzung):**

```typescript
// dashboard/lib/api-client.ts — auth-aware fetch wrapper
// Ergaenzung zu bestehender api-client.ts aus Slice 4

import { getAuthToken } from "@/lib/auth";

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = await getAuthToken();

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}${path}`,
    { ...options, headers },
  );

  if (response.status === 401) {
    // Token expired — redirect to login (Server Component context)
    throw new Error("UNAUTHORIZED");
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail ?? `API error ${response.status}`);
  }

  return response.json() as Promise<T>;
}
```

**Client-Side API Helper (`dashboard/lib/client-api.ts` — NEU):**

> **Zweck:** Client Components können keine HttpOnly Cookies lesen. Diese Hilfsfunktion
> leitet Requests an den Next.js Proxy-Route-Handler weiter, welcher serverseitig das
> Cookie liest und den Authorization-Header setzt.

```typescript
// dashboard/lib/client-api.ts
// Client-side fetch wrapper: routes through Next.js proxy to add auth header from HttpOnly cookie.
// Use in Client Components ("use client") for all authenticated API calls.

export async function clientFetch<T>(
  path: string, // e.g. "/api/projects/123"
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`/api/proxy${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    },
  });

  if (response.status === 401) {
    window.location.href = "/login";
    throw new Error("UNAUTHORIZED");
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error((error as { detail?: string }).detail ?? `API error ${response.status}`);
  }

  return response.json() as Promise<T>;
}
```

**Proxy Route Handler (`dashboard/app/api/proxy/[...path]/route.ts` — NEU):**

> **Zweck:** Liest das HttpOnly `auth_token` Cookie serverseitig, leitet den Request mit
> `Authorization: Bearer <token>` Header an FastAPI weiter.

```typescript
// dashboard/app/api/proxy/[...path]/route.ts
import { cookies } from "next/headers";
import { type NextRequest, NextResponse } from "next/server";

async function proxyRequest(
  request: NextRequest,
  pathSegments: string[],
): Promise<NextResponse> {
  const cookieStore = await cookies();
  const token = cookieStore.get("auth_token")?.value;

  const backendUrl = `${process.env.NEXT_PUBLIC_API_URL}/${pathSegments.join("/")}${request.nextUrl.search}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const body =
    request.method !== "GET" && request.method !== "HEAD"
      ? await request.text()
      : undefined;

  const response = await fetch(backendUrl, {
    method: request.method,
    headers,
    body,
  });

  const data = await response.json().catch(() => ({}));
  return NextResponse.json(data, { status: response.status });
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
): Promise<NextResponse> {
  return proxyRequest(request, (await params).path);
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
): Promise<NextResponse> {
  return proxyRequest(request, (await params).path);
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
): Promise<NextResponse> {
  return proxyRequest(request, (await params).path);
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
): Promise<NextResponse> {
  return proxyRequest(request, (await params).path);
}
```

### 5. Login-Screen

> **Quelle:** `wireframes.md` → "User Flow Overview" + Discovery Auth-Anforderungen

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│              FeedbackAI Insights                            │
│                                                             │
│         ┌─────────────────────────────────────┐             │
│         │  Sign in to your account             │             │
│         ├─────────────────────────────────────┤             │
│         │                                     │             │
│         │  Email                              │             │
│         │  ┌─────────────────────────────┐    │             │
│         │  │ user@example.com…           │    │             │
│         │  └─────────────────────────────┘    │             │
│         │                                     │             │
│         │  Password                           │             │
│         │  ┌─────────────────────────────┐    │             │
│         │  │ ••••••••                    │    │             │
│         │  └─────────────────────────────┘    │             │
│         │                                     │             │
│         │  [Error Banner wenn Auth-Fehler]     │             │
│         │                                     │             │
│         │        [Sign In]                    │             │
│         └─────────────────────────────────────┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**`dashboard/app/login/page.tsx`:**

```typescript
// dashboard/app/login/page.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { FormEvent } from "react";

export default function LoginPage(): JSX.Element {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const isValid = email.length > 0 && password.length > 0;

  async function handleSubmit(e: FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    if (!isValid) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        setError(data.error ?? "Sign in failed. Please check your credentials.");
        return;
      }

      router.replace("/projects");
    } catch {
      setError("Unable to connect. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-gray-900">FeedbackAI Insights</h1>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">
            Sign in to your account
          </h2>

          <form onSubmit={handleSubmit} noValidate data-testid="login-form">
            <div className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  name="email"
                  autoComplete="email"
                  spellCheck={false}
                  placeholder="user@example.com…"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  aria-invalid={error !== null}
                  aria-describedby={error !== null ? "login-error" : undefined}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  data-testid="email-input"
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  name="password"
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  aria-invalid={error !== null}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  data-testid="password-input"
                />
              </div>

              {error !== null && (
                <div
                  id="login-error"
                  role="alert"
                  aria-live="polite"
                  className="flex items-start gap-2 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm"
                  data-testid="login-error"
                >
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={!isValid || isLoading}
                className="w-full py-2 px-4 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors touch-action-manipulation"
                data-testid="submit-button"
              >
                {isLoading ? "Signing in…" : "Sign In"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
```

### 6. UserAvatar + Logout

> **Quelle:** `wireframes.md` → "Screen: Project List" Annotation ① (Header Avatar)

```
┌─────────────────────────────────────────────────────────────┐
│  FeedbackAI Insights                          [JD ▼]        │
│                                               ┌──────────┐  │
│                                               │ Log out  │  │
│                                               └──────────┘  │
```

**`dashboard/components/UserAvatar.tsx`:**

```typescript
// dashboard/components/UserAvatar.tsx
"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";

interface UserAvatarProps {
  email: string;
}

function getInitials(email: string): string {
  return email.slice(0, 2).toUpperCase();
}

export function UserAvatar({ email }: UserAvatarProps): JSX.Element {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent): void {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  async function handleLogout(): Promise<void> {
    setIsLoading(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } finally {
      router.replace("/login");
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        onClick={() => setIsOpen((o) => !o)}
        aria-label={`User menu for ${email}`}
        aria-expanded={isOpen}
        aria-haspopup="true"
        className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 transition-colors touch-action-manipulation"
        data-testid="user-avatar-button"
      >
        {getInitials(email)}
      </button>

      {isOpen && (
        <div
          role="menu"
          className="absolute right-0 mt-2 w-40 rounded-lg border border-gray-200 bg-white shadow-md z-50"
          data-testid="user-menu"
        >
          <div className="px-3 py-2 text-xs text-gray-500 border-b border-gray-100 truncate">
            {email}
          </div>
          <button
            role="menuitem"
            onClick={handleLogout}
            disabled={isLoading}
            className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 focus-visible:bg-gray-50 rounded-b-lg disabled:opacity-50 transition-colors"
            data-testid="logout-button"
          >
            {isLoading ? "Signing out…" : "Log out"}
          </button>
        </div>
      )}
    </div>
  );
}
```

### 7. Loading Skeletons

**`dashboard/components/SkeletonCard.tsx`:**

```typescript
// dashboard/components/SkeletonCard.tsx

interface SkeletonCardProps {
  variant?: "project" | "cluster" | "fact" | "row";
}

export function SkeletonCard({ variant = "project" }: SkeletonCardProps): JSX.Element {
  if (variant === "row") {
    return (
      <div className="flex items-center gap-4 p-3 animate-pulse" data-testid="skeleton-row">
        <div className="h-4 w-12 bg-gray-200 rounded" />
        <div className="h-4 w-24 bg-gray-200 rounded" />
        <div className="h-4 flex-1 bg-gray-200 rounded" />
        <div className="h-4 w-8 bg-gray-200 rounded" />
        <div className="h-6 w-16 bg-gray-200 rounded-full" />
      </div>
    );
  }

  if (variant === "fact") {
    return (
      <div className="p-4 border border-gray-100 rounded-lg animate-pulse" data-testid="skeleton-fact">
        <div className="h-4 bg-gray-200 rounded w-full mb-2" />
        <div className="h-4 bg-gray-200 rounded w-3/4" />
        <div className="flex gap-2 mt-3">
          <div className="h-5 w-20 bg-gray-200 rounded-full" />
          <div className="h-5 w-16 bg-gray-200 rounded-full" />
        </div>
      </div>
    );
  }

  if (variant === "cluster") {
    return (
      <div className="p-5 border border-gray-200 rounded-xl animate-pulse" data-testid="skeleton-cluster">
        <div className="flex justify-between mb-3">
          <div className="h-5 bg-gray-200 rounded w-40" />
          <div className="h-5 w-5 bg-gray-200 rounded" />
        </div>
        <div className="flex gap-2 mb-3">
          <div className="h-5 w-16 bg-gray-200 rounded-full" />
          <div className="h-5 w-20 bg-gray-200 rounded-full" />
        </div>
        <div className="space-y-2">
          <div className="h-4 bg-gray-200 rounded w-full" />
          <div className="h-4 bg-gray-200 rounded w-5/6" />
          <div className="h-4 bg-gray-200 rounded w-4/6" />
        </div>
      </div>
    );
  }

  // variant === "project" (default)
  return (
    <div className="p-5 border border-gray-200 rounded-xl animate-pulse" data-testid="skeleton-project">
      <div className="h-5 bg-gray-200 rounded w-40 mb-3" />
      <div className="flex gap-3">
        <div className="h-4 w-24 bg-gray-200 rounded" />
        <div className="h-4 w-20 bg-gray-200 rounded" />
      </div>
      <div className="h-3 w-28 bg-gray-200 rounded mt-3" />
    </div>
  );
}

export function SkeletonGrid({ count = 3, variant = "project" }: { count?: number; variant?: SkeletonCardProps["variant"] }): JSX.Element {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="skeleton-grid">
      {Array.from({ length: count }, (_, i) => (
        <SkeletonCard key={i} variant={variant} />
      ))}
    </div>
  );
}
```

### 8. Empty States

> **Quelle:** `wireframes.md` → State Variations: `empty` fuer Projects, Clusters, Interviews

**`dashboard/components/EmptyState.tsx`:**

```typescript
// dashboard/components/EmptyState.tsx

interface EmptyStateProps {
  variant: "projects" | "clusters" | "facts" | "interviews";
  onAction?: () => void;
}

const EMPTY_STATE_CONFIG = {
  projects: {
    icon: "📋",
    title: "No projects yet",
    description: "Create your first project to start analyzing interview insights.",
    action: "Create Project",
  },
  clusters: {
    icon: "🔍",
    title: "No clusters yet",
    description: "Assign interviews to this project to start generating insights.",
    action: "Assign Interviews",
  },
  facts: {
    icon: "💡",
    title: "No facts extracted yet",
    description: "Facts will appear here once interview processing is complete.",
    action: null,
  },
  interviews: {
    icon: "🎙",
    title: "No interviews assigned",
    description: "Assign interviews to start extracting insights for this project.",
    action: "Assign Interviews",
  },
} as const;

export function EmptyState({ variant, onAction }: EmptyStateProps): JSX.Element {
  const config = EMPTY_STATE_CONFIG[variant];

  return (
    <div
      className="flex flex-col items-center justify-center py-16 px-4 text-center"
      data-testid={`empty-state-${variant}`}
    >
      <span className="text-5xl mb-4" role="img" aria-hidden="true">
        {config.icon}
      </span>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{config.title}</h3>
      <p className="text-sm text-gray-500 max-w-xs mb-6">{config.description}</p>
      {config.action !== null && onAction !== undefined && (
        <button
          onClick={onAction}
          className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 transition-colors touch-action-manipulation"
          data-testid={`empty-state-${variant}-action`}
        >
          {config.action}
        </button>
      )}
    </div>
  );
}
```

### 9. Error Boundary

**`dashboard/components/ErrorBoundary.tsx`:**

```typescript
// dashboard/components/ErrorBoundary.tsx
"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  errorMessage: string | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, errorMessage: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, errorMessage: error.message };
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  override render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback !== undefined) {
        return this.props.fallback;
      }
      return (
        <div
          role="alert"
          className="flex flex-col items-center justify-center py-12 px-4 text-center"
          data-testid="error-boundary-fallback"
        >
          <span className="text-4xl mb-3" role="img" aria-hidden="true">⚠</span>
          <h3 className="text-base font-semibold text-gray-900 mb-1">
            Something went wrong
          </h3>
          <p className="text-sm text-gray-500 mb-4 max-w-xs">
            {this.state.errorMessage ?? "An unexpected error occurred. Please reload the page."}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, errorMessage: null })}
            className="px-4 py-2 rounded-lg bg-gray-100 text-gray-700 text-sm font-medium hover:bg-gray-200 focus-visible:ring-2 focus-visible:ring-gray-400 transition-colors"
            data-testid="error-boundary-retry"
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

### 10. 404-Seite

**`dashboard/app/not-found.tsx`:**

```typescript
// dashboard/app/not-found.tsx
import Link from "next/link";

export default function NotFound(): JSX.Element {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="text-center">
        <p className="text-6xl font-bold text-gray-300 mb-4">404</p>
        <h1 className="text-xl font-semibold text-gray-900 mb-2">Page not found</h1>
        <p className="text-sm text-gray-500 mb-6">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <Link
          href="/projects"
          className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 transition-colors"
          data-testid="not-found-back-link"
        >
          Back to Projects
        </Link>
      </div>
    </div>
  );
}
```

### 11. Project Settings Tab

> **Quelle:** `wireframes.md` → "Screen: Project Settings Tab"

**`dashboard/app/projects/[id]/settings/page.tsx`:**

```typescript
// dashboard/app/projects/[id]/settings/page.tsx
import { apiFetch } from "@/lib/api-client";
import type { ProjectResponse } from "@/lib/types";
import { SettingsForm } from "@/components/SettingsForm";
import { ModelConfigForm } from "@/components/ModelConfigForm";
import { DangerZone } from "@/components/DangerZone";

interface SettingsPageProps {
  params: Promise<{ id: string }>;
}

export default async function SettingsPage({ params }: SettingsPageProps): Promise<JSX.Element> {
  const { id } = await params;
  const project = await apiFetch<ProjectResponse>(`/api/projects/${id}`);

  return (
    <div className="space-y-10 max-w-2xl">
      <section>
        <h2 className="text-base font-semibold text-gray-900 mb-4">General</h2>
        <SettingsForm project={project} />
      </section>

      <hr className="border-gray-200" />

      <section>
        <h2 className="text-base font-semibold text-gray-900 mb-1">
          Model Configuration (OpenRouter)
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Configure the LLM model slug for each task. Format: provider/model-name
        </p>
        <ModelConfigForm project={project} />
      </section>

      <hr className="border-gray-200" />

      <section>
        <h2 className="text-base font-semibold text-red-600 mb-4">Danger Zone</h2>
        <DangerZone projectId={id} projectName={project.name} />
      </section>
    </div>
  );
}
```

**`dashboard/components/SettingsForm.tsx`:**

```typescript
// dashboard/components/SettingsForm.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { ProjectResponse } from "@/lib/types";

import { clientFetch } from "@/lib/client-api";

interface ResetSourceModalProps {
  project: ProjectResponse;
  onClose: () => void;
}

function ResetSourceModal({ project, onClose }: ResetSourceModalProps): JSX.Element {
  const router = useRouter();
  const otherSource = project.extraction_source === "summary" ? "transcript" : "summary";
  const [newSource, setNewSource] = useState<"summary" | "transcript">(otherSource);
  const [reExtract, setReExtract] = useState(false);
  const [isChanging, setIsChanging] = useState(false);

  async function handleChange(): Promise<void> {
    setIsChanging(true);
    try {
      await clientFetch(`/api/projects/${project.id}/extraction-source`, {
        method: "PUT",
        body: JSON.stringify({ extraction_source: newSource, re_extract: reExtract }),
      });
      router.refresh();
      onClose();
    } finally {
      setIsChanging(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      data-testid="reset-source-modal"
    >
      <div className="bg-white rounded-xl shadow-xl max-w-sm w-full p-6">
        <h3 className="text-base font-semibold text-gray-900 mb-2">
          Change Extraction Source
        </h3>
        <p className="text-sm text-gray-600 mb-4">
          {project.fact_count} facts were extracted from{" "}
          <strong>{project.extraction_source}s</strong>. Changing to a different
          source will only affect future interviews. Existing facts remain unchanged.
        </p>
        <div className="mb-3">
          <label
            htmlFor="new-source-select"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            New Extraction Source
          </label>
          <select
            id="new-source-select"
            value={newSource}
            onChange={(e) => setNewSource(e.target.value as "summary" | "transcript")}
            className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            data-testid="new-source-select"
          >
            <option value="summary">Summary</option>
            <option value="transcript">Transcript</option>
          </select>
        </div>
        <label className="flex items-center gap-2 mb-4 cursor-pointer">
          <input
            type="checkbox"
            checked={reExtract}
            onChange={(e) => setReExtract(e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            data-testid="re-extract-checkbox"
          />
          <span className="text-sm text-gray-700">
            Also re-extract all existing facts with the new source
          </span>
        </label>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 text-sm text-gray-700 hover:text-gray-900"
            data-testid="reset-source-cancel"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleChange}
            disabled={isChanging}
            className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
            data-testid="reset-source-confirm"
          >
            {isChanging ? "Changing…" : "Change Source"}
          </button>
        </div>
      </div>
    </div>
  );
}

interface SettingsFormProps {
  project: ProjectResponse;
}

export function SettingsForm({ project }: SettingsFormProps): JSX.Element {
  const [name, setName] = useState(project.name);
  const [researchGoal, setResearchGoal] = useState(project.research_goal);
  const [promptContext, setPromptContext] = useState(project.prompt_context ?? "");
  const [extractionSource, setExtractionSource] = useState<"summary" | "transcript">(project.extraction_source);
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showResetSourceModal, setShowResetSourceModal] = useState(false);

  const isValid = name.trim().length > 0 && researchGoal.trim().length > 0;

  async function handleSave(): Promise<void> {
    if (!isValid || !isDirty) return;
    setIsSaving(true);
    try {
      await clientFetch(`/api/projects/${project.id}`, {
        method: "PUT",
        body: JSON.stringify({ name: name.trim(), research_goal: researchGoal.trim(), prompt_context: promptContext.trim() || null }),
      });
      setIsDirty(false);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="space-y-4" data-testid="settings-form">
      <div>
        <label htmlFor="project-name" className="block text-sm font-medium text-gray-700 mb-1">
          Project Name
        </label>
        <input
          id="project-name"
          type="text"
          value={name}
          onChange={(e) => { setName(e.target.value); setIsDirty(true); }}
          className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
          data-testid="settings-name-input"
        />
      </div>

      <div>
        <label htmlFor="research-goal" className="block text-sm font-medium text-gray-700 mb-1">
          Research Goal
        </label>
        <textarea
          id="research-goal"
          rows={3}
          value={researchGoal}
          onChange={(e) => { setResearchGoal(e.target.value); setIsDirty(true); }}
          className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
          data-testid="settings-research-goal-input"
        />
      </div>

      <div>
        <label htmlFor="prompt-context" className="block text-sm font-medium text-gray-700 mb-1">
          Prompt Context <span className="text-gray-400 font-normal">(optional)</span>
        </label>
        <textarea
          id="prompt-context"
          rows={4}
          value={promptContext}
          onChange={(e) => { setPromptContext(e.target.value); setIsDirty(true); }}
          className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
          data-testid="settings-prompt-context-input"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Fact Extraction Source
        </label>
        {project.extraction_source_locked ? (
          <div className="space-y-1">
            <div
              className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 bg-gray-50 text-gray-500 cursor-not-allowed"
              data-testid="extraction-source-locked"
            >
              <span className="flex-1 capitalize">{project.extraction_source}</span>
              <span aria-label="Locked" role="img">🔒</span>
            </div>
            <p className="text-xs text-gray-500">
              {project.fact_count} facts extracted with this source.{" "}
              <button
                type="button"
                onClick={() => setShowResetSourceModal(true)}
                className="text-blue-600 hover:underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-blue-500"
                data-testid="reset-source-link"
              >
                Reset & Change Source
              </button>
            </p>
          </div>
        ) : (
          <select
            value={extractionSource}
            className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            data-testid="extraction-source-select"
            onChange={(e) => { setExtractionSource(e.target.value as "summary" | "transcript"); setIsDirty(true); }}
          >
            <option value="summary">Summary</option>
            <option value="transcript">Transcript</option>
          </select>
        )}
      </div>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={handleSave}
          disabled={!isValid || !isDirty || isSaving}
          className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          data-testid="settings-save-button"
        >
          {isSaving ? "Saving…" : "Save Changes"}
        </button>
      </div>

      {showResetSourceModal && (
        <ResetSourceModal
          project={project}
          onClose={() => setShowResetSourceModal(false)}
        />
      )}
    </div>
  );
}
```

**`dashboard/components/ModelConfigForm.tsx`:**

```typescript
// dashboard/components/ModelConfigForm.tsx
"use client";

import { useState } from "react";
import type { ProjectResponse } from "@/lib/types";
import { clientFetch } from "@/lib/client-api";

interface ModelConfigFormProps {
  project: ProjectResponse;
}

const MODEL_FIELDS = [
  { key: "model_interviewer", label: "Interviewer Model" },
  { key: "model_extraction", label: "Fact Extraction Model" },
  { key: "model_clustering", label: "Clustering Model" },
  { key: "model_summary", label: "Summary Model" },
] as const;

type ModelKey = typeof MODEL_FIELDS[number]["key"];

export function ModelConfigForm({ project }: ModelConfigFormProps): JSX.Element {
  const [models, setModels] = useState<Record<ModelKey, string>>({
    model_interviewer: project.model_interviewer,
    model_extraction: project.model_extraction,
    model_clustering: project.model_clustering,
    model_summary: project.model_summary,
  });
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const isValid = Object.values(models).every((v) => v.trim().length > 0);

  async function handleSave(): Promise<void> {
    if (!isValid || !isDirty) return;
    setIsSaving(true);
    try {
      await clientFetch(`/api/projects/${project.id}/models`, {
        method: "PUT",
        body: JSON.stringify(models),
      });
      setIsDirty(false);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="space-y-4" data-testid="model-config-form">
      {MODEL_FIELDS.map(({ key, label }) => (
        <div key={key}>
          <label htmlFor={key} className="block text-sm font-medium text-gray-700 mb-1">
            {label}
          </label>
          <input
            id={key}
            type="text"
            value={models[key]}
            onChange={(e) => {
              setModels((m) => ({ ...m, [key]: e.target.value }));
              setIsDirty(true);
            }}
            spellCheck={false}
            placeholder="provider/model-name…"
            className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
            data-testid={`model-${key}-input`}
          />
          <p className="mt-1 text-xs text-gray-400">Format: provider/model-name</p>
        </div>
      ))}

      <div className="flex justify-end">
        <button
          type="button"
          onClick={handleSave}
          disabled={!isValid || !isDirty || isSaving}
          className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          data-testid="model-config-save-button"
        >
          {isSaving ? "Saving…" : "Save Changes"}
        </button>
      </div>
    </div>
  );
}
```

**`dashboard/components/DangerZone.tsx`:**

```typescript
// dashboard/components/DangerZone.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { clientFetch } from "@/lib/client-api";

interface DangerZoneProps {
  projectId: string;
  projectName: string;
}

export function DangerZone({ projectId, projectName }: DangerZoneProps): JSX.Element {
  const router = useRouter();
  const [showModal, setShowModal] = useState(false);
  const [confirmInput, setConfirmInput] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  const isConfirmed = confirmInput === projectName;

  async function handleDelete(): Promise<void> {
    if (!isConfirmed) return;
    setIsDeleting(true);
    try {
      await clientFetch(`/api/projects/${projectId}`, { method: "DELETE" });
      router.replace("/projects");
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <div
      className="border border-red-200 rounded-xl p-5 bg-red-50"
      data-testid="danger-zone"
    >
      <p className="text-sm text-gray-700 mb-3">
        Delete this project and all its clusters and facts. This action cannot be undone.
      </p>
      <button
        type="button"
        onClick={() => setShowModal(true)}
        className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-500 transition-colors"
        data-testid="delete-project-button"
      >
        Delete Project
      </button>

      {showModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
          data-testid="delete-confirm-modal"
        >
          <div className="bg-white rounded-xl border border-gray-200 shadow-xl w-full max-w-md p-6">
            <h3 id="delete-modal-title" className="text-base font-semibold text-gray-900 mb-1">
              Delete Project
            </h3>
            <p className="text-sm text-red-600 font-medium mb-3">This action is permanent</p>

            <p className="text-sm text-gray-600 mb-4">
              Type the project name to confirm deletion of <strong>{projectName}</strong>:
            </p>

            <input
              type="text"
              value={confirmInput}
              onChange={(e) => setConfirmInput(e.target.value)}
              placeholder={projectName}
              aria-label="Type project name to confirm"
              className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-red-500 mb-4"
              data-testid="delete-confirm-input"
            />

            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => { setShowModal(false); setConfirmInput(""); }}
                disabled={isDeleting}
                className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 text-sm font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors"
                data-testid="delete-cancel-button"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDelete}
                disabled={!isConfirmed || isDeleting}
                className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                data-testid="delete-confirm-button"
              >
                {isDeleting ? "Deleting…" : "Delete Project"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

### 12. Interviews Tab (vollstaendig)

> **Quelle:** `wireframes.md` → "Screen: Project Interviews Tab" + "Screen: Interview Assignment (Modal)"

**`dashboard/app/projects/[id]/interviews/page.tsx`:**

```typescript
// dashboard/app/projects/[id]/interviews/page.tsx
import { apiFetch } from "@/lib/api-client";
import type { InterviewAssignment } from "@/lib/types";
import { InterviewsTabClient } from "@/components/InterviewsTabClient";

interface InterviewsPageProps {
  params: Promise<{ id: string }>;
}

export default async function InterviewsPage({ params }: InterviewsPageProps): Promise<JSX.Element> {
  const { id } = await params;
  const interviews = await apiFetch<InterviewAssignment[]>(`/api/projects/${id}/interviews`);

  return <InterviewsTabClient projectId={id} initialInterviews={interviews} />;
}
```

**`dashboard/components/InterviewsTabClient.tsx`:**

```typescript
// dashboard/components/InterviewsTabClient.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { InterviewAssignment } from "@/lib/types";
import { EmptyState } from "@/components/EmptyState";
import { AssignInterviewsModal } from "@/components/AssignInterviewsModal";
import { clientFetch } from "@/lib/client-api";

interface InterviewsTabClientProps {
  projectId: string;
  initialInterviews: InterviewAssignment[];
}

const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  completed: { label: "analyzed", className: "bg-green-100 text-green-700" },
  pending: { label: "pending", className: "bg-yellow-100 text-yellow-700" },
  running: { label: "pending", className: "bg-yellow-100 text-yellow-700" },
  failed: { label: "failed", className: "bg-red-100 text-red-700" },
};

type FilterStatus = "all" | "analyzed" | "pending" | "failed";
type FilterDateRange = "all" | "last-7-days" | "last-30-days";

export function InterviewsTabClient({
  projectId,
  initialInterviews,
}: InterviewsTabClientProps): JSX.Element {
  const router = useRouter();
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<FilterStatus>("all");
  const [filterDateRange, setFilterDateRange] = useState<FilterDateRange>("all");

  const filteredInterviews = initialInterviews.filter((iv) => {
    if (filterStatus !== "all") {
      const badge = STATUS_BADGE[iv.clustering_status] ?? STATUS_BADGE.pending;
      if (badge.label !== filterStatus) return false;
    }
    if (filterDateRange !== "all") {
      const days = filterDateRange === "last-7-days" ? 7 : 30;
      const cutoff = new Date();
      cutoff.setDate(cutoff.getDate() - days);
      if (new Date(iv.date) < cutoff) return false;
    }
    return true;
  });

  async function handleRetry(interviewId: string): Promise<void> {
    setRetryingId(interviewId);
    try {
      await clientFetch(`/api/projects/${projectId}/interviews/${interviewId}/retry`, {
        method: "POST",
      });
      router.refresh();
    } finally {
      setRetryingId(null);
    }
  }

  if (initialInterviews.length === 0) {
    return (
      <div>
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-base font-semibold text-gray-900">Interviews</h2>
          <button
            onClick={() => setShowAssignModal(true)}
            className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 transition-colors"
            data-testid="assign-interviews-button"
          >
            + Assign Interviews
          </button>
        </div>
        <EmptyState variant="interviews" onAction={() => setShowAssignModal(true)} />
        {showAssignModal && (
          <AssignInterviewsModal
            projectId={projectId}
            onClose={() => setShowAssignModal(false)}
            onAssigned={() => { setShowAssignModal(false); router.refresh(); }}
          />
        )}
      </div>
    );
  }

  return (
    <div data-testid="interviews-tab">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-base font-semibold text-gray-900">Interviews</h2>
        <div className="flex items-center gap-2">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as FilterStatus)}
            className="px-2 py-1.5 rounded-lg border border-gray-300 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            data-testid="interview-filter-status"
            aria-label="Filter by status"
          >
            <option value="all">All Statuses</option>
            <option value="analyzed">Analyzed</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
          </select>
          <select
            value={filterDateRange}
            onChange={(e) => setFilterDateRange(e.target.value as FilterDateRange)}
            className="px-2 py-1.5 rounded-lg border border-gray-300 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            data-testid="interview-filter-date"
            aria-label="Filter by date range"
          >
            <option value="all">All Time</option>
            <option value="last-7-days">Last 7 Days</option>
            <option value="last-30-days">Last 30 Days</option>
          </select>
          <button
            onClick={() => setShowAssignModal(true)}
            className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 transition-colors"
            data-testid="assign-interviews-button"
          >
            + Assign Interviews
          </button>
        </div>
      </div>

      <div className="border border-gray-200 rounded-xl overflow-hidden">
        <table className="w-full text-sm" data-testid="interviews-table">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">#</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Date</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Summary</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Facts</th>
              <th scope="col" className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filteredInterviews.map((interview, index) => {
              const badge = STATUS_BADGE[interview.clustering_status] ?? STATUS_BADGE.pending;
              const isFailed = interview.extraction_status === "failed" || interview.clustering_status === "failed";
              return (
                <tr key={interview.interview_id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 text-gray-500 tabular-nums">#{index + 1}</td>
                  <td className="px-4 py-3 text-gray-600 whitespace-nowrap">
                    {new Date(interview.date).toLocaleDateString("en-US", {
                      year: "numeric", month: "short", day: "numeric",
                    })}
                  </td>
                  <td className="px-4 py-3 text-gray-700 max-w-xs">
                    <span className="line-clamp-2">{interview.summary_preview ?? "—"}</span>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-600 tabular-nums">{interview.fact_count}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${badge.className}`}
                        data-testid={`interview-status-${interview.interview_id}`}
                      >
                        {badge.label}
                      </span>
                      {isFailed && (
                        <button
                          onClick={() => void handleRetry(interview.interview_id)}
                          disabled={retryingId === interview.interview_id}
                          aria-label="Retry processing"
                          className="text-gray-400 hover:text-gray-600 focus-visible:ring-1 focus-visible:ring-gray-400 rounded disabled:opacity-50 transition-colors"
                          data-testid={`retry-button-${interview.interview_id}`}
                        >
                          {retryingId === interview.interview_id ? "↻…" : "↻"}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-xs text-gray-400">
        Status: analyzed = fully processed &nbsp;·&nbsp; pending = in queue &nbsp;·&nbsp; failed = processing error
      </p>

      {showAssignModal && (
        <AssignInterviewsModal
          projectId={projectId}
          onClose={() => setShowAssignModal(false)}
          onAssigned={() => { setShowAssignModal(false); router.refresh(); }}
        />
      )}
    </div>
  );
}
```

**`dashboard/components/AssignInterviewsModal.tsx`:**

```typescript
// dashboard/components/AssignInterviewsModal.tsx
"use client";

import { useEffect, useState } from "react";
import type { AvailableInterview } from "@/lib/types";
import { clientFetch } from "@/lib/client-api";

interface AssignInterviewsModalProps {
  projectId: string;
  onClose: () => void;
  onAssigned: () => void;
}

export function AssignInterviewsModal({
  projectId,
  onClose,
  onAssigned,
}: AssignInterviewsModalProps): JSX.Element {
  const [available, setAvailable] = useState<AvailableInterview[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [isAssigning, setIsAssigning] = useState(false);

  useEffect(() => {
    async function load(): Promise<void> {
      const data = await clientFetch<AvailableInterview[]>(
        `/api/projects/${projectId}/interviews/available`,
      );
      setAvailable(data);
      setIsLoading(false);
    }
    void load();
  }, [projectId]);

  function toggleSelection(id: string): void {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  async function handleAssign(): Promise<void> {
    if (selected.size === 0) return;
    setIsAssigning(true);
    try {
      await clientFetch(`/api/projects/${projectId}/interviews`, {
        method: "POST",
        body: JSON.stringify({ interview_ids: Array.from(selected) }),
      });
      onAssigned();
    } finally {
      setIsAssigning(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="assign-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
      data-testid="assign-interviews-modal"
    >
      <div className="bg-white rounded-xl border border-gray-200 shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 id="assign-modal-title" className="text-base font-semibold text-gray-900">
            Assign Interviews
          </h3>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="text-gray-400 hover:text-gray-600 focus-visible:ring-1 focus-visible:ring-gray-400 rounded transition-colors"
            data-testid="assign-modal-close"
          >
            ✕
          </button>
        </div>

        <div className="px-6 py-4 max-h-80 overflow-y-auto overscroll-contain">
          {isLoading ? (
            <div className="text-sm text-gray-500 text-center py-4">Loading interviews…</div>
          ) : available.length === 0 ? (
            <div className="text-sm text-gray-500 text-center py-4">
              No unassigned interviews available.
            </div>
          ) : (
            <div className="space-y-2">
              {available.map((interview) => (
                <label
                  key={interview.session_id}
                  className="flex items-start gap-3 cursor-pointer p-2 rounded-lg hover:bg-gray-50 transition-colors"
                  data-testid={`assign-checkbox-${interview.session_id}`}
                >
                  <input
                    type="checkbox"
                    checked={selected.has(interview.session_id)}
                    onChange={() => toggleSelection(interview.session_id)}
                    className="mt-0.5 cursor-pointer"
                  />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900">
                      {new Date(interview.created_at).toLocaleDateString("en-US", {
                        year: "numeric", month: "short", day: "numeric",
                      })}
                    </p>
                    {interview.summary_preview !== null && (
                      <p className="text-xs text-gray-500 truncate">{interview.summary_preview}</p>
                    )}
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-100">
          <span className="text-sm text-gray-500">
            {selected.size > 0 ? `${selected.size} selected` : ""}
          </span>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isAssigning}
              className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 text-sm font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors"
              data-testid="assign-modal-cancel"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleAssign}
              disabled={selected.size === 0 || isAssigning}
              className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              data-testid="assign-modal-confirm"
            >
              {isAssigning ? "Assigning…" : "Assign Selected"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
```

### 13. Dependency Injection in Projekt-Routes

Alle bestehenden Endpoints erhalten die Auth-Dependency:

```python
# backend/app/api/project_routes.py — Ergaenzung (Beispiel)
from app.auth.middleware import get_current_user

@router.get("/api/projects", response_model=list[ProjectListItem])
async def list_projects(
    current_user: dict = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
) -> list[dict]:
    return await project_service.list_by_user(str(current_user["id"]))

@router.post("/api/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: CreateProjectRequest,
    current_user: dict = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service),
) -> dict:
    return await project_service.create(user_id=str(current_user["id"]), data=body)
```

### 14. Abhaengigkeiten (neu)

| Paket | Version | Bereich | Zweck |
|-------|---------|---------|-------|
| `python-jose[cryptography]` | `==3.3.0` | Backend | JWT encode/decode |
| `passlib[bcrypt]` | `==1.7.4` | Backend | Passwort-Hashing (bcrypt cost=12) |

> **Keine neuen Frontend-Dependencies** — `fetch`, `next/navigation`, `next/headers`, `react` sind alle bereits installiert.

---

## Integrations-Checkliste

### 1. Auth-Integration
- [ ] `AuthService.login()` gibt JWT zurueck, Cookie wird via Route Handler gesetzt
- [ ] `get_current_user()` Dependency in allen Projekt/Cluster/Fact-Endpoints injiziert
- [ ] `get_current_user_from_token()` im SSE-Endpoint bereits vorhanden (Slice 7) — unveraendert
- [ ] Middleware schutzt alle `/projects/*` Routes (Next.js `middleware.ts`)
- [ ] Token wird als Prop an Client-Komponente weitergegeben fuer `useProjectEvents`

### 2. SSE Token Passthrough
- [ ] `page.tsx` (Server Component) liest Cookie mit `getAuthToken()`
- [ ] Token wird als `token` Prop an `ProjectDashboardClient` (oder aequivalente Client-Komponente) weitergegeben
- [ ] `useProjectEvents(projectId, token, callbacks)` nutzt Token aus Slice 7 unveraendert

### 3. Settings Tab Integration
- [ ] `SettingsForm` ruft `PUT /api/projects/{id}` auf
- [ ] `ModelConfigForm` ruft `PUT /api/projects/{id}/models` auf
- [ ] `DangerZone` ruft `DELETE /api/projects/{id}` auf und redirectet zu `/projects`
- [ ] `extraction_source_locked` aus `ProjectResponse` steuert Lock-State

### 4. Interviews Tab Integration
- [ ] `InterviewsTabClient` ruft `GET /api/projects/{id}/interviews` auf (via Server Component initial load)
- [ ] `AssignInterviewsModal` ruft `GET /api/projects/{id}/interviews/available` auf
- [ ] Retry-Button ruft `POST /api/projects/{id}/interviews/{iid}/retry` auf
- [ ] `router.refresh()` nach Assign und Retry

### 5. Datenfluss-Vollstaendigkeit
- [ ] Login Flow: Form → Route Handler → Backend → Cookie → Redirect
- [ ] Logout Flow: Avatar-Dropdown → Route Handler → Cookie delete → Redirect
- [ ] Protected Route: Middleware check → Server Component → API Call mit Bearer Token
- [ ] Error 401: `apiFetch` wirft `UNAUTHORIZED` Error → Error Boundary zeigt Fehler → User sieht sinnvolle Meldung

---

## UI Anforderungen

### Wireframe-Referenzen

> **Quelle:** `wireframes.md` → alle Screens

| Screen | Wireframe Section | Slice 8 Ergaenzung |
|--------|-------------------|--------------------|
| Project List Header | "Screen: Project List" Annotation ① | `UserAvatar` statt statischem Text |
| Project List (loading) | State `loading` | `SkeletonGrid` mit `variant="project"` |
| Project List (empty) | State `empty` | `EmptyState variant="projects"` mit CTA |
| Cluster Grid (loading) | State `loading` | `SkeletonGrid` mit `variant="cluster"` |
| Cluster Grid (empty) | State `project_empty` | `EmptyState variant="clusters"` mit CTA |
| Interviews Tab | "Screen: Project Interviews Tab" | Vollstaendige Tabelle + Modal |
| Interview Assignment | "Screen: Interview Assignment (Modal)" | `AssignInterviewsModal` |
| Settings Tab | "Screen: Project Settings Tab" | `SettingsForm` + `ModelConfigForm` + `DangerZone` |
| Delete Confirmation | "Screen: Delete Project Confirmation" | `DangerZone` Modal |
| Reset Source | "Screen: Reset Extraction Source Confirmation" | `ResetSourceModal` in `SettingsForm` |

### Accessibility
- [ ] `LoginPage`: `label[htmlFor]` fuer Email + Password; `role="alert"` auf Error-Banner; `aria-invalid` auf Inputs bei Fehler
- [ ] `UserAvatar`: `aria-label` auf Button; `aria-expanded` + `aria-haspopup`; `role="menu"` + `role="menuitem"` auf Dropdown
- [ ] `DangerZone` Modal: `role="dialog"`, `aria-modal="true"`, `aria-labelledby` auf Dialog-Titel
- [ ] `AssignInterviewsModal`: `role="dialog"`, `aria-modal="true"`, `aria-label="Close dialog"` auf Close-Button
- [ ] `InterviewsTabClient`: `scope="col"` auf `<th>`, `tabular-nums` auf Zahl-Spalten
- [ ] `EmptyState`: Icon mit `role="img"` und `aria-hidden="true"`, semantische Heading-Hierarchie
- [ ] `ErrorBoundary`: `role="alert"` auf Fallback-Div

### Skill Verification

**React Best Practices:**
- [ ] `async-parallel`: `Promise.all` in Settings Page (project + interviews parallel — nicht blockierend)
- [ ] `bundle-dynamic-imports`: `AssignInterviewsModal` und `DangerZone` Modal via `next/dynamic` wenn > 10KB
- [ ] `rerender-derived-state-no-effect`: `isValid` als Derived State (kein `useEffect`)
- [ ] `rerender-functional-setstate`: `setSelected((prev) => ...)` in Toggle-Funktion

**Web Design:**
- [ ] Icon-only Buttons (`UserAvatar`, Close-Buttons) haben `aria-label`
- [ ] Form Inputs haben assoziierte `<label>` Elemente
- [ ] Destructive Actions (Delete) haben Confirmation-Dialog
- [ ] Loading States enden mit `…` (nicht `...`)
- [ ] `touch-action: manipulation` auf Buttons (via `touch-action-manipulation` Tailwind class)

**Tailwind v4:**
- [ ] `tabular-nums` fuer numerische Spalten (Fact-Anzahl, Interview-IDs)
- [ ] `line-clamp-2` fuer Summary-Vorschau in Tabellen
- [ ] `overscroll-contain` auf Modal-Scrollcontainer

---

## Acceptance Criteria

1) GIVEN a user is not logged in
   WHEN they navigate to `/projects`
   THEN they are redirected to `/login` with `?from=/projects` query param

2) GIVEN a user is on the login page
   WHEN they submit valid email and password
   THEN `POST /api/auth/login` is called, an HttpOnly cookie `auth_token` is set, and the user is redirected to `/projects`

3) GIVEN a user submits invalid credentials
   WHEN the backend returns 401
   THEN an error message "Sign in failed. Please check your credentials." is displayed inline, the form remains fillable

4) GIVEN a user is logged in and on `/projects`
   WHEN the page loads
   THEN the `UserAvatar` component shows the user's email initials in the header

5) GIVEN a user clicks the Avatar button
   WHEN the dropdown opens
   THEN a "Log out" menu item is visible; clicking it calls `POST /api/auth/logout`, deletes the cookie, and redirects to `/login`

6) GIVEN a project list is loading
   WHEN the server component is fetching projects
   THEN skeleton cards are displayed (via `Suspense` fallback with `SkeletonGrid`)

7) GIVEN no projects exist for the user
   WHEN the project list renders
   THEN the `EmptyState variant="projects"` component is shown with a "Create Project" CTA button

8) GIVEN a user opens the Settings Tab of a project
   WHEN the project has facts extracted (extraction_source_locked = true)
   THEN the extraction source dropdown is replaced by a locked display with lock icon and a "Reset & Change Source" link

9) GIVEN a user changes the project name in Settings
   WHEN they click "Save Changes"
   THEN `PUT /api/projects/{id}` is called with the updated name; the Save button shows "Saving…" during the request

10) GIVEN a user clicks "Delete Project" in the Danger Zone
    WHEN the confirmation modal opens
    THEN the Delete button is disabled until the user types the exact project name

11) GIVEN a user types the exact project name in the delete confirmation modal
    WHEN they click "Delete Project"
    THEN `DELETE /api/projects/{id}` is called and the user is redirected to `/projects`

12) GIVEN a project has assigned interviews
    WHEN the user opens the Interviews Tab
    THEN a table is shown with interview rows including status badges ("analyzed", "pending", "failed")

13) GIVEN an interview has `clustering_status = "failed"`
    WHEN the Interviews Tab renders
    THEN a retry button (↻) is visible on that row; clicking it calls `POST /api/projects/{id}/interviews/{iid}/retry`

14) GIVEN a user clicks "+ Assign Interviews"
    WHEN the modal opens
    THEN `GET /api/projects/{id}/interviews/available` is called and unassigned interviews are shown as checkboxes

15) GIVEN a user selects interviews in the Assign Modal
    WHEN they click "Assign Selected"
    THEN `POST /api/projects/{id}/interviews` is called with selected IDs; the modal closes and the table refreshes

16) GIVEN an API call fails with a non-auth error
    WHEN the error propagates to an Error Boundary
    THEN the `ErrorBoundary` fallback is shown with a "Try again" button that resets the boundary state

17) GIVEN a user navigates to a non-existent route
    WHEN Next.js renders
    THEN the custom 404 page (`not-found.tsx`) is shown with a "Back to Projects" link

18) GIVEN a logged-in user's token expires (24h)
    WHEN any API call returns 401
    THEN `apiFetch` throws `UNAUTHORIZED` and the Error Boundary (or global error handler) redirects to `/login`

19) GIVEN more than 5 login attempts within 1 minute from the same IP
    WHEN the 6th POST /api/auth/login attempt is made
    THEN HTTP 429 is returned with detail "Too many login attempts. Try again in 1 minute."

---

## Testfaelle

**WICHTIG:** Tests definieren die erwarteten Verhaltensweisen vor der Implementierung.

### Test-Datei

`tests/slices/llm-interview-clustering/slice-08-auth-polish.test.ts`

<test_spec>
```typescript
// tests/slices/llm-interview-clustering/slice-08-auth-polish.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// ─── Mock next/navigation ───────────────────────────────────────────────────
const mockReplace = vi.fn();
const mockRefresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace, refresh: mockRefresh }),
}));

// ─── Mock global fetch (for LoginPage which calls /api/auth/login directly) ─
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// ─── Mock clientFetch (for Client Components: DangerZone, SettingsForm, etc.)─
const mockClientFetch = vi.fn().mockResolvedValue({});
vi.mock("@/lib/client-api", () => ({
  clientFetch: (...args: unknown[]) => mockClientFetch(...args),
}));

// ─── Imports after mocks ─────────────────────────────────────────────────────
import LoginPage from "@/app/login/page";
import { UserAvatar } from "@/components/UserAvatar";
import { DangerZone } from "@/components/DangerZone";
import { SettingsForm } from "@/components/SettingsForm";
import { SkeletonCard, SkeletonGrid } from "@/components/SkeletonCard";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { AssignInterviewsModal } from "@/components/AssignInterviewsModal";
import { InterviewsTabClient } from "@/components/InterviewsTabClient";
import type { InterviewAssignment, AvailableInterview, ProjectResponse } from "@/lib/types";

// ─── Helpers ─────────────────────────────────────────────────────────────────
function mockFetchOk(data: unknown): void {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(data),
    status: 200,
  });
}

function mockFetchError(status: number, detail: string): void {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    json: () => Promise.resolve({ detail }),
    status,
  });
}

// ─── LoginPage ────────────────────────────────────────────────────────────────
describe("LoginPage", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    mockReplace.mockReset();
  });

  it("should disable submit button when fields are empty", () => {
    render(<LoginPage />);
    const button = screen.getByTestId("submit-button");
    expect(button).toBeDisabled();
  });

  it("should enable submit button when both fields are filled", async () => {
    render(<LoginPage />);
    await userEvent.type(screen.getByTestId("email-input"), "user@example.com");
    await userEvent.type(screen.getByTestId("password-input"), "secret123");
    expect(screen.getByTestId("submit-button")).not.toBeDisabled();
  });

  it("should call POST /api/auth/login with credentials on submit", async () => {
    mockFetchOk({ success: true, user: { id: "1", email: "user@example.com" } });
    render(<LoginPage />);
    await userEvent.type(screen.getByTestId("email-input"), "user@example.com");
    await userEvent.type(screen.getByTestId("password-input"), "secret123");
    await userEvent.click(screen.getByTestId("submit-button"));
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/auth/login",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ email: "user@example.com", password: "secret123" }),
      }),
    );
  });

  it("should redirect to /projects after successful login", async () => {
    mockFetchOk({ success: true, user: { id: "1", email: "user@example.com" } });
    render(<LoginPage />);
    await userEvent.type(screen.getByTestId("email-input"), "user@example.com");
    await userEvent.type(screen.getByTestId("password-input"), "secret123");
    await userEvent.click(screen.getByTestId("submit-button"));
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/projects"));
  });

  it("should display error message on 401 response", async () => {
    mockFetchError(401, "Invalid email or password");
    render(<LoginPage />);
    await userEvent.type(screen.getByTestId("email-input"), "user@example.com");
    await userEvent.type(screen.getByTestId("password-input"), "wrong");
    await userEvent.click(screen.getByTestId("submit-button"));
    await waitFor(() =>
      expect(screen.getByTestId("login-error")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("login-error").textContent).toMatch(/Invalid credentials|Sign in failed/);
  });

  it("should show loading state during request", async () => {
    let resolve: (v: unknown) => void;
    mockFetch.mockReturnValueOnce(new Promise((r) => { resolve = r; }));
    render(<LoginPage />);
    await userEvent.type(screen.getByTestId("email-input"), "user@example.com");
    await userEvent.type(screen.getByTestId("password-input"), "secret");
    await userEvent.click(screen.getByTestId("submit-button"));
    expect(screen.getByTestId("submit-button").textContent).toMatch(/Signing in/);
    resolve!({ ok: true, json: () => Promise.resolve({ success: true, user: {} }), status: 200 });
  });
});

// ─── UserAvatar ───────────────────────────────────────────────────────────────
describe("UserAvatar", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    mockReplace.mockReset();
  });

  it("should show initials derived from email", () => {
    render(<UserAvatar email="john.doe@example.com" />);
    expect(screen.getByTestId("user-avatar-button").textContent).toBe("JO");
  });

  it("should open dropdown on click", async () => {
    render(<UserAvatar email="user@example.com" />);
    await userEvent.click(screen.getByTestId("user-avatar-button"));
    expect(screen.getByTestId("user-menu")).toBeInTheDocument();
  });

  it("should call logout endpoint and redirect on logout click", async () => {
    mockFetchOk({ success: true });
    render(<UserAvatar email="user@example.com" />);
    await userEvent.click(screen.getByTestId("user-avatar-button"));
    await userEvent.click(screen.getByTestId("logout-button"));
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/auth/logout",
      expect.objectContaining({ method: "POST" }),
    );
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/login"));
  });
});

// ─── DangerZone ───────────────────────────────────────────────────────────────
describe("DangerZone", () => {
  beforeEach(() => {
    mockClientFetch.mockReset().mockResolvedValue({});
    mockReplace.mockReset();
  });

  it("should open confirmation modal on delete click", async () => {
    render(<DangerZone projectId="proj-1" projectName="My Project" />);
    await userEvent.click(screen.getByTestId("delete-project-button"));
    expect(screen.getByTestId("delete-confirm-modal")).toBeInTheDocument();
  });

  it("should keep delete button disabled until project name matches", async () => {
    render(<DangerZone projectId="proj-1" projectName="My Project" />);
    await userEvent.click(screen.getByTestId("delete-project-button"));
    const confirmButton = screen.getByTestId("delete-confirm-button");
    expect(confirmButton).toBeDisabled();
    await userEvent.type(screen.getByTestId("delete-confirm-input"), "My Project");
    expect(confirmButton).not.toBeDisabled();
  });

  it("should call DELETE /api/projects/{id} via clientFetch and redirect on confirmed delete", async () => {
    render(<DangerZone projectId="proj-1" projectName="My Project" />);
    await userEvent.click(screen.getByTestId("delete-project-button"));
    await userEvent.type(screen.getByTestId("delete-confirm-input"), "My Project");
    await userEvent.click(screen.getByTestId("delete-confirm-button"));
    expect(mockClientFetch).toHaveBeenCalledWith(
      "/api/projects/proj-1",
      expect.objectContaining({ method: "DELETE" }),
    );
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/projects"));
  });
});

// ─── EmptyState ───────────────────────────────────────────────────────────────
describe("EmptyState", () => {
  it("should render projects variant with CTA", () => {
    const onAction = vi.fn();
    render(<EmptyState variant="projects" onAction={onAction} />);
    expect(screen.getByTestId("empty-state-projects")).toBeInTheDocument();
    expect(screen.getByTestId("empty-state-projects-action")).toBeInTheDocument();
  });

  it("should call onAction when CTA is clicked", async () => {
    const onAction = vi.fn();
    render(<EmptyState variant="clusters" onAction={onAction} />);
    await userEvent.click(screen.getByTestId("empty-state-clusters-action"));
    expect(onAction).toHaveBeenCalledOnce();
  });

  it("should not render action button for facts variant (no action)", () => {
    render(<EmptyState variant="facts" />);
    expect(screen.queryByTestId("empty-state-facts-action")).toBeNull();
  });
});

// ─── SkeletonCard ─────────────────────────────────────────────────────────────
describe("SkeletonCard", () => {
  it("should render project skeleton", () => {
    render(<SkeletonCard variant="project" />);
    expect(screen.getByTestId("skeleton-project")).toBeInTheDocument();
  });

  it("should render cluster skeleton", () => {
    render(<SkeletonCard variant="cluster" />);
    expect(screen.getByTestId("skeleton-cluster")).toBeInTheDocument();
  });

  it("should render N skeleton cards in SkeletonGrid", () => {
    render(<SkeletonGrid count={4} variant="project" />);
    expect(screen.getAllByTestId("skeleton-project")).toHaveLength(4);
  });
});

// ─── ErrorBoundary ────────────────────────────────────────────────────────────
describe("ErrorBoundary", () => {
  // Suppress console.error from React for expected error
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  function ThrowingComponent({ shouldThrow }: { shouldThrow: boolean }): JSX.Element {
    if (shouldThrow) throw new Error("Test error");
    return <div>OK</div>;
  }

  it("should render children when no error", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={false} />
      </ErrorBoundary>,
    );
    expect(screen.getByText("OK")).toBeInTheDocument();
  });

  it("should render fallback UI when child throws", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>,
    );
    expect(screen.getByTestId("error-boundary-fallback")).toBeInTheDocument();
    expect(screen.getByTestId("error-boundary-retry")).toBeInTheDocument();
  });
});

// ─── SettingsForm ─────────────────────────────────────────────────────────────
describe("SettingsForm", () => {
  const mockProject: ProjectResponse = {
    id: "proj-1",
    name: "My Research Project",
    research_goal: "Understand user pain points",
    prompt_context: null,
    extraction_source: "summary",
    extraction_source_locked: false,
    interview_count: 0,
    cluster_count: 0,
    fact_count: 0,
    model_interviewer: "openai/gpt-4o",
    model_extraction: "openai/gpt-4o-mini",
    model_clustering: "openai/gpt-4o-mini",
    model_summary: "openai/gpt-4o-mini",
    created_at: "2026-02-28T10:00:00Z",
    updated_at: "2026-02-28T10:00:00Z",
  };

  const lockedProject: ProjectResponse = {
    ...mockProject,
    extraction_source_locked: true,
    fact_count: 47,
  };

  beforeEach(() => {
    mockClientFetch.mockReset().mockResolvedValue({});
    mockRefresh.mockReset();
  });

  it("should render settings form with inputs", () => {
    render(<SettingsForm project={mockProject} />);
    expect(screen.getByTestId("settings-form")).toBeInTheDocument();
    expect(screen.getByTestId("settings-name-input")).toHaveValue("My Research Project");
    expect(screen.getByTestId("settings-research-goal-input")).toHaveValue(
      "Understand user pain points",
    );
  });

  it("should keep save button disabled when form is pristine", () => {
    render(<SettingsForm project={mockProject} />);
    expect(screen.getByTestId("settings-save-button")).toBeDisabled();
  });

  it("should enable save button after editing name and call clientFetch PUT on save", async () => {
    render(<SettingsForm project={mockProject} />);
    await userEvent.clear(screen.getByTestId("settings-name-input"));
    await userEvent.type(screen.getByTestId("settings-name-input"), "Updated Name");
    const saveBtn = screen.getByTestId("settings-save-button");
    expect(saveBtn).not.toBeDisabled();
    await userEvent.click(saveBtn);
    expect(mockClientFetch).toHaveBeenCalledWith(
      "/api/projects/proj-1",
      expect.objectContaining({ method: "PUT" }),
    );
  });

  it("should show locked source display when extraction_source_locked is true (AC-8)", () => {
    render(<SettingsForm project={lockedProject} />);
    expect(screen.getByTestId("extraction-source-locked")).toBeInTheDocument();
    expect(screen.getByTestId("reset-source-link")).toBeInTheDocument();
    expect(screen.queryByTestId("extraction-source-select")).toBeNull();
  });

  it("should open ResetSourceModal when reset link is clicked", async () => {
    render(<SettingsForm project={lockedProject} />);
    await userEvent.click(screen.getByTestId("reset-source-link"));
    expect(screen.getByTestId("reset-source-modal")).toBeInTheDocument();
  });

  it("should call clientFetch PUT extraction-source with new source via ResetSourceModal", async () => {
    render(<SettingsForm project={lockedProject} />);
    await userEvent.click(screen.getByTestId("reset-source-link"));
    // Default newSource is "transcript" (opposite of locked "summary")
    await userEvent.click(screen.getByTestId("reset-source-confirm"));
    expect(mockClientFetch).toHaveBeenCalledWith(
      "/api/projects/proj-1/extraction-source",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ extraction_source: "transcript", re_extract: false }),
      }),
    );
  });
});

// ─── InterviewsTabClient ─────────────────────────────────────────────────────
describe("InterviewsTabClient", () => {
  const mockInterviews: InterviewAssignment[] = [
    {
      interview_id: "iv-1",
      date: "2026-02-28T10:00:00Z",
      summary_preview: "User had issues with navigation",
      fact_count: 4,
      extraction_status: "completed",
      clustering_status: "completed",
    },
    {
      interview_id: "iv-2",
      date: "2026-02-27T09:00:00Z",
      summary_preview: "Pricing was confusing",
      fact_count: 0,
      extraction_status: "failed",
      clustering_status: "failed",
    },
  ];

  beforeEach(() => {
    mockClientFetch.mockReset().mockResolvedValue({});
    mockRefresh.mockReset();
  });

  it("should render interview table with status badges", () => {
    render(<InterviewsTabClient projectId="proj-1" initialInterviews={mockInterviews} />);
    expect(screen.getByTestId("interviews-table")).toBeInTheDocument();
    expect(screen.getByTestId("interview-status-iv-1").textContent).toBe("analyzed");
    expect(screen.getByTestId("interview-status-iv-2").textContent).toBe("failed");
  });

  it("should show retry button for failed interviews", () => {
    render(<InterviewsTabClient projectId="proj-1" initialInterviews={mockInterviews} />);
    expect(screen.getByTestId("retry-button-iv-2")).toBeInTheDocument();
    expect(screen.queryByTestId("retry-button-iv-1")).toBeNull();
  });

  it("should call retry endpoint via clientFetch and refresh on retry click", async () => {
    render(<InterviewsTabClient projectId="proj-1" initialInterviews={mockInterviews} />);
    await userEvent.click(screen.getByTestId("retry-button-iv-2"));
    expect(mockClientFetch).toHaveBeenCalledWith(
      "/api/projects/proj-1/interviews/iv-2/retry",
      expect.objectContaining({ method: "POST" }),
    );
    await waitFor(() => expect(mockRefresh).toHaveBeenCalled());
  });

  it("should show empty state when no interviews", () => {
    render(<InterviewsTabClient projectId="proj-1" initialInterviews={[]} />);
    expect(screen.getByTestId("empty-state-interviews")).toBeInTheDocument();
  });
});

// ─── AssignInterviewsModal ───────────────────────────────────────────────────
describe("AssignInterviewsModal", () => {
  const mockAvailable: AvailableInterview[] = [
    { session_id: "sess-1", created_at: "2026-02-28T10:00:00Z", summary_preview: "Preview 1" },
    { session_id: "sess-2", created_at: "2026-02-27T09:00:00Z", summary_preview: "Preview 2" },
  ];

  beforeEach(() => {
    mockClientFetch.mockReset();
  });

  it("should load and display available interviews", async () => {
    mockClientFetch.mockResolvedValueOnce(mockAvailable);
    render(
      <AssignInterviewsModal projectId="proj-1" onClose={vi.fn()} onAssigned={vi.fn()} />,
    );
    await waitFor(() =>
      expect(screen.getByTestId("assign-checkbox-sess-1")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("assign-checkbox-sess-2")).toBeInTheDocument();
  });

  it("should keep assign button disabled until at least 1 is selected", async () => {
    mockClientFetch.mockResolvedValueOnce(mockAvailable);
    render(
      <AssignInterviewsModal projectId="proj-1" onClose={vi.fn()} onAssigned={vi.fn()} />,
    );
    await waitFor(() => screen.getByTestId("assign-checkbox-sess-1"));
    expect(screen.getByTestId("assign-modal-confirm")).toBeDisabled();
    await userEvent.click(screen.getByTestId("assign-checkbox-sess-1"));
    expect(screen.getByTestId("assign-modal-confirm")).not.toBeDisabled();
  });

  it("should call POST interviews with selected IDs on confirm via clientFetch", async () => {
    mockClientFetch.mockResolvedValueOnce(mockAvailable).mockResolvedValueOnce({});
    const onAssigned = vi.fn();
    render(
      <AssignInterviewsModal projectId="proj-1" onClose={vi.fn()} onAssigned={onAssigned} />,
    );
    await waitFor(() => screen.getByTestId("assign-checkbox-sess-1"));
    await userEvent.click(screen.getByTestId("assign-checkbox-sess-1"));
    await userEvent.click(screen.getByTestId("assign-modal-confirm"));
    expect(mockClientFetch).toHaveBeenCalledWith(
      "/api/projects/proj-1/interviews",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ interview_ids: ["sess-1"] }),
      }),
    );
    await waitFor(() => expect(onAssigned).toHaveBeenCalled());
  });
});
```
</test_spec>

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig und vollstaendig
- [ ] JWT Auth: Login, Cookie, Middleware, Logout implementiert
- [ ] Alle Endpoints mit `Depends(get_current_user)` geschuetzt
- [ ] Settings Tab: General + Model Config + Danger Zone vollstaendig
- [ ] Interviews Tab: Tabelle + Status-Badges + Retry + Assign-Modal vollstaendig
- [ ] Loading Skeletons fuer Projekt-Liste, Cluster-Grid, Facts-Liste
- [ ] Empty States fuer alle Screens
- [ ] Error Boundaries fuer Cluster-Detail und Projekt-Dashboard
- [ ] 404-Seite implementiert
- [ ] Keine hardcodierten Tokens im Code
- [ ] `JWT_SECRET` nur aus Environment-Variable (`settings.jwt_secret`)

---

## Integration Contract (GATE 2 PFLICHT)

> **Wichtig:** Diese Section wird vom Gate 2 Compliance Agent geprueft.

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| slice-01-db-schema-projekt-crud | `users` Tabelle | DB Schema | EXISTS — `UserRepository.get_by_email()`, `get_by_id()` |
| slice-01-db-schema-projekt-crud | `projects` Tabelle mit `user_id` FK | DB Schema | EXISTS — owner-check `project.user_id == current_user.id` |
| slice-04-dashboard-projekt-cluster-uebersicht | `dashboard/lib/api-client.ts` | File | EXISTS — wird um `apiFetch()` mit Auth-Header erweitert |
| slice-04-dashboard-projekt-cluster-uebersicht | `dashboard/app/projects/[id]/page.tsx` | Server Component | EXISTS — wird erweitert um Token-Prop an Client-Component |
| slice-04-dashboard-projekt-cluster-uebersicht | `dashboard/components/EmptyState.tsx` | Component | EXISTS — wird erweitert um neue Varianten |
| slice-04-dashboard-projekt-cluster-uebersicht | `dashboard/components/SkeletonCard.tsx` | Component | EXISTS — wird erweitert um `cluster`, `fact`, `row` Varianten |
| slice-07-live-updates-sse | `useProjectEvents(projectId, token, callbacks)` | Hook | EXISTS — Token als 2. Parameter bereits definiert |
| slice-07-live-updates-sse | `backend/app/auth/middleware.py::get_current_user_from_token` | Function | EXISTS — bereits im SSE-Endpoint verwendet |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `get_current_user()` | FastAPI Dependency | Alle Backend-Routes | `async (credentials, db) => dict[id, email, ...]` |
| `get_current_user_from_token()` | FastAPI Dependency | SSE Route (Slice 7) | `async (token, db) => dict[id, email, ...]` |
| `AuthService.login()` | Method | `auth_routes.py` | `async (email, password) => {access_token, token_type, user}` |
| `AuthService.decode_token()` | Static Method | `middleware.py` | `(token: str) => user_id: str` |
| `UserAvatar` | React Component | App Layout | `{email: string}` |
| `ErrorBoundary` | React Component | Dashboard Pages | `{children, fallback?}` |
| `EmptyState` | React Component | All Tab-Sections | `{variant, onAction?}` |
| `SkeletonCard` / `SkeletonGrid` | React Component | Loading States | `{variant, count?}` |

### Integration Validation Tasks

- [ ] `get_current_user` Dependency funktioniert in `project_routes.py` (returns user dict mit `id`)
- [ ] Cookie `auth_token` wird von Next.js Route Handler korrekt als HttpOnly gesetzt
- [ ] Next.js Middleware liest Cookie und redirected korrekt
- [ ] `apiFetch` schickt `Authorization: Bearer <token>` Header
- [ ] `useProjectEvents` in `page.tsx` erhaelt Token aus `getAuthToken()` (Server-seitig)
- [ ] Settings Tab `PUT /api/projects/{id}` gibt `ProjectResponse` zurueck mit `extraction_source_locked`
- [ ] Delete `DELETE /api/projects/{id}` gibt `204 No Content` zurueck

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele sind PFLICHT-Deliverables.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `AuthService` | Section 3 (Backend Auth) | YES | Exakt wie spezifiziert (login + decode_token) |
| `get_current_user()` | Section 3 (Auth Middleware) | YES | FastAPI Dependency mit HTTPBearer |
| `get_current_user_from_token()` | Section 3 (Auth Middleware) | YES | FastAPI Dependency fuer SSE |
| `LoginRequest` / `AuthResponse` Pydantic models | Section 3 (Auth Routes) | YES | auth_routes.py |
| `POST /api/auth/login` route | Section 3 (Auth Routes) | YES | Ruft AuthService.login() auf |
| `GET /api/auth/me` route | Section 3 (Auth Routes) | YES | Gibt UserResponse zurueck |
| `UserRepository` | Section 3 (Auth Repository) | YES | get_by_email + get_by_id |
| `middleware.ts` | Section 4 (Frontend Middleware) | YES | matcher fuer `/projects/:path*` |
| Route Handler `POST /api/auth/login` | Section 4 (Route Handler Login) | YES | Setzt HttpOnly Cookie |
| Route Handler `POST /api/auth/logout` | Section 4 (Route Handler Logout) | YES | Loescht Cookie |
| `getAuthToken()` | Section 4 (Auth Helper) | YES | Server-seitiger Cookie-Leser |
| `apiFetch<T>()` | Section 4 (API Client) | YES | Auth-aware fetch wrapper mit 401-Handling |
| `LoginPage` | Section 5 (Login Screen) | YES | Exakt wie spezifiziert inkl. data-testids |
| `UserAvatar` | Section 6 (UserAvatar) | YES | Mit Initialen + Logout-Dropdown |
| `SkeletonCard` / `SkeletonGrid` | Section 7 (Skeletons) | YES | Alle 4 Varianten (project, cluster, fact, row) |
| `EmptyState` | Section 8 (Empty States) | YES | Alle 4 Varianten mit Config |
| `ErrorBoundary` | Section 9 (Error Boundary) | YES | Class Component mit getDerivedStateFromError |
| `not-found.tsx` | Section 10 (404) | YES | Mit "Back to Projects" Link |
| `SettingsForm` | Section 11 (Settings Tab) | YES | General-Settings inkl. extraction_source_locked |
| `ModelConfigForm` | Section 11 (Settings Tab) | YES | 4 Model-Felder mit isValid/isDirty |
| `DangerZone` | Section 11 (Settings Tab) | YES | Type-to-confirm Modal |
| `InterviewsTabClient` | Section 12 (Interviews Tab) | YES | Tabelle + Status-Badges + Retry |
| `AssignInterviewsModal` | Section 12 (Interviews Tab) | YES | Checkbox-Liste + Assign-Button |

---

## Links

- Architecture: `specs/phase-4/2026-02-28-llm-interview-clustering/architecture.md` → Section "Security"
- Wireframes: `specs/phase-4/2026-02-28-llm-interview-clustering/wireframes.md` → "Screen: Project Settings Tab", "Screen: Project Interviews Tab"
- Discovery: `specs/phase-4/2026-02-28-llm-interview-clustering/discovery.md` → "Business Rules", "Data → Projekt"
- Slice 7 (SSE): `slice-07-live-updates-sse.md` → `useProjectEvents` Hook Interface
- Slice 4 (Dashboard): `slice-04-dashboard-projekt-cluster-uebersicht.md` → API Client, Next.js Setup

---

## Deliverables (SCOPE SAFEGUARD)

<!-- DELIVERABLES_START -->
### Backend

- [ ] `backend/app/auth/service.py` — `AuthService`: `login()`, `_create_token()`, `decode_token()`
- [ ] `backend/app/auth/middleware.py` — `get_current_user()`, `get_current_user_from_token()` FastAPI Dependencies
- [ ] `backend/app/auth/repository.py` — `UserRepository`: `get_by_email()`, `get_by_id()`
- [ ] `backend/app/api/auth_routes.py` — `POST /api/auth/login`, `GET /api/auth/me`
- [ ] `backend/app/api/project_routes.py` — Alle Endpoints mit `Depends(get_current_user)` erweitert
- [ ] `backend/app/api/cluster_routes.py` — Alle Endpoints mit `Depends(get_current_user)` erweitert
- [ ] `backend/app/main.py` — `auth_router` registriert
- [ ] `backend/requirements.txt` — `python-jose[cryptography]==3.3.0`, `passlib[bcrypt]==1.7.4` hinzugefuegt

### Frontend

- [ ] `dashboard/middleware.ts` — Next.js Middleware fuer `/projects/:path*`
- [ ] `dashboard/app/login/page.tsx` — Login-Screen (Client Component)
- [ ] `dashboard/app/api/auth/login/route.ts` — Route Handler: setzt HttpOnly Cookie
- [ ] `dashboard/app/api/auth/logout/route.ts` — Route Handler: loescht Cookie
- [ ] `dashboard/lib/auth.ts` — `getAuthToken()` Server-Helper
- [ ] `dashboard/lib/api-client.ts` — Erweitert um `apiFetch()` mit Auth-Header + 401-Handling
- [ ] `dashboard/lib/client-api.ts` — `clientFetch()` Browser-Helper fuer Client Components (via Proxy)
- [ ] `dashboard/app/api/proxy/[...path]/route.ts` — Next.js Catch-All Proxy Route Handler (liest HttpOnly Cookie, setzt Authorization-Header, leitet an FastAPI weiter)
- [ ] `dashboard/components/UserAvatar.tsx` — Avatar mit Initialen + Logout-Dropdown
- [ ] `dashboard/components/SkeletonCard.tsx` — Erweitert um `cluster`, `fact`, `row` Varianten
- [ ] `dashboard/components/EmptyState.tsx` — Erweitert um `interviews` Variante
- [ ] `dashboard/components/ErrorBoundary.tsx` — React Error Boundary (Class Component)
- [ ] `dashboard/app/not-found.tsx` — 404-Seite
- [ ] `dashboard/app/projects/[id]/settings/page.tsx` — Settings Tab Server Component
- [ ] `dashboard/components/SettingsForm.tsx` — General Settings Form
- [ ] `dashboard/components/ModelConfigForm.tsx` — Model Configuration Form
- [ ] `dashboard/components/DangerZone.tsx` — Delete Project mit Type-to-confirm Modal
- [ ] `dashboard/app/projects/[id]/interviews/page.tsx` — Interviews Tab Server Component (erweitert)
- [ ] `dashboard/components/InterviewsTabClient.tsx` — Interview-Tabelle Client Component
- [ ] `dashboard/components/AssignInterviewsModal.tsx` — Assign-Modal Client Component

### Tests

- [ ] `tests/slices/llm-interview-clustering/slice-08-auth-polish.test.ts` — Vitest Unit Tests (alle describe-Bloecke)
<!-- DELIVERABLES_END -->

**Hinweis fuer den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind Pflicht
- Der Stop-Hook prueft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen
- `ResetSourceModal` (in `SettingsForm.tsx`) ist als internes Modal implementiert, keine separate Datei
- Backend `auth/` Verzeichnis muss auch `__init__.py` enthalten
