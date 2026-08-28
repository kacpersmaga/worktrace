"""The four or five sentences a manager reads first, written from the computed results."""

from worktrace.mining.scoring import human_duration
from worktrace.schemas import Analysis, Finding


def headline_findings(analysis: Analysis) -> list[Finding]:
    findings: list[Finding] = []
    overview = analysis.overview

    if analysis.bottlenecks:
        top = analysis.bottlenecks[0]
        cause = top.diagnosis.causes[0] if top.diagnosis and top.diagnosis.causes else None
        where = f"between “{top.activity}” and “{top.next_activity}”" if top.kind == "handover" else f"in “{top.activity}”"
        findings.append(Finding(
            tone="warning",
            title=f"{cause.title} {where}" if cause else f"“{top.activity}” is the main bottleneck",
            detail=f"{cause.evidence} What to do: {cause.action}" if cause else top.evidence[0],
            tab="bottlenecks",
        ))

    if analysis.automation:
        saving = sum(candidate.saving_hours_per_week for candidate in analysis.automation[:3])
        best = analysis.automation[0]
        hands_on = [cause for cause in (best.diagnosis.causes if best.diagnosis else [])
                    if cause.kind in {"rekeying", "copy_out", "typing", "lookups"}]
        how = f"{hands_on[0].evidence} {hands_on[0].action}" if hands_on else " ".join(best.blueprint[:3])
        findings.append(Finding(
            tone="opportunity",
            title=f"About {saving:.0f} h a week could be automated, starting with “{best.activity}”",
            detail=how,
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
