"""Optional local scheduler fallback for running the agent from a machine that stays on."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from background_worker import launch_agent_job

IST_OFFSET = timezone(timedelta(hours=5, minutes=30))

def seconds_until_next_weekday_0830() -> float:
    now = datetime.now(IST_OFFSET)
    target = now.replace(hour=8, minute=30, second=0, microsecond=0)
    while target <= now or target.weekday() >= 5:
        target += timedelta(days=1)
        target = target.replace(hour=8, minute=30, second=0, microsecond=0)
    return max(1.0, (target - now).total_seconds())

def run_forever() -> None:
    print("Local scheduler started. Press Ctrl+C to stop.")
    while True:
        sleep_for = seconds_until_next_weekday_0830()
        print(f"Next run in {sleep_for/60:.1f} minutes")
        time.sleep(sleep_for)
        launch_agent_job(quick_mode=False)
        time.sleep(30)

if __name__ == "__main__":
    run_forever()
