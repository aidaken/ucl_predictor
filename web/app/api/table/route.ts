import { NextResponse } from "next/server";
import { loadPayload } from "@/lib/load";

export const dynamic = "force-dynamic";

export async function GET() {
  const payload = await loadPayload();
  if (!payload) {
    return NextResponse.json({ error: "no predictions yet" }, { status: 404 });
  }
  return NextResponse.json({ _meta: payload._meta, table: payload.table });
}
