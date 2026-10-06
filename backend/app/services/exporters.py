"""
Render security events to CSV / JSON / PDF (used by event export and reports).
All functions are synchronous and CPU-bound — call them via asyncio.to_thread.
"""

import csv
import io
import json
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Sequence

from app.models.security_event import SecurityEvent
from app.services.verdict import ABNORMAL, guesses_text
from app.utils.timeutil import to_iso_z

COMPUTED = {
    "verdict": lambda e: ABNORMAL,
    "attack_guesses": lambda e: guesses_text(e.attack_guesses) if e.attack_guesses else None,
}
FORMULA_START = ("=", "+", "-", "@", "\t", "\r")

COLUMNS = [
    ("timestamp", "Timestamp (UTC)"),
    ("source_ip", "Source IP"),
    ("source_port", "Src Port"),
    ("destination_ip", "Destination IP"),
    ("destination_port", "Dst Port"),
    ("protocol", "Protocol"),
    ("anomaly_score", "Score"),
    ("severity", "Severity"),
    ("verdict", "Verdict"),
    ("attack_type", "Possible Attack"),
    ("confidence", "Confidence"),
    ("attack_guesses", "Model Guesses"),
    ("mode", "Mode"),
    ("state", "State"),
    ("action_taken", "Action"),
    ("detection_reason", "Reason"),
]


def event_row(event: SecurityEvent) -> Dict[str, object]:
    def val(attr: str):
        if attr in COMPUTED:
            return COMPUTED[attr](event)
        value = getattr(event, attr)
        if isinstance(value, datetime):
            return to_iso_z(value)
        return getattr(value, "value", value)

    return {attr: val(attr) for attr, _ in COLUMNS} | {"id": str(event.id)}


def _cell(value) -> object:
    """CSV cell; text that a spreadsheet would run as a formula (=, +, -, @) is quoted with '
    so a crafted value can never execute when the export is opened in Excel."""
    if value is None:
        return ""
    if isinstance(value, str) and value.startswith(FORMULA_START):
        return "'" + value
    return value


def to_csv(events: Sequence[SecurityEvent]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["ID"] + [label for _, label in COLUMNS])
    for event in events:
        row = event_row(event)
        writer.writerow([row["id"]] + [_cell(row[a]) for a, _ in COLUMNS])
    return buffer.getvalue().encode("utf-8-sig")  # BOM so Excel opens UTF-8 correctly


def breakdown(events: Sequence[SecurityEvent]) -> Dict[str, Dict[str, int]]:
    return {
        "severity": dict(Counter(e.severity.value for e in events)),
        "state": dict(Counter(e.state.value for e in events)),
        "possible attack": dict(Counter(e.attack_type or "Unknown" for e in events)),
        "action": dict(Counter(e.action_taken.value for e in events)),
    }


def to_json(events: Sequence[SecurityEvent], meta: Optional[dict] = None, include_breakdown: bool = True) -> bytes:
    doc: dict = {"meta": meta or {}, "total": len(events)}
    if include_breakdown:
        doc["breakdown"] = breakdown(events)
    doc["events"] = [event_row(e) for e in events]
    return json.dumps(doc, indent=2, default=str).encode("utf-8")


def to_pdf(events: Sequence[SecurityEvent], title: str, subtitle: str = "",
           include_breakdown: bool = True) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm, title=title)
    styles = getSampleStyleSheet()
    story: List = [Paragraph(title, styles["Title"])]
    if subtitle:
        story.append(Paragraph(subtitle, styles["Normal"]))
    story.append(Paragraph(f"Total events: {len(events)}", styles["Normal"]))
    story.append(Spacer(1, 6 * mm))

    grid = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#94a3b8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ])

    if include_breakdown and events:
        for name, counts in breakdown(events).items():
            rows = [[name.capitalize(), "Count"]] + [[k, str(v)] for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]
            table = Table(rows, hAlign="LEFT")
            table.setStyle(grid)
            story += [table, Spacer(1, 4 * mm)]

    cols = ["timestamp", "source_ip", "destination_ip", "destination_port", "protocol",
            "anomaly_score", "severity", "verdict", "attack_type", "state", "action_taken"]
    labels = dict(COLUMNS)
    rows = [[labels[c] for c in cols]]
    for event in events:
        row = event_row(event)
        rows.append([
            f"{row[c]:.3f}" if c == "anomaly_score" and row[c] is not None else ("" if row[c] is None else str(row[c]))
            for c in cols
        ])
    table = Table(rows, repeatRows=1)
    table.setStyle(grid)
    story.append(table)
    doc.build(story)
    return buffer.getvalue()
