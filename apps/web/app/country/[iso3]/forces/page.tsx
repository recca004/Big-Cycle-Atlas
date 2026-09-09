"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { fetchCountry, fetchForceCoverage } from "@/lib/api";
import type { ForceCoverage, ForceCoverageData, ForceInput } from "@/lib/api";
import type { Country } from "@/types/country";

const SOURCE_LABELS: Record<string, string> = {
  world_bank: "World Bank",
  bis: "BIS",
  oecd: "OECD",
};

const STATUS_LABELS: Record<ForceCoverage["status"], string> = {
  available: "Data available",
  partial: "Partially measurable",
  defined_not_sourced: "Indicators defined · data source pending",
  missing: "Data not yet available",
};

function inputLabel(input: ForceInput): string {
  const name = input.name ?? input.indicator_code;
  const source = input.source ? SOURCE_LABELS[input.source] ?? input.source : null;
  return source ? `${name} — ${source}` : name;
}

function latestPeriodLabel(input: ForceInput): string | null {
  if (!input.latest_period) return null;
  return new Date(input.latest_period).toISOString().slice(0, 10);
}

export default function ForcesPage() {
  const params = useParams<{ iso3: string }>();
  const iso3 = (params.iso3 ?? "").toUpperCase();
  const [country, setCountry] = useState<Country | null>(null);
  const [coverage, setCoverage] = useState<ForceCoverageData | null>(null);
  const [state, setState] = useState<"loading" | "error" | "not-found" | "ready">(
    "loading",
  );

  useEffect(() => {
    let cancelled = false;
    fetchCountry(iso3)
      .then(async (data) => {
        if (cancelled) return;
        if (data === null) {
          setState("not-found");
          return;
        }
        setCountry(data);
        try {
          const cov = await fetchForceCoverage(iso3);
          if (!cancelled) setCoverage(cov);
        } catch {
          if (!cancelled) setCoverage(null);
        }
        if (!cancelled) setState("ready");
      })
      .catch(() => {
        if (!cancelled) setState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [iso3]);

  const forces = coverage?.forces ?? [];
  const counts = {
    available: forces.filter((f) => f.status === "available").length,
    partial: forces.filter((f) => f.status === "partial").length,
    defined_not_sourced: forces.filter((f) => f.status === "defined_not_sourced")
      .length,
    missing: forces.filter((f) => f.status === "missing").length,
  };

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-16">
      <p className="label-md mb-8 text-tertiary">
        <Link href={`/country/${iso3}`} className="hover:text-primary">
          {country?.name ?? iso3}
        </Link>{" "}
        · Big Cycle forces
      </p>
      {state === "loading" && (
        <p className="text-sm text-tertiary">Loading force coverage…</p>
      )}
      {state === "error" && (
        <div className="rounded-lg border border-border bg-surface p-4">
          <p className="headline-sm">Force coverage is currently unavailable.</p>
          <p className="mt-2 text-sm text-tertiary">
            The Atlas could not reach the API. Start the backend with{" "}
            <code>uv run python run.py</code> from apps/api, then reload.
          </p>
        </div>
      )}
      {state === "not-found" && (
        <div className="rounded-lg border border-border bg-surface p-4">
          <p className="headline-sm">{iso3} is not tracked by the Atlas.</p>
          <Link
            href="/countries"
            className="mt-4 inline-flex h-[34px] items-center rounded-md bg-primary px-2.5 text-[13px] text-inverse hover:bg-accent"
          >
            Back to countries
          </Link>
        </div>
      )}
      {state === "ready" && (
        <>
          <h1 className="headline-lg">Big Cycle Forces</h1>
          <p className="mt-2 max-w-2xl text-sm text-tertiary">
            Data coverage per force — which forces the Atlas can currently
            measure, which have defined indicators without a data source, and
            which still need data. Coverage is not strength: no force scores
            are calculated yet.
          </p>

          <div className="mt-8 rounded-lg border border-border bg-surface p-4">
            <p className="headline-sm">17 Big Cycle forces</p>
            <p className="mt-2 text-sm text-tertiary">
              {counts.available} currently measurable · {counts.partial}{" "}
              partially measurable · {counts.defined_not_sourced} defined but
              not sourced · {counts.missing} still missing data
            </p>
          </div>

          <ol className="mt-8 space-y-4">
            {forces.map((force, index) => (
              <li
                key={force.code}
                className="rounded-lg border border-border bg-surface p-4"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="headline-sm">
                    {index + 1}. {force.name}
                  </p>
                  <p className="label-md text-tertiary">
                    {STATUS_LABELS[force.status]}
                  </p>
                </div>

                {force.live_inputs.length > 0 && (
                  <ul className="mt-3 space-y-1 text-sm">
                    {force.live_inputs.map((input) => (
                      <li key={input.indicator_code}>
                        {inputLabel(input)}
                        {input.has_data ? (
                          <span className="text-tertiary">
                            {latestPeriodLabel(input)
                              ? ` · through ${latestPeriodLabel(input)}`
                              : ""}
                          </span>
                        ) : (
                          <span className="text-tertiary"> · no data yet</span>
                        )}
                      </li>
                    ))}
                  </ul>
                )}

                {force.candidate_inputs.length > 0 && (
                  <ul className="mt-1 space-y-1 text-sm text-tertiary">
                    {force.candidate_inputs.map((input) => (
                      <li key={input.indicator_code}>
                        {input.name ?? input.indicator_code} — catalog only,
                        source pending
                      </li>
                    ))}
                  </ul>
                )}

                {force.status === "missing" && (
                  <p className="mt-3 text-sm text-tertiary">
                    Data not yet available
                  </p>
                )}
              </li>
            ))}
          </ol>

          <Link
            href={`/country/${iso3}`}
            className="mt-8 inline-flex h-[34px] items-center rounded-md bg-primary px-2.5 text-[13px] text-inverse hover:bg-accent"
          >
            Back to {country?.name ?? iso3}
          </Link>
        </>
      )}
    </div>
  );
}