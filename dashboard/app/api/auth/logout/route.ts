// dashboard/app/api/auth/logout/route.ts
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export async function POST(): Promise<NextResponse> {
  (await cookies()).delete("auth_token");
  return NextResponse.json({ success: true });
}
