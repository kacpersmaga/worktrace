import type { AppUsage } from "./types";

const SERIES = ["--series-1", "--series-2", "--series-3", "--series-4", "--series-5", "--series-6", "--series-7"];

/**
 * Applications keep one colour across every chart on the page. Colour follows the
 * app (ranked by time once, for the whole analysis), never its position in a chart.
 * Beyond seven apps the rest share a neutral "Other".
 */
export function appColors(apps: AppUsage[]): (app: string) => string {
  const assigned = new Map(apps.slice(0, SERIES.length).map((usage, index) => [usage.app, `var(${SERIES[index]})`]));
  return (app: string) => assigned.get(app) ?? "var(--series-other)";
}
