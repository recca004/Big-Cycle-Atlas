import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  fetchForceScores,
  fetchCountryObservations,
  fetchCountries,
  API_URL,
} from "@/lib/api/client";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

function okJson(body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
}

beforeEach(() => mockFetch.mockReset());

describe("api client", () => {
  it("builds force-scores URL", async () => {
    mockFetch.mockReturnValue(okJson({ iso3: "USA", forces: [] }));
    await fetchForceScores("USA");
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_URL}/api/countries/USA/force-scores`,
      expect.anything(),
    );
  });

  it("passes period query param", async () => {
    mockFetch.mockReturnValue(okJson({ iso3: "USA", forces: [] }));
    await fetchForceScores("USA", "2024-Q4");
    const url = mockFetch.mock.calls[0]![0] as string;
    expect(url).toContain("period=2024-Q4");
  });

  it("builds observations URL with indicator and limit", async () => {
    mockFetch.mockReturnValue(okJson([]));
    await fetchCountryObservations("CHE", { indicator: "GINI_INDEX", limit: 24 });
    const url = mockFetch.mock.calls[0]![0] as string;
    expect(url).toContain("/countries/CHE/observations");
    expect(url).toContain("indicator=GINI_INDEX");
    expect(url).toContain("limit=24");
  });

  it("returns parsed JSON on success", async () => {
    mockFetch.mockReturnValue(okJson([{ iso3: "USA" }]));
    const out = await fetchCountries();
    expect(out).toEqual([{ iso3: "USA" }]);
  });

  it("throws on non-OK responses", async () => {
    mockFetch.mockReturnValue(
      Promise.resolve(new Response("nope", { status: 404 })),
    );
    await expect(fetchCountries()).rejects.toThrow();
  });
});
