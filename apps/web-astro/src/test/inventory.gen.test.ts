import { it } from "vitest";
import { writeFileSync, readFileSync } from "node:fs";
import "@/features/widgets";
import { listWidgets } from "@/features/workspace/widgetRegistry";

const DOC = "../../docs/WIDGET_REGISTRY.md";

it("widget registry doc matches the live registry (drift check)", () => {
  const defs = listWidgets();
  const lines = [
    "# Widget Registry",
    "",
    `Generated from \`src/features/widgets/index.ts\` — ${defs.length} registered widget types.`,
    "",
    "| ID | Name | Category | Default | Min | Data requirement |",
    "|---|---|---|---|---|---|",
    ...defs.map(
      (d) =>
        `| \`${d.typeId}\` | ${d.displayName} | ${d.category} | ${d.defaultSize.w}×${d.defaultSize.h} | ${d.minSize.w}×${d.minSize.h} | ${d.dataRequirement.replace(/\|/g, "/")} |`,
    ),
    "",
    "## Config fields per widget",
    "",
    ...defs.map(
      (d) =>
        `### \`${d.typeId}\` — ${d.displayName}\n\n${d.description}\n\n${d.configFields.map((f) => `- \`${f.key}\` (${f.type})${f.default !== undefined ? ` — default \`${JSON.stringify(f.default)}\`` : ""}`).join("\n") || "- none"}\n`,
    ),
  ];
  const generated = lines.join("\n");
  if (process.env.REGEN === "1") {
    writeFileSync(DOC, generated);
    return;
  }
  const committed = readFileSync(DOC, "utf-8");
  if (committed !== generated) {
    throw new Error(
      "docs/WIDGET_REGISTRY.md is stale — regenerate with REGEN=1",
    );
  }
});
