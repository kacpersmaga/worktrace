// Mirrors backend/worktrace/schemas.py one to one.

export type Severity = "critical" | "high" | "medium" | "low";

export interface Signal {
  key: string;
  label: string;
  value: number;
  display: string;
  percentile: number;
}

export interface DataQuality {
  source_format: "kyp_activity_sequence" | "event_log";
  rows_read: number;
  rows_dropped: Record<string, number>;
  steps: number;
  rows_per_step: number;
  case_strategy: "business_id" | "work_session" | "case_column";
  cases: number;
  cases_cut_off: number;
  business_ids_found: number;
  business_ids_rejected: string[];
  steps_with_business_id: number;
  steps_with_imputed_id: number;
  export_metadata: Record<string, string>;
  notes: string[];
}

export interface Overview {
  users: number;
  cases: number;
  steps: number;
  activities: number;
  applications: number;
  start: string;
  end: string;
  active_days: number;
  tracked_hours: number;
  active_hours: number;
  idle_hours: number;
  median_case_minutes: number;
  p90_case_minutes: number;
  copy_paste_operations: number;
  cross_app_transfers: number;
  app_switches_per_hour: number;
}

export interface AppUsage {
  app: string;
  active_hours: number;
  idle_hours: number;
  steps: number;
  share: number;
}

export interface HeatCell {
  weekday: number;
  hour: number;
  active_hours: number;
}

export interface MapNode {
  id: string;
  label: string;
  app: string;
  count: number;
  cases: number;
  median_seconds: number;
  total_hours: number;
  kind: "start" | "end" | "activity";
}

export interface MapEdge {
  source: string;
  target: string;
  count: number;
  cases: number;
  dependency: number;
  median_wait_seconds: number;
  p90_wait_seconds: number;
}

export interface ProcessMap {
  nodes: MapNode[];
  edges: MapEdge[];
  cases: number;
  activities_total: number;
}

export interface Variant {
  id: number;
  steps: string[];
  cases: number;
  share: number;
  cumulative_share: number;
  median_minutes: number;
  distance_from_main: number;
}

export interface Deviation {
  kind: "skipped" | "inserted" | "replaced";
  activity: string;
  cases: number;
  share: number;
}

export interface VariantAnalysis {
  total_variants: number;
  main_path: string[];
  main_path_share: number;
  top5_coverage: number;
  variants: Variant[];
  deviations: Deviation[];
}

export interface Share {
  label: string;
  share: number;
  detail: string;
}

export interface Cause {
  kind: string;
  title: string;
  evidence: string;
  action: string;
  hours: number;
  impact: string;
  examples: string[];
}

export interface Diagnosis {
  summary: string;
  per_run: Record<string, number>;
  time_split: Share[];
  screens: Share[];
  before: Share[];
  after: Share[];
  data_in: Share[];
  data_out: Share[];
  causes: Cause[];
}

export interface Bottleneck {
  kind: "step" | "handover";
  activity: string;
  next_activity: string | null;
  score: number;
  severity: Severity;
  hours_lost: number;
  median_seconds: number;
  p90_seconds: number;
  occurrences: number;
  cases: number;
  signals: Signal[];
  evidence: string[];
  diagnosis: Diagnosis | null;
}

export interface ReworkLoop {
  pattern: string[];
  occurrences: number;
  cases: number;
  share_of_cases: number;
  hours: number;
}

export interface AppSwitch {
  from_app: string;
  to_app: string;
  switches: number;
  ping_pongs: number;
}

export interface ContextSwitching {
  switches: number;
  switches_per_hour: number;
  ping_pong_share: number;
  pairs: AppSwitch[];
}

export interface ClipboardFlow {
  source_app: string;
  target_app: string;
  source_step: string;
  target_step: string;
  transfers: number;
  users: number;
}

export interface AutomationCandidate {
  activity: string;
  app: string;
  approach: string;
  score: number;
  hours_per_week: number;
  saving_hours_per_week: number;
  automation_rate: number;
  executions_per_week: number;
  signals: Signal[];
  rationale: string[];
  diagnosis: Diagnosis | null;
  blueprint: string[];
}

export interface Routine {
  steps: string[];
  occurrences: number;
  cases: number;
  median_seconds: number;
  hours: number;
}

export interface Person {
  user: string;
  alias: string;
  cases: number;
  steps: number;
  active_hours: number;
  idle_share: number;
  median_case_minutes: number;
  speed_index: number | null;
  rework_rate: number;
  switches_per_hour: number;
  clipboard_per_hour: number;
  top_apps: string[];
}

export interface TimelineSegment {
  app: string;
  activity: string;
  start: string;
  end: string;
  idle: boolean;
}

export interface PersonDay {
  alias: string;
  date: string;
  segments: TimelineSegment[];
}

export interface AnomalousCase {
  case_id: string;
  user: string;
  start: string;
  minutes: number;
  steps: number;
  score: number;
  reasons: string[];
}

export interface Finding {
  tone: "warning" | "opportunity" | "info";
  title: string;
  detail: string;
  tab: string;
}

export interface Analysis {
  id: string;
  name: string;
  period: "day" | "week";
  synthetic: boolean;
  quality: DataQuality;
  overview: Overview;
  findings: Finding[];
  apps: AppUsage[];
  heatmap: HeatCell[];
  process_map: ProcessMap;
  variants: VariantAnalysis;
  bottlenecks: Bottleneck[];
  rework: ReworkLoop[];
  switching: ContextSwitching;
  clipboard: ClipboardFlow[];
  automation: AutomationCandidate[];
  routines: Routine[];
  people: Person[];
  timelines: PersonDay[];
  anomalies: AnomalousCase[];
}

export interface Job {
  id: string;
  name: string;
  created: string;
  status: "running" | "done" | "failed";
  error: string | null;
}

export interface Demo {
  key: string;
  name: string;
  description: string;
  synthetic: boolean;
}

export interface Explanation {
  text: string;
  source: "gemini" | "rules";
}
