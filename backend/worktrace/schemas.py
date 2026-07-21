"""Everything the engine returns. The frontend types mirror these models one to one."""

from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["critical", "high", "medium", "low"]
CaseStrategy = Literal["business_id", "work_session", "case_column"]


class Signal(BaseModel):
    """One measured input to a score, with its rank among all candidates (0 = lowest, 1 = highest)."""

    key: str
    label: str
    value: float
    display: str
    percentile: float


class DataQuality(BaseModel):
    source_format: Literal["kyp_activity_sequence", "event_log"]
    rows_read: int
    rows_dropped: dict[str, int]
    steps: int
    rows_per_step: float
    case_strategy: CaseStrategy
    cases: int
    cases_cut_off: int = 0
    business_ids_found: int
    business_ids_rejected: list[str]
    steps_with_business_id: float
    steps_with_imputed_id: int
    export_metadata: dict[str, str]
    notes: list[str]


class Overview(BaseModel):
    users: int
    cases: int
    steps: int
    activities: int
    applications: int
    start: str
    end: str
    active_days: int
    tracked_hours: float
    active_hours: float
    idle_hours: float
    median_case_minutes: float
    p90_case_minutes: float
    copy_paste_operations: int
    cross_app_transfers: int
    app_switches_per_hour: float


class AppUsage(BaseModel):
    app: str
    active_hours: float
    idle_hours: float
    steps: int
    share: float


class HeatCell(BaseModel):
    weekday: int
    hour: int
    active_hours: float


class MapNode(BaseModel):
    id: str
    label: str
    app: str
    count: int
    cases: int
    median_seconds: float
    total_hours: float
    kind: Literal["start", "end", "activity"] = "activity"


class MapEdge(BaseModel):
    source: str
    target: str
    count: int
    cases: int
    dependency: float
    median_wait_seconds: float
    p90_wait_seconds: float


class ProcessMap(BaseModel):
    """Everything the miner trusts; the dashboard's sliders and the BPMN export simplify it further."""

    nodes: list[MapNode]
    edges: list[MapEdge]
    cases: int
    activities_total: int


class Variant(BaseModel):
    id: int
    steps: list[str]
    cases: int
    share: float
    cumulative_share: float
    median_minutes: float
    distance_from_main: float


class Deviation(BaseModel):
    kind: Literal["skipped", "inserted", "replaced"]
    activity: str
    cases: int
    share: float


class VariantAnalysis(BaseModel):
    total_variants: int
    main_path: list[str]
    main_path_share: float
    top5_coverage: float
    variants: list[Variant]
    deviations: list[Deviation]


class Bottleneck(BaseModel):
    kind: Literal["step", "handover"]
    activity: str
    next_activity: str | None = None
    score: float
    severity: Severity
    hours_lost: float
    median_seconds: float
    p90_seconds: float
    occurrences: int
    cases: int
    signals: list[Signal]
    evidence: list[str]


class ReworkLoop(BaseModel):
    pattern: list[str]
    occurrences: int
    cases: int
    share_of_cases: float
    hours: float


class AppSwitch(BaseModel):
    from_app: str
    to_app: str
    switches: int
    ping_pongs: int


class ContextSwitching(BaseModel):
    switches: int
    switches_per_hour: float
    ping_pong_share: float
    pairs: list[AppSwitch]


class ClipboardFlow(BaseModel):
    source_app: str
    target_app: str
    source_step: str
    target_step: str
    transfers: int
    users: int


class AutomationCandidate(BaseModel):
    activity: str
    app: str
    approach: str
    score: float
    hours_per_week: float
    saving_hours_per_week: float
    automation_rate: float
    executions_per_week: float
    signals: list[Signal]
    rationale: list[str]


class Routine(BaseModel):
    steps: list[str]
    occurrences: int
    cases: int
    median_seconds: float
    hours: float


class Person(BaseModel):
    user: str
    alias: str
    cases: int
    steps: int
    active_hours: float
    idle_share: float
    median_case_minutes: float
    speed_index: float | None = Field(description="Above 1 means faster than the team on the same activities; None with too little shared work")
    rework_rate: float
    switches_per_hour: float
    clipboard_per_hour: float
    top_apps: list[str]


class TimelineSegment(BaseModel):
    app: str
    activity: str
    start: str
    end: str
    idle: bool


class PersonDay(BaseModel):
    alias: str
    date: str
    segments: list[TimelineSegment]


class AnomalousCase(BaseModel):
    case_id: str
    user: str
    start: str
    minutes: float
    steps: int
    score: float
    reasons: list[str]


class Finding(BaseModel):
    tone: Literal["warning", "opportunity", "info"]
    title: str
    detail: str
    tab: str


class Analysis(BaseModel):
    id: str
    name: str
    synthetic: bool = False
    quality: DataQuality
    overview: Overview
    findings: list[Finding]
    apps: list[AppUsage]
    heatmap: list[HeatCell]
    process_map: ProcessMap
    variants: VariantAnalysis
    bottlenecks: list[Bottleneck]
    rework: list[ReworkLoop]
    switching: ContextSwitching
    clipboard: list[ClipboardFlow]
    automation: list[AutomationCandidate]
    routines: list[Routine]
    people: list[Person]
    timelines: list[PersonDay]
    anomalies: list[AnomalousCase]
