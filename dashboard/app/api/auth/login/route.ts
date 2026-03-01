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
      { error: (error as { detail?: string }).detail ?? "Invalid credentials" },
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
