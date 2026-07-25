"""How each person works, compared fairly.

Comparing raw totals punishes people who simply get the harder cases. The
speed index compares like with like instead: for every activity, a person's
median duration is set against the team median for that activity, and the
ratios are averaged weighted by how often the person does each activity.
"""

import numpy as np
import pandas as pd

from worktrace.mining.switching import mark_switches
from worktrace.schemas import Person, PersonDay, TimelineSegment

MIN_SHARED_EXECUTIONS = 3
MIN_COMPARED_EXECUTIONS = 20  # below this a speed index is noise
MAX_SEGMENTS = 400


def aliases(steps: pd.DataFrame) -> dict[str, str]:
    """Anonymised exports use UUIDs as user names; show them as User 1..n by active time."""
    order = steps.groupby("user")["active_s"].sum().sort_values(ascending=False).index
    return {user: f"User {number}" for number, user in enumerate(order, start=1)}


def analyse_people(steps: pd.DataFrame, flow: pd.DataFrame, transfers: pd.DataFrame) -> list[Person]:
    names = aliases(steps)
    marked = mark_switches(steps)
    speed = _speed_index(flow)
    rework = _rework_rate(flow)
    case_minutes = _case_minutes(flow)
    clipboard_ops = steps.groupby("user")[["copies", "pastes", "cuts"]].sum().sum(axis=1)

    people = []
    for user, own in marked.groupby("user"):
        active_hours = own["active_s"].sum() / 3600
        idle = own["idle_s"].sum()
        top_apps = own.groupby("app")["active_s"].sum().nlargest(3).index.tolist()
        people.append(Person(
            user=user,
            alias=names[user],
            cases=int(flow.loc[flow["user"] == user, "case_id"].nunique()),
            steps=len(own),
            active_hours=round(active_hours, 2),
            idle_share=round(idle / (idle + own["active_s"].sum()), 4) if idle else 0.0,
            median_case_minutes=round(float(case_minutes.get(user, 0)), 1),
            speed_index=round(float(speed[user]), 2) if user in speed else None,
            rework_rate=round(float(rework.get(user, 0)), 4),
            switches_per_hour=round(own["switched"].sum() / active_hours, 1) if active_hours else 0.0,
            clipboard_per_hour=round(clipboard_ops.get(user, 0) / active_hours, 1) if active_hours else 0.0,
            top_apps=top_apps,
        ))
    return sorted(people, key=lambda person: person.alias.zfill(8))


def _speed_index(flow: pd.DataFrame) -> pd.Series:
    durations = flow.assign(duration_s=flow["active_s"] + flow["idle_s"])
    team = durations.groupby("activity")["duration_s"].median()
    own = durations.groupby(["user", "activity"])["duration_s"].agg(["median", "size"]).reset_index()
    own = own[own["size"] >= MIN_SHARED_EXECUTIONS]
    own["ratio"] = own["activity"].map(team) / own["median"].clip(lower=1)
    # Geometric mean, so being 2x faster and 2x slower cancels out.
    own["log_ratio"] = np.log(own["ratio"].clip(lower=0.05, upper=20))
    enough = own.groupby("user")["size"].transform("sum") >= MIN_COMPARED_EXECUTIONS
    own = own[enough]
    weighted = own.groupby("user").apply(lambda rows: np.average(rows["log_ratio"], weights=rows["size"]), include_groups=False)
    return np.exp(weighted)


def _rework_rate(flow: pd.DataFrame) -> pd.Series:
    repeats = flow.groupby(["user", "case_id", "activity"]).size()
    has_repeat = (repeats > 1).groupby(level=["user", "case_id"]).any()
    return has_repeat.groupby(level="user").mean()


def _case_minutes(flow: pd.DataFrame) -> pd.Series:
    # A case belongs to the person who did most of its steps.
    owner = flow.groupby("case_id")["user"].agg(lambda users: users.mode().iat[0])
    span = flow.groupby("case_id").agg(start=("start", "min"), end=("end", "max"))
    minutes = (span["end"] - span["start"]).dt.total_seconds() / 60
    return minutes.groupby(owner).median()


def day_timelines(steps: pd.DataFrame) -> list[PersonDay]:
    """Each person's busiest day as a sequence of application blocks, for the timeline chart."""
    names = aliases(steps)
    steps = steps.assign(date=steps["start"].dt.date)
    days = []
    for user, own in steps.groupby("user"):
        busiest = own.groupby("date")["active_s"].sum().idxmax()
        day = own[own["date"] == busiest].sort_values("start")
        days.append(PersonDay(alias=names[user], date=str(busiest), segments=_merge_segments(day)))
    return sorted(days, key=lambda day: day.alias.zfill(8))


def _merge_segments(day: pd.DataFrame) -> list[TimelineSegment]:
    """Join consecutive steps in the same application into one block."""
    new_block = (day["app"] != day["app"].shift()) | (day["start"] - day["end"].shift() > pd.Timedelta(minutes=2))
    blocks = day.groupby(new_block.cumsum()).agg(
        app=("app", "first"),
        activity=("activity", lambda names: names.mode().iat[0]),
        start=("start", "first"),
        end=("end", "last"),
        active_s=("active_s", "sum"),
        idle_s=("idle_s", "sum"),
    )
    return [
        TimelineSegment(
            app=row.app,
            activity=row.activity,
            start=row.start.isoformat(),
            end=row.end.isoformat(),
            idle=bool(row.idle_s > row.active_s),
        )
        for row in blocks.head(MAX_SEGMENTS).itertuples()
    ]
