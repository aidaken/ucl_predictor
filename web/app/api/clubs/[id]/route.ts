import { NextResponse } from "next/server";
import { loadPayload } from "@/lib/load";

export const dynamic = "force-dynamic";

export async function GET(_request: Request, context: { params: { id: string } }) {
  const payload = await loadPayload();
  if (!payload) {
    return NextResponse.json({ error: "no predictions yet" }, { status: 404 });
  }
  const id = context.params.id.toUpperCase();
  const club = payload.clubs.find((row) => row.id.toUpperCase() === id);
  if (!club) {
    return NextResponse.json({ error: "club not found" }, { status: 404 });
  }
  return NextResponse.json({ _meta: payload._meta, club });
}
