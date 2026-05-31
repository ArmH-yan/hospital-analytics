"""
Hospital Analytics - Daily Pipeline Scheduler
"""

import schedule
import time
import logging
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding so all characters print correctly
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

os.makedirs("reports", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("reports/scheduler.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent


def run_step(name: str, script_path: str) -> bool:
    logger.info(f"  >> Running: {name}")
    start = time.time()

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=str(ROOT)
    )
    elapsed = round(time.time() - start, 2)
    if result.returncode == 0:
        logger.info(f"  [OK] {name} - done in {elapsed}s")
        return True
    else:
        logger.error(f"  [FAILED] {name} - failed in {elapsed}s")
        logger.error(f"  STDERR:\n{result.stderr[-1000:]}")
        return False


def daily_pipeline():
    logger.info("=" * 60)
    logger.info(f"  HOSPITAL ANALYTICS PIPELINE - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    logger.info("=" * 60)

    steps = [
        ("1. Generate Raw Data",    str(ROOT / "src" / "etl"     / "generate_data.py")),
        ("2. Data Quality Checks",  str(ROOT / "src" / "quality" / "data_quality.py")),
        ("3. ETL -> PostgreSQL",    str(ROOT / "src" / "etl"     / "load_to_postgres.py")),
        ("4. Google Sheets Update", str(ROOT / "src" / "sheets"  / "sheets_kpi_update.py")),
        ("5. ML No-show Model",     str(ROOT / "src" / "ml"      / "no_show_prediction.py")),
    ]

    results = {}
    for name, script in steps:
        ok = run_step(name, script)
        results[name] = "OK" if ok else "FAILED"
        if not ok:
            logger.warning(f"  Step failed: {name} - continuing...")

    logger.info("\n  Pipeline summary:")
    for step, status in results.items():
        logger.info(f"    [{status}]  {step}")
    logger.info("=" * 60)


def run_once():
    daily_pipeline()


def run_scheduled(hour: int = 2, minute: int = 0):
    run_time = f"{hour:02d}:{minute:02d}"
    logger.info(f"Scheduler started. Pipeline will run daily at {run_time}.")
    schedule.every().day.at(run_time).do(daily_pipeline)
    daily_pipeline()
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--once",   action="store_true")
    parser.add_argument("--hour",   type=int, default=2)
    parser.add_argument("--minute", type=int, default=0)
    args = parser.parse_args()

    if args.once:
        run_once()
    else:
        run_scheduled(args.hour, args.minute)
