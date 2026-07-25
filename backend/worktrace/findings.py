"""The four or five sentences a manager reads first, written from the computed results."""

from worktrace.mining.scoring import human_duration
from worktrace.schemas import Analysis, Finding


def headline_findings(analysis: Analysis) -> list[Finding]:
    findings: list[Finding] = []
    overview = analysis.overview

    if analysis.bottlenecks:
        top = analysis.bottlenecks[0]
        if top.kind == "handover":
            findings.append(Finding(
                tone="warning",
                title=f"Cases stall between “{top.activity}” and “{top.next_activity}”",
                detail=f"A typical case waits {human_duration(top.median_seconds)} there; "
                       f"{top.cases:,} cases waited there, {top.hours_lost / 24:,.0f} days in total.",
                tab="bottlenecks",
            ))
        else:
            share = top.hours_lost / overview.tracked_hours if overview.tracked_hours else 0
            findings.append(Finding(
                tone="warning",
                title=f"“{top.activity}” is the main bottleneck",
                detail=f"{top.hours_lost:.1f} h ({share:.0%} of tracked time). {top.evidence[-1]}",
                tab="bottlenecks",
            ))

    if analysis.automation:
        saving = sum(candidate.saving_hours_per_week for candidate in analysis.automation[:3])
        best = analysis.automation[0]
        findings.append(Finding(
            tone="opportunity",
            title=f"About {saving:.0f} h a week could be automated",
            detail=f"Top three candidates; the best is “{best.activity}” ({best.approach.lower()}).",
            tab="automation",
        ))

    if overview.cross_app_transfers:
        flow = analysis.clipboard[0] if analysis.clipboard else None
        route = f" Most go from {flow.source_app} to {flow.target_app}." if flow else ""
        findings.append(Finding(
            tone="opportunity",
            title=f"{overview.cross_app_transfers:,} values carried between apps by hand",
            detail=f"Pastes matched to a copy in another application.{route}",
            tab="automation",
        ))

    if analysis.rework and analysis.quality.case_strategy != "work_session":
        loop = max(analysis.rework, key=lambda item: item.share_of_cases)
        if loop.share_of_cases >= 0.05:
            findings.append(Finding(
                tone="warning",
                title=f"{loop.share_of_cases:.0%} of cases go back to “{loop.pattern[0]}”",
                detail=" → ".join(loop.pattern) + f", {loop.hours:.1f} h of rework.",
                tab="variants",
            ))

    if analysis.switching.switches_per_hour:
        findings.append(Finding(
            tone="info",
            title=f"{analysis.switching.switches_per_hour:.0f} application switches per working hour",
            detail=f"{analysis.switching.ping_pong_share:.0%} of them are quick back-and-forth between two apps.",
            tab="people",
        ))
    return findings[:5]
