import pandas as pd

from conftest import flow_frame
from worktrace.mining.automation import _predictability
from worktrace.mining.bottlenecks import detect_bottlenecks
from worktrace.mining.bpmn import to_bpmn
from worktrace.mining.clipboard import match_transfers
from worktrace.mining.process_map import build_process_map
from worktrace.mining.rework import find_rework_loops
from worktrace.mining.routines import find_routines
from worktrace.mining.transitions import collapse_repeats, dependency_measure, directly_follows
from worktrace.mining.variants import analyse_variants

HOUR = 3600


def invoices(count: int, approval_wait: int = 6 * HOUR) -> dict:
    """count cases of Receive -> Enter -> Approve with a long wait before Approve."""
    return {
        f"C{index}": [("Receive invoice", 0, 60), ("Enter invoice", 120, 300), ("Approve invoice", 420 + approval_wait, 60)]
        for index in range(count)
    }


def test_back_to_back_repeats_are_merged():
    flow = collapse_repeats(flow_frame({"C1": [("Enter data", 0, 10), ("Enter data", 10, 20), ("Save", 30, 5)]}))
    assert flow["activity"].tolist() == ["Enter data", "Save"]
    assert flow["active_s"].tolist() == [30.0, 5.0]


def test_dependency_measure_trusts_one_way_relations():
    dfg = pd.DataFrame({"activity": ["A", "B", "C"], "next_activity": ["B", "A", "D"], "count": [20, 20, 9]})
    measure = dependency_measure(dfg)
    assert measure.iat[0] == 0  # A and B interleave both ways
    assert measure.iat[2] == 9 / 10


def test_handover_wait_is_found_and_ranked_first():
    flow = flow_frame(invoices(12))
    top = detect_bottlenecks(flow)[0]
    assert top.kind == "handover"
    assert (top.activity, top.next_activity) == ("Enter invoice", "Approve invoice")
    assert top.median_seconds == 6 * HOUR


def test_single_overnight_gap_is_not_a_bottleneck():
    cases = invoices(12, approval_wait=60)
    cases["C0"][2] = ("Approve invoice", 420 + 14 * HOUR, 60)  # one case waited overnight
    found = detect_bottlenecks(flow_frame(cases))
    assert all(bottleneck.kind == "step" for bottleneck in found)


def test_variants_report_typical_deviations():
    cases = invoices(8)
    cases["X1"] = [("Receive invoice", 0, 60), ("Approve invoice", 100, 60)]
    analysis = analyse_variants(flow_frame(cases))
    assert analysis.main_path == ["Receive invoice", "Enter invoice", "Approve invoice"]
    assert analysis.deviations[0].kind == "skipped"
    assert analysis.deviations[0].activity == "Enter invoice"


def test_rework_loops_are_counted_by_pattern():
    loop = [("Check PO", 0, 60), ("Email vendor", 100, 60), ("Check PO", 200, 60), ("Post", 300, 60)]
    flow = flow_frame({"C1": loop, "C2": loop, "C3": [("Check PO", 0, 60), ("Post", 100, 60)]})
    top = find_rework_loops(flow)[0]
    assert top.pattern == ["Check PO", "Email vendor", "Check PO"]
    assert top.cases == 2


def test_routines_keep_whole_sequences_not_fragments():
    path = [("Open", 0, 10), ("Copy", 20, 10), ("Paste", 40, 10), ("Save", 60, 10)]
    routines = find_routines(flow_frame({f"C{index}": path for index in range(5)}))
    assert routines[0].steps == ["Open", "Copy", "Paste", "Save"]
    assert len(routines) == 1


def test_predictability_is_one_for_deterministic_steps():
    flow = flow_frame({
        "C1": [("A", 0, 10), ("B", 20, 10), ("C", 40, 10)],
        "C2": [("A", 0, 10), ("B", 20, 10), ("D", 40, 10)],
    })
    predictability = _predictability(flow)
    assert predictability["A"] == 1.0
    assert predictability["B"] == 0.0


def test_pastes_are_matched_to_the_latest_copy_of_the_same_user():
    t = pd.Timestamp("2026-03-02 09:00")
    clipboard = pd.DataFrame([
        {"user": "u1", "time": t, "app": "Acrobat", "activity": "Read PDF", "kind": "copy"},
        {"user": "u2", "time": t + pd.Timedelta(seconds=5), "app": "Excel", "activity": "Sheet", "kind": "copy"},
        {"user": "u1", "time": t + pd.Timedelta(seconds=30), "app": "SAP", "activity": "Enter invoice", "kind": "paste"},
        {"user": "u1", "time": t + pd.Timedelta(hours=1), "app": "SAP", "activity": "Enter invoice", "kind": "paste"},
    ])
    transfers = match_transfers(clipboard)
    assert transfers[["source_app", "target_app"]].values.tolist() == [["Acrobat", "SAP"]]


def test_process_map_and_bpmn_connect_start_to_end():
    process_map = build_process_map(flow_frame(invoices(10)))
    xml = to_bpmn(process_map, "Invoices")
    assert {node.id for node in process_map.nodes} >= {"__start__", "__end__", "Enter invoice"}
    assert xml.count("<bpmn:userTask") == 3
    assert "sourceRef=\"__start__\"" in xml


def test_directly_follows_measures_hand_over_waits():
    dfg = directly_follows(flow_frame(invoices(4)))
    wait = dfg.set_index(["activity", "next_activity"]).loc[("Receive invoice", "Enter invoice"), "median_wait_s"]
    assert wait == 60
