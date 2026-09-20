"""Local JSON trade journal storage for the Streamlit UI."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent
JOURNAL_PATH = PROJECT_ROOT / "data" / "journal" / "trades.json"


def load_journal() -> list[dict[str, Any]]:
    if not JOURNAL_PATH.exists():
        return []
    with JOURNAL_PATH.open() as handle:
        return json.load(handle)


def save_journal(entries: list[dict[str, Any]]) -> None:
    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with JOURNAL_PATH.open("w") as handle:
        json.dump(entries, handle, indent=2, default=str)


def add_journal_entry(entries: list[dict[str, Any]], entry: dict[str, Any]) -> list[dict[str, Any]]:
    payload = dict(entry)
    payload.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
    updated = [payload, *entries]
    save_journal(updated)
    return updated
