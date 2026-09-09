import Link from "next/link";
import { TrackedCountries } from "@/components/tracked-countries";

export default function HomePage() {
  return (
    <div className="mx-auto w-full max-w-6xl px-6">
      <section className="pb-16 pt-20">
        <p className="label-md mb-8 text-tertiary">A measurable Big Cycle framework</p>
        <h1 className="headline-display max-w-3xl">Where are we in the Big Cycle?</h1>
        <p className="body-md mt-8 max-w-[25rem] text-secondary">
          Big Cycle Atlas tracks the economic and institutional forces that shape the
          rise and decline of countries — 17 forces, scored from public data, placed
          into a transparent cycle model.
        </p>
        <div className="mt-10 flex gap-4">
          <Link
            href="/countries"
            className="inline-flex h-[34px] items-center rounded-md bg-primary px-2.5 text-[13px] text-inverse hover:bg-accent"
          >
            View countries
          </Link>
        </div>
      </section>

      <section className="border-t border-border pb-24 pt-12">
        <TrackedCountries />
      </section>
    </div>
  );
}