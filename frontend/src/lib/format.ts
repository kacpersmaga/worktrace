const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });
const whole = new Intl.NumberFormat("en");

export function count(value: number): string {
  return value >= 10_000 ? compact.format(value) : whole.format(Math.round(value));
}

export function percent(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function hours(value: number): string {
  if (value >= 100) return `${whole.format(Math.round(value))} h`;
  if (value >= 1) return `${value.toFixed(1)} h`;
  return `${Math.round(value * 60)} min`;
}

export function duration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)} s`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(seconds < 600 ? 1 : 0)} min`;
  if (seconds < 86400) return `${(seconds / 3600).toFixed(1)} h`;
  return `${(seconds / 86400).toFixed(1)} days`;
}

export function minutes(value: number): string {
  return duration(value * 60);
}

export function dateRange(start: string, end: string): string {
  const options: Intl.DateTimeFormatOptions = { day: "numeric", month: "short", year: "numeric" };
  const from = new Date(start).toLocaleDateString("en-GB", options);
  const to = new Date(end).toLocaleDateString("en-GB", options);
  return from === to ? from : `${from} – ${to}`;
}

export function clockTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}
