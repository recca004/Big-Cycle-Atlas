/// <reference types="vitest" />
import { getViteConfig } from "astro/config";

export default getViteConfig({
  // @ts-expect-error -- vitest config passthrough
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
