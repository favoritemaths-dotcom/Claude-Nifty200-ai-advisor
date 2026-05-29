"""Lightweight launcher for running agent.py outside the Streamlit request cycle."""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from logger_config import AGENT_LOG_FILE, get_logger
from progress_tracker import (
    LOG_DIR,
    pid_is_running,
    read_progress,
    read_run_state,
    utc_now_iso,
    write_run_state,
)

ROOT_DIR = Path(__file__).resolve().parent
LOGGER = get_logger("background_worker", LOG_DIR / "worker.log")

def _streamlit_secret(key: str) -> str:
    try:
        import streamlit as st  # type: ignore
        return str(st.secrets.get(key, os.getenv(key, "")) or os.getenv(key, ""))
    except Exception:
        return os.getenv(key, "")

def _build_env() -> Dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env.setdefault("GEMINI_API_KEY", _streamlit_secret("GEMINI_API_KEY"))
    env.setdefault("GROQ_API_KEY", _streamlit_secret("GROQ_API_KEY"))
    return env

def get_runtime_snapshot() -> Dict[str, Any]:
    """Return a merged view of the latest run state and progress."""
    run_state = read_run_state({}) or {}
    progress = read_progress({}) or {}
    briefing_exists = (ROOT_DIR / "latest_briefing.json").exists()

    snapshot: Dict[str, Any] = {
        "run_state": run_state,
        "progress": progress,
        "briefing_exists": briefing_exists,
        "status": progress.get("status") or run_state.get("status") or ("done" if briefing_exists else "idle"),
        "message": progress.get("message") or run_state.get("message") or "",
        "detail": progress.get("detail") or run_state.get("detail") or "",
        "pid": run_state.get("pid"),
        "started_at": run_state.get("started_at") or run_state.get("updated_at"),
        "mode": run_state.get("mode", "full"),
    }

    pid = snapshot.get("pid")
    if snapshot["status"] == "running" and pid and not pid_is_running(pid):
        # The worker died unexpectedly. If a briefing exists, treat it as done.
        snapshot["status"] = "done" if briefing_exists else "error"
        snapshot["detail"] = snapshot.get("detail") or "Background process stopped unexpectedly."

    if briefing_exists and snapshot["status"] == "idle":
        snapshot["status"] = "done"
    return snapshot

def launch_agent_job(quick_mode: bool = False) -> Dict[str, Any]:
    """Launch agent.py as a detached subprocess and record the run state."""
    existing = get_runtime_snapshot()
    if existing.get("status") == "running":
        return {
            "ok": False,
            "reason": "A run is already active.",
            "runtime": existing,
        }

    args = [sys.executable, "agent.py"]
    if quick_mode:
        args.append("--quick")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stdout_path = AGENT_LOG_FILE
    stdout_handle = open(stdout_path, "a", encoding="utf-8", buffering=1)
    env = _build_env()
    job_payload = {
        "status": "running",
        "mode": "quick" if quick_mode else "full",
        "pid": None,
        "command": " ".join(args),
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "started_utc": utc_now_iso(),
        "message": "Analysis started",
        "detail": "Launching agent process",
    }

    try:
        proc = subprocess.Popen(
            args,
            cwd=str(ROOT_DIR),
            env=env,
            stdout=stdout_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        job_payload["pid"] = proc.pid
        job_payload["message"] = "Analysis running"
        job_payload["detail"] = "Agent subprocess started"
        write_run_state(job_payload)
        LOGGER.info("Launched agent process pid=%s mode=%s", proc.pid, job_payload["mode"])
        return {"ok": True, "pid": proc.pid, "runtime": get_runtime_snapshot()}
    except Exception as exc:
        job_payload["status"] = "error"
        job_payload["message"] = "Failed to launch agent"
        job_payload["detail"] = str(exc)
        write_run_state(job_payload)
        LOGGER.exception("Unable to launch agent process")
        return {"ok": False, "reason": str(exc), "runtime": get_runtime_snapshot()}
    finally:
        try:
            stdout_handle.close()
        except Exception:
            pass
