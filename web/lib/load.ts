import { neon } from "@neondatabase/serverless";
import fs from "fs";
import path from "path";

export type Payload = {
  _meta: Record<string, unknown>;
  table: Array<Record<string, unknown>>;
  clubs: Array<Record<string, unknown> & { id: string }>;
  bracket: Record<string, unknown>;
};

export async function loadPayload(): Promise<Payload | null> {
  const url = process.env.DATABASE_URL;
  if (url) {
    try {
      const sql = neon(url);
      const rows = await sql`SELECT payload FROM runs ORDER BY id DESC LIMIT 1`;
      const payload = rows[0]?.payload as Payload | undefined;
      if (payload?.clubs) return payload;
    } catch {
      // Fall through to the JSON written by update.py.
    }
  }

  const candidates = [
    path.join(process.cwd(), "data", "predictions.json"),
    path.join(process.cwd(), "..", "data", "predictions.json"),
  ];
  for (const file of candidates) {
    if (fs.existsSync(file)) {
      return JSON.parse(fs.readFileSync(file, "utf8")) as Payload;
    }
  }
  return null;
}
