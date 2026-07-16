import gzip
from datetime import timedelta

import pandas as pd

from conftest import T0, kyp_row, step_rows, write_kyp
from worktrace.ingest import load_event_log
from worktrace.ingest.business_ids import clean_business_ids, id_shape, impute_business_ids
from worktrace.ingest.sessions import assign_sessions


def test_counters_are_counted_once_per_step_not_once_per_row(tmp_csv):
    rows = step_rows("u1", "Enter invoice", "SAP", T0, 60, ["activity-change", "mouse", "paste", "paste"], pastes=2, clicks=1)
    log = load_event_log(write_kyp(tmp_csv(), rows))

    assert len(log.steps) == 1
    assert log.steps["pastes"].sum() == 2  # summing the repeated column over 4 rows would give 8
    assert log.steps["clicks"].sum() == 1
    assert log.quality.rows_per_step == 4


def test_footer_lines_are_not_users_and_become_metadata(tmp_csv):
    log = load_event_log(write_kyp(tmp_csv(), step_rows("u1", "Read mail", "Outlook", T0, 30, ["activity-change"])))

    assert set(log.steps["user"]) == {"u1"}
    assert log.quality.rows_dropped["footer lines"] == 2
    assert log.quality.export_metadata["Time zone"] == "Europe/Warsaw"


def test_gzip_and_windows_1250_exports_are_read(tmp_csv):
    rows = step_rows("u1", "Księgowanie faktury", "SAP", T0, 30, ["activity-change"])
    plain = write_kyp(tmp_csv("plain.csv"), rows, encoding="cp1250")
    zipped = tmp_csv("export.csv.gz")
    zipped.write_bytes(gzip.compress(plain.read_bytes()))

    assert load_event_log(plain).steps["activity"].iat[0] == "Księgowanie faktury"
    assert load_event_log(zipped).steps["activity"].iat[0] == "Księgowanie faktury"


def test_rows_without_timestamp_are_dropped_and_reported(tmp_csv):
    good = step_rows("u1", "Read mail", "Outlook", T0, 30, ["activity-change"])
    broken = kyp_row("u1", "Read mail", "Outlook", T0, T0, "mouse", T0) | {"Process step start": "not a date"}
    log = load_event_log(write_kyp(tmp_csv(), good + [broken]))

    assert log.quality.rows_dropped["no timestamp"] == 1


def test_interaction_types_are_normalised_across_exporter_versions(tmp_csv):
    rows = step_rows("u1", "Fill form", "Chrome", T0, 30, ["Click", "Text entry", "Paste"])
    for row in rows:
        row["Clicks No."] = row["Text entries No."] = row["Paste No."] = ""  # older export without counters
    log = load_event_log(write_kyp(tmp_csv(), rows))

    step = log.steps.iloc[0]
    assert (step["clicks"], step["keys"], step["pastes"]) == (1, 1, 1)
    assert list(log.clipboard["kind"]) == ["paste"]


def test_id_shape_voting_rejects_noise():
    raw = pd.Series(["INV-00481", "INV-00482", "INV-00483", "kypidbuser", "2026", "NOT_FOUND", ""])
    cleaned, rejected = clean_business_ids(raw)

    assert id_shape("INV-00481") == "AAA-99999"
    assert cleaned.dropna().tolist() == ["INV-00481", "INV-00482", "INV-00483"]
    assert rejected == ["2026", "kypidbuser"]


def test_imputation_fills_enclosed_steps_and_starts_new_cases_correctly():
    minute = timedelta(minutes=1)
    steps = pd.DataFrame({
        "user": ["u1"] * 6,
        "activity": ["Open email", "Enter invoice", "Update tracker", "Post", "Open email", "Enter invoice"],
        "business_id": ["A-1", None, "A-1", "A-1", None, "B-2"],
    })
    steps["start"] = [T0 + minute * index for index in range(6)]
    steps["end"] = steps["start"] + minute * 0.9

    filled, count = impute_business_ids(steps)

    assert filled.tolist() == ["A-1", "A-1", "A-1", "A-1", "B-2", "B-2"]
    assert count == 2


def test_sessions_split_at_breaks():
    steps = pd.DataFrame({"user": ["u1"] * 3, "idle_s": [0.0, 2400.0, 0.0]})
    steps["start"] = [T0, T0 + timedelta(minutes=5), T0 + timedelta(minutes=50)]
    steps["end"] = steps["start"] + timedelta(minutes=1)

    sessions = assign_sessions(steps)

    assert sessions.iat[0] == sessions.iat[1] != sessions.iat[2]


def test_steps_without_usable_ids_become_work_sessions(tmp_csv):
    rows = step_rows("u1", "Code", "IDE", T0, 60, ["activity-change"])
    rows += step_rows("u1", "Code", "IDE", T0 + timedelta(hours=2), 60, ["activity-change"])
    log = load_event_log(write_kyp(tmp_csv(), rows))

    assert log.quality.case_strategy == "work_session"
    assert log.quality.cases == 2


def test_generic_event_logs_are_recognised(tmp_csv):
    path = tmp_csv("log.csv")
    path.write_text(
        "case_id,activity,timestamp,user\n"
        "C1,Submit,2025-01-02 08:00,anna\nC1,Approve,2025-01-02 09:30,jan\nC2,Submit,2025-01-03 10:00,anna\n",
        encoding="utf-8",
    )
    log = load_event_log(path)

    assert log.quality.source_format == "event_log"
    assert log.quality.case_strategy == "case_column"
    assert log.steps.loc[log.steps["activity"] == "Submit", "active_s"].max() == 5400
