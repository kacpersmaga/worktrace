"""Shared helpers for turning raw measurements into comparable, explainable scores."""

from collections.abc import Callable

import pandas as pd

from worktrace.schemas import Severity, Signal


def percentile_ranks(values: pd.Series) -> pd.Series:
    """Rank each value against the others: 0 for the lowest, 1 for the highest, ties share a rank."""
    if len(values) <= 1:
        return pd.Series(1.0, index=values.index)
    return values.rank(method="average", pct=True).sub(1 / len(values)).div(1 - 1 / len(values)).clip(0, 1)


def weighted_score(ranks: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    """0-100 score: a weighted average of percentile ranks."""
    total = sum(weights.values())
    return sum(ranks[key] * weight for key, weight in weights.items()) / total * 100


def severity(score: float) -> Severity:
    if score >= 80:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


Formatter = Callable[[float], str]


def make_signals(row: pd.Series, ranks: pd.Series, labels: dict[str, str], formats: dict[str, Formatter]) -> list[Signal]:
    return [
        Signal(
            key=key,
            label=label,
            value=round(float(row[key]), 4),
            display=formats[key](float(row[key])),
            percentile=round(float(ranks[key]), 3),
        )
        for key, label in labels.items()
    ]


def human_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f} s"
    if seconds < 3600:
        return f"{seconds / 60:.1f} min"
    if seconds < 86400:
        return f"{seconds / 3600:.1f} h"
    return f"{seconds / 86400:.1f} days"


def hours(value: float) -> str:
    return f"{value:.1f} h"


def percent(value: float) -> str:
    return f"{value:.0%}"


def times(value: float) -> str:
    return f"{value:.1f}x"


def decimal(value: float) -> str:
    return f"{value:.2f}"
