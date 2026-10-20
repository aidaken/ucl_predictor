import { neon } from "@neondatabase/serverless";
import fs from "fs";
import path from "path";

export type Payload = {
  _meta: Record<string, unknown>;
  table: Array<Record<string, unknown>>;
  clubs: Array<Record<string, unknown> & { id: string }>;
  bracket: Record<string, unknown>;
};

function versionKey(value: unknown): number[] {
  return String(value || "0")
    .split(".")
    .map((part) => {
      const digits = part.match(/^\d+/);
      return digits ? Number(digits[0]) : 0;
    });
}

function compareVersions(left: unknown, right: unknown): number {
  const a = versionKey(left);
  const b = versionKey(right);
  const length = Math.max(a.length, b.length);
  for (let index = 0; index < length; index += 1) {
    const gap = (a[index] || 0) - (b[index] || 0);
    if (gap) return gap;
  }
  return 0;
}

export async function loadPayload(): Promise<Payload | null> {
  const url = process.env.DATABASE_URL;
  if (url) {
    try {
      const sql = neon(url, { fetchOptions: { cache: "no-store" } });
      // Newest row is not enough. A scheduled job on an old checkout can insert
      // a later id with an older model, and that is what put Real Madrid back
      // on top. Serve the highest model version, then the latest id of that version.
      const rows = await sql`SELECT id, model_version, payload FROM runs`;
      const ranked = [...rows].sort((left, right) => {
        const byVersion = compareVersions(right.model_version, left.model_version);
        if (byVersion) return byVersion;
        return Number(right.id) - Number(left.id);
      });
      const payload = ranked[0]?.payload as Payload | undefined;
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
