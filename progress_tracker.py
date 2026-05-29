"""Atomic JSON helpers for background job state, progress, and briefing files."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).resolve().parent
PROGRESS_FILE = BASE_DIR / "agent_progress.json"
RUN_STATE_FILE = BASE_DIR / "run_state.json"
BRIEFING_FILE = BASE_DIR / "latest_briefing.json"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def atomic_write_json(path: str | Path, payload: Dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False, default=str)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.remove(tmp_name)
        except Exception:
            pass
        raise

def read_json(path: str | Path, default: Optional[Any] = None) -> Any:
    path = Path(path)
    try:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default

def write_progress(
    step: int,
    total_steps: int,
    message: str,
    status: str = "running",
    detail: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "step": step,
        "total_steps": total_steps,
        "message": message,
        "status": status,
        "detail": detail,
        "pct": int((step / total_steps) * 100) if total_steps else 0,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "updated_utc": utc_now_iso(),
    }
    if extra:
        payload.update(extra)
    atomic_write_json(PROGRESS_FILE, payload)
    return payload

def read_progress(default: Optional[Any] = None) -> Any:
    return read_json(PROGRESS_FILE, default)

def write_run_state(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(payload)
    payload.setdefault("updated_at", datetime.now().isoformat(timespec="seconds"))
    payload.setdefault("updated_utc", utc_now_iso())
    atomic_write_json(RUN_STATE_FILE, payload)
    return payload

def read_run_state(default: Optional[Any] = None) -> Any:
    return read_json(RUN_STATE_FILE, default)

def write_briefing(payload: Dict[str, Any]) -> Dict[str, Any]:
    atomic_write_json(BRIEFING_FILE, payload)
    return payload

def read_briefing(default: Optional[Any] = None) -> Any:
    return read_json(BRIEFING_FILE, default)

def pid_is_running(pid: Optional[int]) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False
