"""Central logging configuration for Nifty 200 AI Advisor."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

APP_LOG_FILE = LOG_DIR / "app.log"
AGENT_LOG_FILE = LOG_DIR / "agent.log"
WORKER_LOG_FILE = LOG_DIR / "worker.log"

def get_logger(name: str, log_file: Path | str, level: int = logging.INFO) -> logging.Logger:
    """Return a rotating file logger with a consistent format."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler = RotatingFileHandler(
            str(log_file), maxBytes=2_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(level)
        logger.addHandler(stream_handler)

    return logger

def configure_root_logging() -> logging.Logger:
    """Configure a shared root logger that also writes to app.log."""
    return get_logger("nifty200", APP_LOG_FILE)
