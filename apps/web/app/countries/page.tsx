import { CountryList } from "@/components/country-list";

export const metadata = {
  title: "Countries — Big Cycle Atlas",
};

export default function CountriesPage() {
  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-16">
      <h1 className="headline-lg">Countries</h1>
      <p className="body-md mt-4 max-w-xl text-secondary">
        All countries currently tracked by the Atlas. Data is served by the API and
        stored in the database.
      </p>
      <div className="mt-12">
        <CountryList />
      </div>
    </div>
  );
}