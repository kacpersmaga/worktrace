"""Run every analysis on one event log and assemble the result the dashboard shows."""

from pathlib import Path

import pandas as pd

from worktrace.findings import headline_findings
from worktrace.ingest import EventLog, load_event_log
from worktrace.mining.anomalies import find_anomalies
from worktrace.mining.automation import automation_candidates
from worktrace.mining.bottlenecks import detect_bottlenecks
from worktrace.mining.clipboard import clipboard_flows, match_transfers
from worktrace.mining.diagnosis import DiagnosisContext, automation_blueprint, diagnose_handover, diagnose_step
from worktrace.mining.people import aliases, analyse_people, day_timelines
from worktrace.mining.process_map import build_process_map
from worktrace.mining.rework import find_rework_loops
from worktrace.mining.routines import find_routines
from worktrace.mining.switching import analyse_switching, mark_switches
from worktrace.mining.transitions import collapse_repeats
from worktrace.mining.variants import analyse_variants
from worktrace.mining.window import complete_cases
from worktrace.schemas import Analysis, AppUsage, HeatCell, Overview

MAX_APPS = 12


def analyse_file(path: str | Path, analysis_id: str, name: str, synthetic: bool = False) -> tuple[Analysis, pd.DataFrame]:
    """Returns the analysis and the flow table used for BPMN discovery (kept by the caller)."""
    log = load_event_log(path)
    return analyse(log, analysis_id, name, synthetic)


def analyse(log: EventLog, analysis_id: str, name: str, synthetic: bool = False) -> tuple[Analysis, pd.DataFrame]:
    steps = log.steps
    flow = collapse_repeats(log.case_steps)
    transfers = match_transfers(log.clipboard)
    weeks = max(_active_days(steps) / 5, 1 / 5)
    sessions = log.quality.case_strategy == "work_session"
    # Sessions are bounded by breaks, never by the export window; real cases can be cut off at both ends.
    complete, cut_off = (flow, 0) if sessions else complete_cases(flow)
    log.quality.cases_cut_off = cut_off

    overview = _overview(log, flow, complete, transfers)
    switching = analyse_switching(steps)
    overview.app_switches_per_hour = switching.switches_per_hour

    analysis = Analysis(
        id=analysis_id,
        name=name,
        synthetic=synthetic,
        quality=log.quality,
        overview=overview,
        findings=[],
        apps=_app_usage(steps),
        heatmap=_heatmap(steps),
        process_map=build_process_map(complete),
        variants=analyse_variants(complete),
        bottlenecks=detect_bottlenecks(flow, cases_are_sessions=sessions),
        rework=find_rework_loops(flow),
        switching=switching,
        clipboard=clipboard_flows(transfers),
        automation=automation_candidates(flow, transfers, weeks),
        routines=find_routines(flow),
        people=analyse_people(steps, flow, transfers),
        timelines=day_timelines(steps),
        anomalies=find_anomalies(complete, steps),
    )
    _diagnose(analysis, DiagnosisContext(
        flow=flow, steps=mark_switches(steps), transfers=transfers, rework=analysis.rework,
        aliases=aliases(steps), cases_are_sessions=sessions, **_period(steps),
    ))
    analysis.period = _period(steps)["period"]
    analysis.findings = headline_findings(analysis)
    return analysis, flow


def _diagnose(analysis: Analysis, context: DiagnosisContext) -> None:
    """Attach the why and the what-to-do to every bottleneck and automation candidate."""
    for bottleneck in analysis.bottlenecks:
        if bottleneck.kind == "handover":
            bottleneck.diagnosis = diagnose_handover(context, bottleneck.activity, bottleneck.next_activity)
        else:
            bottleneck.diagnosis = diagnose_step(context, bottleneck.activity)
    for candidate in analysis.automation:
        candidate.diagnosis = diagnose_step(context, candidate.activity)
        candidate.blueprint = automation_blueprint(candidate.diagnosis, candidate.activity, candidate.app)


def _period(steps: pd.DataFrame) -> dict:
    """Short exports are described per day; a week or more per week."""
    days = _active_days(steps)
    return {"periods": days, "period": "day"} if days < 5 else {"periods": days / 5, "period": "week"}


def _active_days(steps: pd.DataFrame) -> int:
    return int(steps["start"].dt.date.nunique())


def _overview(log: EventLog, flow: pd.DataFrame, complete: pd.DataFrame, transfers: pd.DataFrame) -> Overview:
    steps = log.steps
    span = complete.groupby("case_id").agg(start=("start", "min"), end=("end", "max"))
    case_minutes = (span["end"] - span["start"]).dt.total_seconds() / 60
    active, idle = steps["active_s"].sum() / 3600, steps["idle_s"].sum() / 3600
    return Overview(
        users=int(steps["user"].nunique()),
        cases=int(flow["case_id"].nunique()),
        steps=len(steps),
        activities=int(steps["activity"].nunique()),
        applications=int(steps["app"].nunique()),
        start=steps["start"].min().isoformat(),
        end=steps["end"].max().isoformat(),
        active_days=_active_days(steps),
        tracked_hours=round(active + idle, 2),
        active_hours=round(active, 2),
        idle_hours=round(idle, 2),
        median_case_minutes=round(float(case_minutes.median()), 1),
        p90_case_minutes=round(float(case_minutes.quantile(0.9)), 1),
        copy_paste_operations=int(steps[["copies", "pastes", "cuts"]].sum().sum()),
        cross_app_transfers=int((transfers["source_app"] != transfers["target_app"]).sum()),
        app_switches_per_hour=0.0,
    )


def _app_usage(steps: pd.DataFrame) -> list[AppUsage]:
    usage = steps.groupby("app").agg(active_s=("active_s", "sum"), idle_s=("idle_s", "sum"), steps=("app", "size"))
    total = (usage["active_s"] + usage["idle_s"]).sum()
    usage = usage.assign(total=usage["active_s"] + usage["idle_s"]).sort_values("total", ascending=False)
    return [
        AppUsage(
            app=app,
            active_hours=round(row.active_s / 3600, 2),
            idle_hours=round(row.idle_s / 3600, 2),
            steps=int(row.steps),
            share=round(row.total / total, 4) if total else 0.0,
        )
        for app, row in usage.head(MAX_APPS).iterrows()
    ]


def _heatmap(steps: pd.DataFrame) -> list[HeatCell]:
    hours = steps.groupby([steps["start"].dt.weekday, steps["start"].dt.hour])["active_s"].sum() / 3600
    return [HeatCell(weekday=int(day), hour=int(hour), active_hours=round(value, 3)) for (day, hour), value in hours.items()]
