import type { AsyncState } from "./hooks";

/** Shared widget body states — loading / error / empty / unavailable. */

export function WidgetLoading() {
  return (
    <div className="widget-state" role="status">
      <span className="widget-skeleton" aria-hidden="true" />
      <span className="body-sm">Loading…</span>
    </div>
  );
}

export function WidgetError({ detail }: { detail?: string }) {
  return (
    <div className="widget-state" role="alert">
      <p className="body-sm widget-state-title">Data unavailable</p>
      <p className="widget-state-detail">
        {detail ?? "The API could not be reached."}
      </p>
    </div>
  );
}

export function WidgetEmpty({ message }: { message: string }) {
  return (
    <div className="widget-state">
      <p className="body-sm widget-state-title">No data</p>
      <p className="widget-state-detail">{message}</p>
    </div>
  );
}

export interface UnavailableSpec {
  reason: string;
  sourceStatus?: string | undefined;
  methodologyStatus?: string | undefined;
}

/** Explicit unavailable state — never filled with fictional data. */
export function WidgetUnavailable({
  reason,
  sourceStatus,
  methodologyStatus,
}: UnavailableSpec) {
  return (
    <div className="widget-state widget-unavailable">
      <p className="body-sm widget-state-title">Not yet available</p>
      <p className="widget-state-detail">{reason}</p>
      {sourceStatus && (
        <p className="widget-state-detail">
          <span className="label-md">Source</span> {sourceStatus}
        </p>
      )}
      {methodologyStatus && (
        <p className="widget-state-detail">
          <span className="label-md">Methodology</span> {methodologyStatus}
        </p>
      )}
    </div>
  );
}

export function resolveAsync<T>(
  state: AsyncState<T>,
  render: (data: T) => React.ReactNode,
  emptyCheck?: (data: T) => string | null,
): React.ReactNode {
  if (state.kind === "loading") return <WidgetLoading />;
  if (state.kind === "error") return <WidgetError />;
  const empty = emptyCheck?.(state.data);
  if (empty) return <WidgetEmpty message={empty} />;
  return render(state.data);
}
