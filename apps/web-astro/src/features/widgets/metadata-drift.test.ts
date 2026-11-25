import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

/** Regression: the workspace used to hardcode normalization-v0.8 /
 *  force-aggregation-v0.3 while the engine moved on. Widget source must
 *  never contain hardcoded engine version strings — versions come from
 *  GET /api/research/versions. */
function* walk(dir: string): Generator<string> {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      if (entry === "node_modules" || entry.startsWith(".")) continue;
      yield* walk(full);
    } else if (/\.(ts|tsx|astro)$/.test(entry) && !/\.test\./.test(entry)) {
      yield full;
    }
  }
}

describe("metadata drift prevention", () => {
  it("no hardcoded engine model versions in frontend source", () => {
    const offenders: string[] = [];
    for (const file of walk(join(__dirname, "../../"))) {
      const text = readFileSync(file, "utf-8");
      for (const match of text.matchAll(/normalization-v\d+\.\d+|force-aggregation-v\d+\.\d+/g)) {
        offenders.push(`${file}: ${match[0]}`);
      }
    }
    expect(offenders).toEqual([]);
  });
});
