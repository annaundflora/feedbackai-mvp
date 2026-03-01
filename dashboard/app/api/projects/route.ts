import { cookies } from 'next/headers'
import { type NextRequest, NextResponse } from 'next/server'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function POST(request: NextRequest): Promise<NextResponse> {
  const body = await request.json()
  const cookieStore = await cookies()
  const token = cookieStore.get('auth_token')?.value

  const res = await fetch(`${API_BASE}/api/projects`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({}))
    return NextResponse.json(error, { status: res.status })
  }

  const data = await res.json()
  return NextResponse.json(data)
}
