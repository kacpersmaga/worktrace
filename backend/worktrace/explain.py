"""Plain-language explanations of a single result.

With GEMINI_API_KEY set, Gemini writes the explanation from the measured
numbers only (they are passed in, and the prompt forbids inventing others).
Without a key the explanation is assembled from the same evidence, so the
feature works offline and in tests.
"""

import json
import os

from pydantic import BaseModel

from worktrace.schemas import Analysis

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
PROMPT = """You explain process-mining results to an operations manager who is not a data analyst.
Use only the numbers in the JSON below; do not invent figures. Write 3 short paragraphs:
what the result means, the most likely cause in this kind of process, and one concrete next step.
Plain English, no headings, no bullet points, under 140 words.

Process: {process}
Result type: {kind}
Result: {payload}
"""


class Explanation(BaseModel):
    text: str
    source: str


def explain(analysis: Analysis, kind: str, index: int) -> Explanation:
    item = _pick(analysis, kind, index)
    payload = item.model_dump_json(exclude={"signals"}) if isinstance(item, BaseModel) else json.dumps(item)
    if os.environ.get("GEMINI_API_KEY"):
        return Explanation(text=_ask_gemini(analysis.name, kind, payload), source="gemini")
    return Explanation(text=_from_evidence(item), source="rules")


def _pick(analysis: Analysis, kind: str, index: int) -> BaseModel:
    collections = {
        "bottleneck": analysis.bottlenecks,
        "automation": analysis.automation,
        "finding": analysis.findings,
        "anomaly": analysis.anomalies,
    }
    if kind not in collections:
        raise KeyError(f"Unknown result type: {kind}")
    return collections[kind][index]


def _ask_gemini(process: str, kind: str, payload: str) -> str:
    from google import genai

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(model=MODEL, contents=PROMPT.format(process=process, kind=kind, payload=payload))
    return (response.text or "").strip()


def _from_evidence(item: BaseModel) -> str:
    lines = getattr(item, "evidence", None) or getattr(item, "rationale", None) or getattr(item, "reasons", None)
    if lines:
        return " ".join(lines)
    return getattr(item, "detail", "")
