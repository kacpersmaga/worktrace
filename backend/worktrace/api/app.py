"""HTTP API for the dashboard."""

import os
import shutil
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from worktrace.api.jobs import Job, JobStore
from worktrace.explain import Explanation, explain

ROOT = Path(__file__).resolve().parents[3]
DATA = Path(os.environ.get("WORKTRACE_DATA", ROOT / "data"))
WORK = Path(os.environ.get("WORKTRACE_WORK", ROOT / "backend" / ".worktrace"))
ALLOWED_SUFFIXES = (".csv", ".csv.gz", ".gz")
MAX_UPLOAD_BYTES = 400 * 1024 * 1024


class Demo(BaseModel):
    key: str
    name: str
    description: str
    synthetic: bool
    file: str


DEMOS = [
    Demo(
        key="accounts-payable",
        name="Accounts payable team",
        description="Three weeks of nine clerks processing supplier invoices across Outlook, Acrobat, SAP and Excel.",
        synthetic=True,
        file="demo/accounts_payable.csv.gz",
    ),
    Demo(
        key="kyp-pilot-day",
        name="KYP.ai pilot, one day",
        description="A real, anonymised Activity Sequence Export: eight people of a software team on 1 March 2026.",
        synthetic=False,
        file="demo/kyp_pilot_day.csv.gz",
    ),
]

app = FastAPI(title="WorkTrace API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("WORKTRACE_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
jobs = JobStore(WORK / "results")


class JobView(BaseModel):
    id: str
    name: str
    created: str
    status: str
    error: str | None = None


class ExplainRequest(BaseModel):
    kind: str
    index: int


def _view(job: Job) -> JobView:
    return JobView(id=job.id, name=job.name, created=job.created, status=job.status, error=job.error)


def _job_or_404(job_id: str) -> Job:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "Analysis not found")
    return job


def _finished(job_id: str) -> Job:
    job = _job_or_404(job_id)
    if job.status != "done":
        raise HTTPException(409, f"Analysis is {job.status}")
    return job


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/demos")
def list_demos() -> list[Demo]:
    return [demo for demo in DEMOS if (DATA / demo.file).exists()]


@app.post("/api/demos/{key}")
def open_demo(key: str) -> JobView:
    demo = next((demo for demo in DEMOS if demo.key == key), None)
    if demo is None or not (DATA / demo.file).exists():
        raise HTTPException(404, "Unknown demo dataset")
    return _view(jobs.submit(DATA / demo.file, demo.name, demo.synthetic, job_id=f"demo-{demo.key}"))


@app.post("/api/analyses")
def upload(file: UploadFile) -> JobView:
    filename = file.filename or "upload.csv"
    if not filename.lower().endswith(ALLOWED_SUFFIXES):
        raise HTTPException(400, "Upload a .csv or .csv.gz file")
    uploads = WORK / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    target = uploads / f"{os.urandom(6).hex()}{''.join(Path(filename).suffixes[-2:]) or '.csv'}"
    with target.open("wb") as handle:
        shutil.copyfileobj(file.file, handle, length=1024 * 1024)
    if target.stat().st_size > MAX_UPLOAD_BYTES:
        target.unlink()
        raise HTTPException(413, "File is larger than 400 MB")
    name = Path(filename).name.split(".")[0].removeprefix("Activity Sequence Export - ") or "Upload"
    return _view(jobs.submit(target, name))


@app.get("/api/analyses")
def recent() -> list[JobView]:
    return [_view(job) for job in jobs.recent()]


@app.get("/api/analyses/{job_id}/status")
def status(job_id: str) -> JobView:
    return _view(_job_or_404(job_id))


@app.get("/api/analyses/{job_id}")
def result(job_id: str):
    return _finished(job_id).analysis


@app.get("/api/analyses/{job_id}/bpmn")
def bpmn(job_id: str) -> Response:
    job = _finished(job_id)
    filename = f"{job.name.lower().replace(' ', '-')}.bpmn"
    return Response(
        jobs.bpmn(job),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/analyses/{job_id}/explain")
def explain_result(job_id: str, request: ExplainRequest) -> Explanation:
    job = _finished(job_id)
    try:
        return explain(job.analysis, request.kind, request.index)
    except (KeyError, IndexError) as error:
        raise HTTPException(404, str(error)) from error
