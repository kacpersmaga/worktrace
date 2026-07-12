"""Unusual cases, found with an Isolation Forest.

Every case is described by a handful of features (duration, steps, rework,
waiting, application switches). The Isolation Forest flags cases that are easy
to separate from the rest; robust z-scores (median and MAD) then name the
features that make each one stand out, so a flagged case comes with a reason.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from worktrace.mining.people import aliases
from worktrace.mining.scoring import human_duration
from worktrace.schemas import AnomalousCase

MIN_CASES = 30
CONTAMINATION = 0.03
MAX_ANOMALIES = 12
EXPLAIN_Z = 2.5
FEATURE_LABELS = {
    "minutes": "lasted {value} ({ratio:.1f}x a typical case)",
    "steps": "had {value:.0f} steps vs a typical {typical:.0f}",
    "repeats": "repeated {value:.0f} steps",
    "wait_share": "spent {value:.0%} of its time waiting between steps",
    "apps": "touched {value:.0f} applications vs a typical {typical:.0f}",
}


def find_anomalies(flow: pd.DataFrame, users: pd.DataFrame) -> list[AnomalousCase]:
    """flow: case-ordered steps with repeats collapsed; users: all steps (for aliases)."""
    features = _case_features(flow)
    if len(features) < MIN_CASES:
        return []

    model = IsolationForest(n_estimators=200, contamination=CONTAMINATION, random_state=7)
    matrix = np.log1p(features[list(FEATURE_LABELS)].to_numpy(dtype=float))
    flagged = model.fit_predict(matrix) == -1
    features["score"] = -model.score_samples(matrix)

    names = aliases(users)
    median = features[list(FEATURE_LABELS)].median()
    mad = (features[list(FEATURE_LABELS)] - median).abs().median().replace(0, np.nan)
    results = []
    for case_id, row in features[flagged].sort_values("score", ascending=False).head(MAX_ANOMALIES).iterrows():
        reasons = _reasons(row, median, mad)
        if not reasons:
            continue
        results.append(AnomalousCase(
            case_id=str(case_id),
            user=names.get(row["user"], row["user"]),
            start=row["start"].isoformat(),
            minutes=round(float(row["minutes"]), 1),
            steps=int(row["steps"]),
            score=round(float(row["score"]), 3),
            reasons=reasons,
        ))
    return results


def _case_features(flow: pd.DataFrame) -> pd.DataFrame:
    by_case = flow.groupby("case_id", sort=False)
    start, end = by_case["start"].min(), by_case["end"].max()
    span_s = (end - start).dt.total_seconds()
    work_s = by_case.apply(lambda case: (case["active_s"] + case["idle_s"]).sum(), include_groups=False)
    return pd.DataFrame({
        "user": by_case["user"].agg(lambda users: users.mode().iat[0]),
        "start": start,
        "minutes": span_s / 60,
        "steps": by_case.size(),
        "repeats": by_case.size() - by_case["activity"].nunique(),
        "wait_share": (1 - work_s / span_s.where(span_s > 0)).clip(0, 1).fillna(0),
        "apps": by_case["app"].nunique(),
    })


def _reasons(row: pd.Series, median: pd.Series, mad: pd.Series) -> list[str]:
    reasons = []
    for feature, template in FEATURE_LABELS.items():
        if pd.isna(mad[feature]):
            continue
        z = 0.6745 * (row[feature] - median[feature]) / mad[feature]
        if z < EXPLAIN_Z:
            continue
        value = human_duration(row[feature] * 60) if feature == "minutes" else row[feature]
        ratio = row[feature] / median[feature] if median[feature] else 0
        reasons.append("The case " + template.format(value=value, typical=median[feature], ratio=ratio) + ".")
    return reasons
