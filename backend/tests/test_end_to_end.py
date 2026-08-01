"""The synthetic AP team has known behaviour built in; the analysis has to find it."""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from worktrace.analysis import analyse_file
from worktrace.synthetic import Generator, write_export


@pytest.fixture(scope="module")
def ap_export(tmp_path_factory) -> Path:
    generator = Generator(seed=3, days=10)
    path = tmp_path_factory.mktemp("data") / "ap.csv.gz"
    write_export(generator.run(), path, generator.working_days)
    return path


@pytest.fixture(scope="module")
def analysis(ap_export):
    return analyse_file(ap_export, "test", "AP")[0]


def test_cases_are_invoices(analysis):
    assert analysis.quality.case_strategy == "business_id"
    assert analysis.quality.business_ids_rejected  # the generator plants junk IDs
    assert analysis.variants.main_path[:2] == ["Open invoice email", "Review invoice PDF"]


def test_approval_wait_is_a_top_bottleneck(analysis):
    handovers = [(b.activity, b.next_activity) for b in analysis.bottlenecks[:3] if b.kind == "handover"]
    assert ("Request approval", "Post invoice in SAP") in handovers


def test_missing_purchase_order_loop_matches_the_planted_rate(analysis):
    # The generator sends 18% of the 97% non-duplicate invoices back to the vendor: about 17.5% of cases.
    loop = next(loop for loop in analysis.rework if loop.pattern == ["Check purchase order", "Email vendor about PO", "Check purchase order"])
    assert 0.12 <= loop.share_of_cases <= 0.22


def test_untagged_steps_are_attributed_so_most_invoices_look_complete(analysis):
    assert analysis.quality.steps_with_imputed_id > 0
    skipped_post = next((d.share for d in analysis.variants.deviations
                         if d.kind == "skipped" and d.activity == "Post invoice in SAP"), 0)
    assert skipped_post < 0.2


def test_pdf_to_sap_copy_paste_is_found(analysis):
    routes = {(flow.source_app, flow.target_app) for flow in analysis.clipboard}
    assert ("Adobe Acrobat Reader", "SAP GUI") in routes


def test_slow_clerk_has_the_lowest_speed_index(analysis):
    slowest = min((person for person in analysis.people if person.speed_index), key=lambda person: person.speed_index)
    assert slowest.speed_index < 0.8


def test_api_runs_an_upload_end_to_end(ap_export, tmp_path, monkeypatch):
    monkeypatch.setenv("WORKTRACE_WORK", str(tmp_path))
    from importlib import reload

    import worktrace.api.app as api
    reload(api)
    client = TestClient(api.app)

    with ap_export.open("rb") as handle:
        job = client.post("/api/analyses", files={"file": ("ap.csv.gz", handle)}).json()
    for _ in range(100):
        status = client.get(f"/api/analyses/{job['id']}/status").json()
        if status["status"] != "running":
            break
        time.sleep(0.2)

    assert status["status"] == "done", status.get("error")
    assert client.get(f"/api/analyses/{job['id']}").json()["overview"]["users"] == 9
    assert client.get(f"/api/analyses/{job['id']}/bpmn").text.startswith("<?xml")
    explained = client.post(f"/api/analyses/{job['id']}/explain", json={"kind": "bottleneck", "index": 0}).json()
    assert explained["text"]
