"""A synthetic KYP.ai export of an accounts-payable team, for demos and tests.

The real hackathon dataset cannot be redistributed, and the one public sample
is a single day of a software team. This generator simulates three weeks of
nine AP clerks processing supplier invoices and writes the result in the exact
Activity Sequence Export format, including its quirks: one row per
interaction, step counters repeated on every row, Business IDs that are often
NOT_FOUND or wrong, and the "Applied filters" footer.

Built-in behaviour the analysis should find:
  - approvals wait hours to days in the approval portal (hand-over bottleneck)
  - a missing purchase order sends ~18% of invoices back to the vendor (rework)
  - invoice data is copied from the PDF into SAP and from SAP into Excel
  - clerks differ in speed; one works noticeably slower and switches apps a lot

Usage: python -m worktrace.synthetic --out ../data/demo/accounts_payable.csv.gz
"""

import argparse
import csv
import gzip
import random
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

COLUMNS = [
    "User name", "Host name", "Process step", "Application name", "Original view name", "Activity Status",
    "Process step start", "Process step end", "Activity duration (ms)", "Activity type", "Activity name",
    "Activity start timestamp", "Business ID", "Business ID Source", "Activity content", "Process Name",
    "Process ID", "Unit name", "User UUID", "AI Business ID", "Original Activity name", "Url", "Content",
    "Process Step Total Duration", "Process Step Active Duration", "Process Step Passive Duration",
    "Text entries No.", "Clicks No.", "Activities No.", "Copy No.", "Paste No.", "Cut No.", "Screenshot UUID",
    "Component", "Tab name", "OCR Content", "Parsed Visible Content",
]


@dataclass(frozen=True)
class StepKind:
    """median seconds, clicks, keys, copies, pastes per execution, and the chance the screen shows the invoice ID"""

    name: str
    app: str
    view: str
    seconds: float
    clicks: int
    keys: int
    copies: int = 0
    pastes: int = 0
    id_visible: float = 0.7


STEPS = {step.name: step for step in [
    StepKind("Open invoice email", "Outlook", "Inbox - AP Invoices", 45, 4, 0, id_visible=0.6),
    StepKind("Review invoice PDF", "Adobe Acrobat Reader", "Invoice.pdf", 70, 6, 0, copies=4, id_visible=0.85),
    StepKind("Search vendor in SAP", "SAP GUI", "Display Vendor (XK03)", 55, 7, 3, pastes=1),
    StepKind("Check purchase order", "SAP GUI", "Display Purchase Order (ME23N)", 80, 9, 2, pastes=1),
    StepKind("Check for duplicates", "Excel", "AP tracker.xlsx", 50, 6, 2, pastes=1, id_visible=0.5),
    StepKind("Enter invoice in SAP", "SAP GUI", "Enter Incoming Invoice (MIRO)", 210, 22, 14, copies=1, pastes=4, id_visible=0.9),
    StepKind("Ask buyer about price", "Teams", "Chat", 120, 6, 8, pastes=1, id_visible=0.3),
    StepKind("Correct invoice amount", "SAP GUI", "Change Invoice (MIR4)", 95, 10, 5, id_visible=0.9),
    StepKind("Update AP tracker", "Excel", "AP tracker.xlsx", 75, 8, 4, pastes=3, id_visible=0.6),
    StepKind("Request approval", "Chrome", "Approvals - Invoice workflow", 60, 9, 3, pastes=1),
    StepKind("Post invoice in SAP", "SAP GUI", "Post Invoice (MIRO)", 65, 8, 1),
    StepKind("Email vendor about PO", "Outlook", "RE: Invoice - missing PO", 150, 6, 18, pastes=1, id_visible=0.8),
    StepKind("Reject duplicate invoice", "Outlook", "RE: Duplicate invoice", 90, 5, 10, id_visible=0.8),
    StepKind("Reply to vendor", "Outlook", "RE: Invoice received", 60, 4, 6, id_visible=0.7),
]}
NOISE = [
    StepKind("Read Teams chat", "Teams", "Chat", 50, 3, 2, id_visible=0),
    StepKind("Browse intranet", "Chrome", "Intranet - News", 80, 5, 0, id_visible=0),
    StepKind("Check calendar", "Outlook", "Calendar", 30, 3, 0, id_visible=0),
]
JUNK_IDS = ["ap.clerk", "2026", "MIRO", "PO", "VENDOR-1"]


@dataclass
class Clerk:
    user_name: str
    user_uuid: str
    speed: float
    switchy: bool = False
    skips_tracker: float = 0.1


@dataclass
class Invoice:
    number: str
    path: list[str]
    approval_at: int = 0  # index in path of "Post invoice in SAP"
    waiting_until: datetime | None = None
    position: int = 0


@dataclass
class Generator:
    seed: int = 26
    start: date = date(2026, 5, 4)
    days: int = 15
    rows: list[list[str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)
        self.invoice_counter = 4100
        self.working_days = working_days(self.start, self.days)

    def run(self) -> list[list[str]]:
        clerks = [
            Clerk(str(uuid.UUID(int=self.rng.getrandbits(128))), str(uuid.UUID(int=self.rng.getrandbits(128))),
                  speed=self.rng.uniform(0.8, 1.2))
            for _ in range(9)
        ]
        clerks[2].speed, clerks[2].switchy = 1.55, True
        clerks[5].speed, clerks[5].skips_tracker = 0.75, 0.4
        for clerk in clerks:
            self._simulate_clerk(clerk)
        self.rows.sort(key=lambda row: (row[0], row[11]))
        return self.rows

    # --- process logic -------------------------------------------------

    def _new_invoice(self) -> Invoice:
        self.invoice_counter += self.rng.randint(1, 3)
        path = ["Open invoice email", "Review invoice PDF", "Search vendor in SAP"]
        if self.rng.random() < 0.03:
            return Invoice(f"INV-2026-{self.invoice_counter:05d}", path + ["Check for duplicates", "Reject duplicate invoice"])
        path.append("Check purchase order")
        if self.rng.random() < 0.18:
            path += ["Email vendor about PO", "__wait_vendor__", "Check purchase order"]
        path.append("Enter invoice in SAP")
        if self.rng.random() < 0.12:
            path += ["Ask buyer about price", "Correct invoice amount"]
        path += ["Update AP tracker", "Request approval", "__wait_approval__"]
        if self.rng.random() < 0.05:
            path += ["Correct invoice amount", "Request approval", "__wait_approval__"]
        path.append("Post invoice in SAP")
        if self.rng.random() < 0.35:
            path.append("Reply to vendor")
        return Invoice(f"INV-2026-{self.invoice_counter:05d}", path)

    def _simulate_clerk(self, clerk: Clerk) -> None:
        parked: list[Invoice] = []
        for day in self.working_days:
            now = datetime.combine(day, datetime.min.time()) + timedelta(hours=8, minutes=self.rng.randint(0, 40))
            lunch_done = False
            day_end = now.replace(hour=16, minute=self.rng.randint(15, 50))
            while now < day_end:
                if not lunch_done and now.hour >= 12:
                    now = self._idle_step(clerk, now, minutes=self.rng.randint(25, 40))
                    lunch_done = True
                    continue
                ready = [invoice for invoice in parked if invoice.waiting_until <= now]
                invoice = ready[0] if ready else self._new_invoice()
                if ready:
                    parked.remove(invoice)
                now = self._work_on(clerk, invoice, now)
                if invoice.waiting_until:
                    parked.append(invoice)
                if self.rng.random() < (0.5 if clerk.switchy else 0.25):
                    now = self._step(clerk, self.rng.choice(NOISE), now, invoice_number=None)

    def _work_on(self, clerk: Clerk, invoice: Invoice, now: datetime) -> datetime:
        invoice.waiting_until = None
        while invoice.position < len(invoice.path):
            name = invoice.path[invoice.position]
            invoice.position += 1
            if name == "__wait_approval__":
                invoice.waiting_until = now + timedelta(hours=self.rng.lognormvariate(1.6, 0.8))
                return now
            if name == "__wait_vendor__":
                invoice.waiting_until = now + timedelta(hours=self.rng.lognormvariate(2.8, 0.5))
                return now
            if name == "Update AP tracker" and self.rng.random() < clerk.skips_tracker:
                continue
            now = self._step(clerk, STEPS[name], now, invoice.number, slow=clerk.speed)
            if clerk.switchy and self.rng.random() < 0.3:
                now = self._step(clerk, NOISE[0], now, None)
        return now

    # --- export rows ---------------------------------------------------

    def _step(self, clerk: Clerk, kind: StepKind, start: datetime, invoice_number: str | None, slow: float = 1.0) -> datetime:
        seconds = max(5.0, kind.seconds * slow * self.rng.lognormvariate(0, 0.45))
        idle = seconds * self.rng.uniform(0.2, 0.6) if self.rng.random() < 0.04 else 0.0
        end = start + timedelta(seconds=seconds + idle)
        counts = {name: max(0, round(base * self.rng.uniform(0.6, 1.4))) for name, base in
                  {"clicks": kind.clicks, "keys": kind.keys, "copies": kind.copies, "pastes": kind.pastes}.items()}

        business_id, source = "", "NOT_FOUND"
        if invoice_number and self.rng.random() < kind.id_visible:
            business_id, source = invoice_number, "AI"
        elif self.rng.random() < 0.02:
            business_id, source = self.rng.choice(JUNK_IDS), "AI"

        interactions = (["activity-change"] + ["mouse"] * counts["clicks"] + ["text-entry"] * counts["keys"]
                        + ["copy"] * counts["copies"] + ["paste"] * counts["pastes"] + (["idle"] if idle else []))
        head, tail = interactions[0], interactions[1:]
        self.rng.shuffle(tail)
        # copies happen while reading, pastes while typing: keep them in a believable order
        tail.sort(key=lambda kind_name: {"copy": 0, "paste": 2}.get(kind_name, 1))
        interactions = [head] + tail
        moments = sorted(self.rng.uniform(0, seconds) for _ in interactions[1:])
        times = [start] + [start + timedelta(seconds=moment) for moment in moments]
        total_ms, passive_ms = int((seconds + idle) * 1000), int(idle * 1000)
        for index, (interaction, moment) in enumerate(zip(interactions, times)):
            following = times[index + 1] if index + 1 < len(times) else end
            self.rows.append(self._row(clerk, kind, start, end, interaction, moment, following, business_id, source,
                                       counts, len(interactions), total_ms, passive_ms))
        return end + timedelta(seconds=self.rng.uniform(0, 4))

    def _idle_step(self, clerk: Clerk, start: datetime, minutes: int) -> datetime:
        end = start + timedelta(minutes=minutes)
        kind = StepKind("Use Windows Lock Screen", "LockApp", "Windows Default Lock Screen", 0, 0, 0, id_visible=0)
        total = int((end - start).total_seconds() * 1000)
        self.rows.append(self._row(clerk, kind, start, end, "idle", start, end, "", "NOT_FOUND",
                                   {"clicks": 0, "keys": 0, "copies": 0, "pastes": 0}, 1, total, total))
        return end

    def _row(self, clerk: Clerk, kind: StepKind, start: datetime, end: datetime, interaction: str, moment: datetime,
             following: datetime, business_id: str, source: str, counts: dict[str, int], activities: int,
             total_ms: int, passive_ms: int) -> list[str]:
        def stamp(value: datetime) -> str:
            return value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{value.microsecond // 1000:03d}"

        status = "Passive" if interaction == "idle" else "Active"
        content = "<Anonymized>" if interaction in {"text-entry", "copy", "paste"} else ""
        return [
            clerk.user_name, "", kind.name, kind.app, kind.view, status, stamp(start), stamp(end),
            str(int((following - moment).total_seconds() * 1000)), interaction, "", stamp(moment),
            business_id, source, content, "Accounts Payable", "41", "", clerk.user_uuid, business_id, "", "",
            content, str(total_ms), str(total_ms - passive_ms), str(passive_ms), str(counts["keys"]),
            str(counts["clicks"]), str(activities), str(counts["copies"]), str(counts["pastes"]), "0", "", "", "",
            "", "",
        ]


def working_days(start: date, count: int) -> list[date]:
    days, current = [], start
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def write_export(rows: list[list[str]], path: Path, days: list[date]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, quoting=csv.QUOTE_ALL)
        writer.writerow(COLUMNS)
        writer.writerows(rows)
        for line in ["Applied filters:", "Organization selection : Demo AP Shared Services",
                     f"Time interval: {days[0]} 00:00 to {days[-1]} 23:59", "Time zone: Europe/Warsaw"]:
            writer.writerow([line] + [""] * (len(COLUMNS) - 1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path("../data/demo/accounts_payable.csv.gz"))
    parser.add_argument("--seed", type=int, default=26)
    parser.add_argument("--days", type=int, default=15)
    args = parser.parse_args()
    generator = Generator(seed=args.seed, days=args.days)
    rows = generator.run()
    write_export(rows, args.out, generator.working_days)
    print(f"{len(rows):,} interaction rows -> {args.out}")


if __name__ == "__main__":
    main()
