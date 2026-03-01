import { type NextRequest, NextResponse } from 'next/server'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
): Promise<NextResponse | Response> {
  const { id } = await params
  const token = request.nextUrl.searchParams.get('token')

  const upstreamUrl = `${API_BASE}/api/projects/${id}/events${token ? `?token=${encodeURIComponent(token)}` : ''}`

  const upstream = await fetch(upstreamUrl, {
    headers: { Accept: 'text/event-stream' },
  }).catch(() => null)

  if (!upstream || !upstream.ok || !upstream.body) {
    return NextResponse.json({ error: 'SSE upstream unavailable' }, { status: 502 })
  }

  return new Response(upstream.body, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  })
}
