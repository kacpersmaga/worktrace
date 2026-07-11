"""Context switching between applications.

A switch is two consecutive steps of the same user in different applications
within one work session. A ping-pong is A -> B -> A inside two minutes: the
pattern of someone looking a value up in one system to type it into another.
"""

import pandas as pd

from worktrace.schemas import AppSwitch, ContextSwitching

PING_PONG_WINDOW = pd.Timedelta(minutes=2)
MAX_PAIRS = 12


def mark_switches(steps: pd.DataFrame) -> pd.DataFrame:
    """Add switched (bool) and ping_pong (bool) columns to user-ordered steps."""
    steps = steps.sort_values(["user", "start"]).copy()
    by_session = steps.groupby("session_id", sort=False)
    previous_app = by_session["app"].shift()
    steps["from_app"] = previous_app
    steps["switched"] = previous_app.notna() & (previous_app != steps["app"])

    app_two_back = by_session["app"].shift(2)
    end_two_back = by_session["end"].shift(2)
    steps["ping_pong"] = (
        steps["switched"]
        & (app_two_back == steps["app"])
        & (steps["start"] - end_two_back <= PING_PONG_WINDOW)
    )
    return steps


def analyse_switching(steps: pd.DataFrame) -> ContextSwitching:
    marked = mark_switches(steps)
    switches = marked[marked["switched"]]
    active_hours = marked["active_s"].sum() / 3600

    pairs = switches.groupby(["from_app", "app"]).agg(switches=("switched", "size"), ping_pongs=("ping_pong", "sum"))
    pairs = pairs.sort_values("switches", ascending=False).head(MAX_PAIRS)
    return ContextSwitching(
        switches=len(switches),
        switches_per_hour=round(len(switches) / active_hours, 1) if active_hours else 0.0,
        ping_pong_share=round(float(switches["ping_pong"].mean()), 4) if len(switches) else 0.0,
        pairs=[
            AppSwitch(from_app=source, to_app=target, switches=int(row.switches), ping_pongs=int(row.ping_pongs))
            for (source, target), row in pairs.iterrows()
        ],
    )
