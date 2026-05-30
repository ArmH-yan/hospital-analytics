"""
Hospital Analytics — Daily Pipeline Scheduler
Orchestrates the full ETL → Quality → Sheets → ML pipeline.
Runs nightly via cron or Windows Task Scheduler.

Cron example (runs daily at 2:00 AM):
  0 2 * * * /usr/bin/python3 /path/to/automation/scheduler.py >> /var/log/hospital_etl.log 2>&1
"""

import schedule
import time
import logging
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("reports/scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Root of the project (parent of automation/)
ROOT = Path(__file__).parent.parent


def run_step(name: str, script_path: str) -> bool:
    """Run a Python script as a subprocess, return True on success."""
    logger.info(f"  ▶ Running: {name}")
    start = time.time()
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True, text=True
    )
    elapsed = round(time.time() - start, 2)
    if result.returncode == 0:
        logger.info(f"  ✅ {name} — OK ({elapsed}s)")
        return True
    else:
        logger.error(f"  ❌ {name} — FAILED ({elapsed}s)")
        logger.error(f"     STDERR: {result.stderr[-500:]}")
        return False


def daily_pipeline():
    logger.info("=" * 60)
    logger.info(f"  🏥 DAILY PIPELINE — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    logger.info("=" * 60)

    steps = [
        ("1. Generate Raw Data",    str(ROOT / "src/etl/generate_data.py")),
        ("2. Data Quality Checks",  str(ROOT / "src/quality/data_quality.py")),
        ("3. ETL → PostgreSQL",     str(ROOT / "src/etl/load_to_postgres.py")),
        ("4. Google Sheets Update", str(ROOT / "src/sheets/sheets_kpi_update.py")),
        ("5. ML No-show Model",     str(ROOT / "src/ml/no_show_prediction.py")),
    ]

    results = {}
    for name, script in steps:
        ok = run_step(name, script)
        results[name] = "✅ OK" if ok else "❌ FAILED"
        if not ok:
            logger.warning(f"  Pipeline interrupted at: {name}")
            # Continue other steps even if one fails
            # break  ← uncomment if you want hard-stop on failure

    logger.info("\n  Pipeline summary:")
    for step, status in results.items():
        logger.info(f"    {status}  {step}")
    logger.info("=" * 60)


def run_once():
    """Run the full pipeline once immediately (for testing)."""
    daily_pipeline()


def run_scheduled(hour: int = 2, minute: int = 0):
    """Schedule the pipeline to run daily at HH:MM."""
    run_time = f"{hour:02d}:{minute:02d}"
    logger.info(f"Scheduler started. Pipeline will run daily at {run_time}.")
    schedule.every().day.at(run_time).do(daily_pipeline)

    # Also run immediately on start
    daily_pipeline()

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Hospital Analytics Pipeline Scheduler")
    parser.add_argument("--once",      action="store_true", help="Run once and exit")
    parser.add_argument("--hour",      type=int, default=2, help="Scheduled hour (24h)")
    parser.add_argument("--minute",    type=int, default=0, help="Scheduled minute")
    args = parser.parse_args()

    if args.once:
        run_once()
    else:
        run_scheduled(args.hour, args.minute)
