"""Analysis jobs: run in a background thread, results cached on disk as JSON."""

import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from worktrace.analysis import analyse_file
from worktrace.mining.bpmn import to_bpmn
from worktrace.schemas import Analysis

Status = Literal["running", "done", "failed"]


@dataclass
class Job:
    id: str
    name: str
    created: str
    status: Status = "running"
    error: str | None = None
    analysis: Analysis | None = field(default=None, repr=False)


class JobStore:
    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.folder.mkdir(parents=True, exist_ok=True)
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=2)
        self._load_cached()

    def submit(self, source: Path, name: str, synthetic: bool = False, job_id: str | None = None) -> Job:
        job_id = job_id or uuid.uuid4().hex[:10]
        with self.lock:
            existing = self.jobs.get(job_id)
            if existing and existing.status != "failed":
                return existing
            job = Job(id=job_id, name=name, created=datetime.now(timezone.utc).isoformat())
            self.jobs[job_id] = job
        self.pool.submit(self._run, job, source, synthetic)
        return job

    def get(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def recent(self) -> list[Job]:
        return sorted(self.jobs.values(), key=lambda job: job.created, reverse=True)

    def bpmn(self, job: Job) -> str:
        return to_bpmn(job.analysis.process_map, job.name)

    def _run(self, job: Job, source: Path, synthetic: bool) -> None:
        try:
            analysis, _ = analyse_file(source, job.id, job.name, synthetic)
        except Exception as error:  # surfaced to the user as the job's error message
            job.status, job.error = "failed", str(error)
            return
        job.analysis, job.status = analysis, "done"
        payload = {"id": job.id, "name": job.name, "created": job.created, "analysis": analysis.model_dump(mode="json")}
        (self.folder / f"{job.id}.json").write_text(json.dumps(payload), encoding="utf-8")

    def _load_cached(self) -> None:
        for path in self.folder.glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                analysis = Analysis.model_validate(payload["analysis"])
            except (ValueError, KeyError):
                path.unlink(missing_ok=True)  # written by an older version; it will be recomputed
                continue
            self.jobs[payload["id"]] = Job(payload["id"], payload["name"], payload["created"], "done", None, analysis)
