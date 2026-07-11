"""Copy-paste flows reconstructed from the interaction log.

Each paste is matched to the latest copy or cut by the same user shortly
before it. When the two happened in different applications, a person carried
data from one system to another by hand: the textbook case for an integration.
"""

import pandas as pd

from worktrace.schemas import ClipboardFlow

MATCH_WINDOW = pd.Timedelta(minutes=10)
MAX_FLOWS = 15


def match_transfers(clipboard: pd.DataFrame) -> pd.DataFrame:
    """One row per paste that has a matching earlier copy: source/target app and step."""
    if clipboard.empty:
        return pd.DataFrame(columns=["user", "source_app", "target_app", "source_step", "target_step"])

    events = clipboard.dropna(subset=["time"]).sort_values("time")
    copies = events[events["kind"].isin(["copy", "cut"])]
    pastes = events[events["kind"] == "paste"]
    matched = pd.merge_asof(
        pastes,
        copies[["user", "time", "app", "activity"]].rename(columns={"app": "source_app", "activity": "source_step"}),
        on="time",
        by="user",
        direction="backward",
        tolerance=MATCH_WINDOW,
    )
    matched = matched.dropna(subset=["source_app"])
    return matched.rename(columns={"app": "target_app", "activity": "target_step"})[
        ["user", "source_app", "target_app", "source_step", "target_step"]
    ]


def clipboard_flows(transfers: pd.DataFrame) -> list[ClipboardFlow]:
    cross_app = transfers[transfers["source_app"] != transfers["target_app"]]
    grouped = cross_app.groupby(["source_app", "target_app", "source_step", "target_step"]).agg(
        transfers=("user", "size"), users=("user", "nunique")
    )
    grouped = grouped.sort_values("transfers", ascending=False).head(MAX_FLOWS)
    return [
        ClipboardFlow(
            source_app=source_app,
            target_app=target_app,
            source_step=source_step,
            target_step=target_step,
            transfers=int(row.transfers),
            users=int(row.users),
        )
        for (source_app, target_app, source_step, target_step), row in grouped.iterrows()
    ]
