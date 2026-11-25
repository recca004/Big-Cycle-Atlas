import { fetchCycleHistory, fetchForceHistory } from "@/lib/api/client";
import type {
  CycleHistoryResponse,
  ForceHistoryResponse,
} from "@/types/research";
import { EChart } from "@/lib/charts/EChart";
import { cycleHistoryOption } from "@/lib/charts/cycleChart";
import { forceHistoryOption } from "@/lib/charts/forceChart";
import { useFetch } from "@/lib/ui/shared";
import { WidgetError, WidgetLoading } from "./common";
import type { WidgetProps } from "@/features/workspace/widgetRegistry";

/** Experimental Big Cycle history — retains experimental status when added
 *  to any workspace (Mission 3 §10/§23). */
export function CycleHistoryWidget({ config }: WidgetProps) {
  const iso3 = String(config.country ?? "USA");
  const model = String(config.model ?? "model_b_domain");
  const startYear = Number(config.startYear ?? 2000);
  const h = useFetch<CycleHistoryResponse>(
    (c) => fetchCycleHistory(iso3, model, startYear, { signal: c.signal }),
    [iso3, model, startYear],
  );
  if (h.kind === "loading") return <WidgetLoading />;
  if (h.kind === "error") return <WidgetError detail={h.error} />;
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <span className="badge badge-warn" style={{ alignSelf: "flex-start" }}>
        EXPERIMENTAL
      </span>
      <div style={{ flex: 1, minHeight: 0 }}>
        <EChart option={cycleHistoryOption(h.data)}
                ariaLabel={`Experimental cycle history ${iso3}`} />
      </div>
    </div>
  );
}

/** Historical force dimensions — level / relative / momentum, missing
 *  values never connected across gaps. */
export function ForceHistoryWidget({ config }: WidgetProps) {
  const iso3 = String(config.country ?? "USA");
  const force = String(config.force ?? "rule_of_law");
  const startYear = Number(config.startYear ?? 1996);
  const h = useFetch<ForceHistoryResponse>(
    (c) => fetchForceHistory(iso3, force, startYear, { signal: c.signal }),
    [iso3, force, startYear],
  );
  if (h.kind === "loading") return <WidgetLoading />;
  if (h.kind === "error") return <WidgetError detail={h.error} />;
  return (
    <EChart option={forceHistoryOption(h.data)}
            ariaLabel={`Force history ${force} ${iso3}`} />
  );
}
