"""
Hospital Analytics — ETL Pipeline
Loads cleaned CSV data into PostgreSQL, refreshes materialized views.
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import psycopg2
import logging
import os
import time
from pathlib import Path
from datetime import datetime

# Auto-load .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; use system env vars or defaults

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("reports/etl.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ─── Config — set via environment variables or edit defaults ──────────────────
DB_HOST = os.getenv("DB_HOST",     "localhost")
DB_PORT = os.getenv("DB_PORT",     "5432")
DB_NAME = os.getenv("DB_NAME",     "hospital_analytics")
DB_USER = os.getenv("DB_USER",     "postgres")
DB_PASS = os.getenv("DB_PASS",     "postgres")

CLEAN_DIR = "data/cleaned"
SQL_DIR   = "sql/schema"


def get_engine():
    url = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(url, echo=False, pool_pre_ping=True)


def run_sql_file(engine, filepath: str):
    with open(filepath) as f:
        sql = f.read()
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
    logger.info(f"  ✓ Executed {filepath}")


def load_table(engine, df: pd.DataFrame, table: str, if_exists: str = "append"):
    before = len(df)
    df = df.drop_duplicates()          # final safety dedup before load
    df = df.where(pd.notnull(df), None)  # convert NaN → None for SQL NULLs
    df.to_sql(
        table, engine,
        if_exists=if_exists, index=False,
        method="multi", chunksize=1000
    )
    logger.info(f"  ✓ Loaded {len(df):,} rows into '{table}' (dropped {before - len(df)} dupes)")


def truncate_table(engine, table: str):
    with engine.connect() as conn:
        conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
        conn.commit()
    logger.info(f"  ✓ Truncated '{table}'")


def refresh_materialized_views(engine):
    views = ["mv_monthly_revenue", "mv_doctor_performance"]
    with engine.connect() as conn:
        for v in views:
            conn.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {v}"))
            conn.commit()
            logger.info(f"  ✓ Refreshed {v}")


def validate_row_counts(engine):
    tables = ["patients", "doctors", "appointments", "treatments", "resources"]
    logger.info("  Row count validation:")
    with engine.connect() as conn:
        for t in tables:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).fetchone()
            logger.info(f"    {t:20s}: {result[0]:>8,} rows")


def run_etl():
    start = time.time()
    logger.info("=" * 60)
    logger.info("  HOSPITAL ANALYTICS ETL PIPELINE STARTED")
    logger.info(f"  Run time: {datetime.utcnow().isoformat()}")
    logger.info("=" * 60)

    engine = get_engine()

    # ── Step 1: Apply schema ──────────────────────────────────────────────────
    logger.info("\n[1/5] Applying database schema...")
    run_sql_file(engine, f"{SQL_DIR}/01_schema.sql")

    # ── Step 2: Load reference tables (doctors, resources — rarely change) ────
    logger.info("\n[2/5] Loading reference data...")
    for table, file in [
        ("doctors",   "doctors.csv"),
        ("resources", "resources.csv"),
    ]:
        truncate_table(engine, table)
        df = pd.read_csv(f"{CLEAN_DIR}/{file}")
        load_table(engine, df, table)

    # ── Step 3: Load fact tables ──────────────────────────────────────────────
    logger.info("\n[3/5] Loading transactional data...")
    truncate_table(engine, "treatments")
    truncate_table(engine, "appointments")
    truncate_table(engine, "patients")

    patients = pd.read_csv(f"{CLEAN_DIR}/patients_clean.csv",
                           parse_dates=["registration_date"])
    appointments = pd.read_csv(f"{CLEAN_DIR}/appointments_clean.csv",
                               parse_dates=["appointment_date"])
    treatments = pd.read_csv(f"{CLEAN_DIR}/treatments_clean.csv",
                             parse_dates=["treatment_date"])

    # Only load appointments whose patient_id exists in patients
    valid_pids = set(patients["patient_id"].dropna())
    appointments = appointments[appointments["patient_id"].isin(valid_pids)]
    treatments   = treatments[treatments["patient_id"].isin(valid_pids)]

    load_table(engine, patients,     "patients")
    load_table(engine, appointments, "appointments")
    load_table(engine, treatments,   "treatments")

    # ── Step 4: Refresh materialized views ───────────────────────────────────
    logger.info("\n[4/5] Refreshing materialized views...")
    # First run needs CREATE ... WITH DATA instead of CONCURRENT REFRESH
    try:
        refresh_materialized_views(engine)
    except Exception:
        logger.warning("  Could not CONCURRENT REFRESH (first run). Running standard refresh.")
        with engine.connect() as conn:
            conn.execute(text("REFRESH MATERIALIZED VIEW mv_monthly_revenue"))
            conn.execute(text("REFRESH MATERIALIZED VIEW mv_doctor_performance"))
            conn.commit()

    # ── Step 5: Validate ─────────────────────────────────────────────────────
    logger.info("\n[5/5] Validating row counts...")
    validate_row_counts(engine)

    elapsed = round(time.time() - start, 2)
    logger.info(f"\n✅ ETL COMPLETE in {elapsed}s")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_etl()
