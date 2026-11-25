import { describe, it, expect } from "vitest";
import { toCsv } from "@/lib/export";

describe("toCsv", () => {
  it("emits headers and rows", () => {
    const csv = toCsv(["a", "b"], [[1, "x"], [2, "y"]]);
    expect(csv).toBe('a,b\n1,x\n2,y\n');
  });

  it("guards against formula injection", () => {
    const csv = toCsv(["v"], [
      ["=1+1"],
      ["+SUM(A1:A2)"],
      ["-10"],
      ["@cmd"],
      ["normal"],
      [10.5],
    ]);
    const lines = csv.trim().split("\n").slice(1);
    expect(lines).toEqual([
      "'=1+1",
      "'+SUM(A1:A2)",
      "'-10",
      "'@cmd",
      "normal",
      "10.5",
    ]);
  });

  it("quotes cells with commas and escapes quotes", () => {
    const csv = toCsv(["v"], [['say "hi"'], ["a,b"], ["line\nbreak"], [null]]);
    // Embedded newlines stay inside the quoted cell; the null row is empty.
    const lines = csv.split("\n");
    expect(lines[1]).toBe('"say ""hi"""');
    expect(lines[2]).toBe('"a,b"');
    expect(lines[3]).toBe('"line');
    expect(lines[4]).toBe('break"');
    expect(lines[5]).toBe("");
  });
});
