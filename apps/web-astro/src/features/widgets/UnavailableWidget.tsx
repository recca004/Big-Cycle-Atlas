import type { WidgetProps } from "@/features/workspace/widgetRegistry";
import { WidgetUnavailable } from "./common";

/** Generic unavailable widget — carries an explicit reason instead of data. */
export function UnavailableWidget({ config }: WidgetProps) {
  return (
    <WidgetUnavailable
      reason={
        (config.reason as string) ||
        "This widget's data or scoring method is not implemented yet."
      }
      sourceStatus={config.sourceStatus as string | undefined}
      methodologyStatus={config.methodologyStatus as string | undefined}
    />
  );
}
