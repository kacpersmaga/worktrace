import pandas as pd

from conftest import flow_frame
from worktrace.mining.diagnosis import DiagnosisContext, diagnose_handover, diagnose_step

HOUR = 3600


def context_for(flow: pd.DataFrame, transfers: pd.DataFrame | None = None) -> DiagnosisContext:
    steps = flow.assign(ping_pong=False, switched=False, from_app=None, session_id=flow["case_id"])
    empty = pd.DataFrame(columns=["user", "source_app", "target_app", "source_step", "target_step"])
    return DiagnosisContext(flow=flow, steps=steps, transfers=transfers if transfers is not None else empty,
                            rework=[], aliases={"u1": "User 1"}, periods=1, period="week", cases_are_sessions=False)


def test_slow_runs_made_of_pauses_are_called_pauses_with_examples():
    cases = {f"C{index}": [("Check order", 0, 60)] for index in range(30)}
    cases["C0"] = [("Check order", 0, 50 * 60)]  # left open for 50 minutes
    cases["C1"] = [("Check order", 0, 40 * 60)]
    cases["C2"] = [("Check order", 0, 35 * 60)]
    flow = flow_frame(cases)
    slow = flow["active_s"] > 60
    flow.loc[slow, "no_input_s"] = flow.loc[slow, "active_s"] - 60
    flow.loc[slow, "clicking_s"] = 60.0

    cause = diagnose_step(context_for(flow), "Check order").causes[0]

    assert cause.kind == "pauses"
    assert "waiting for" in cause.action
    assert cause.examples[0].startswith("C0")


def test_values_pasted_from_a_pdf_point_to_document_extraction():
    flow = flow_frame({f"C{index}": [("Enter invoice", 0, 120)] for index in range(10)})
    transfers = pd.DataFrame({
        "user": "u1", "source_app": "Adobe Acrobat Reader", "target_app": "SAP",
        "source_step": "Review PDF", "target_step": "Enter invoice",
    }, index=range(30))

    diagnosis = diagnose_step(context_for(flow, transfers), "Enter invoice")

    assert diagnosis.causes[0].kind == "rekeying"
    assert "document AI" in diagnosis.causes[0].action
    assert diagnosis.data_in[0].share == 3.0


def test_approval_waits_are_explained_as_an_approval_queue():
    cases = {f"C{index}": [("Request approval", 0, 60), ("Post invoice", 60 + 20 * HOUR, 60)] for index in range(10)}
    diagnosis = diagnose_handover(context_for(flow_frame(cases)), "Request approval", "Post invoice")

    kinds = [cause.kind for cause in diagnosis.causes]
    assert kinds[0] == "approval"
    assert "overnight" in kinds  # 20 h later is always the next day
