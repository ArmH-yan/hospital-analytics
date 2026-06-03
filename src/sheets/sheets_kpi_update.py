"""
Hospital Analytics — Google Sheets KPI Automation
Pulls daily KPIs from PostgreSQL and writes them to a Google Sheet.

Setup:
  1. Create a GCP project, enable Sheets API + Drive API.
  2. Create a Service Account, download JSON key -> save as credentials/gsheets_key.json
  3. Share your Google Sheet with the service account email.
  4. Set SPREADSHEET_ID below.

pip install gspread google-auth sqlalchemy psycopg2-binary pandas
"""

import gspread
from google.oauth2.service_account import Credentials
from sqlalchemy import create_engine, text
import pandas as pd
from datetime import datetime, date, timezone
import logging
import os

# Auto-load .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────
SPREADSHEET_ID   = os.getenv("SPREADSHEET_ID", "")
if not SPREADSHEET_ID:
    logger.warning("SPREADSHEET_ID env var not set. Google Sheets update will be skipped.")
CREDENTIALS_FILE = "credentials/gsheets_key.json"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "hospital_analytics")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")


def get_engine():
    url = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(url, echo=False, pool_pre_ping=True)


def get_sheets_client():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)


# ─── KPI Queries ──────────────────────────────────────────────────────────────

def fetch_executive_kpis(engine) -> pd.DataFrame:
    query = """
    SELECT
        CURRENT_DATE::TEXT                                          AS report_date,
        COUNT(DISTINCT patient_id)                                  AS total_patients,
        COUNT(*)                                                    AS total_appointments,
        COUNT(*) FILTER (WHERE appointment_status = 'No-show')     AS total_no_shows,
        ROUND(COUNT(*) FILTER (WHERE appointment_status = 'No-show')::NUMERIC
              / NULLIF(COUNT(*), 0) * 100, 2)                      AS no_show_rate_pct,
        ROUND(SUM(appointment_cost)
              FILTER (WHERE appointment_status = 'Completed'), 2)  AS total_revenue,
        ROUND(AVG(waiting_time_minutes), 1)                        AS avg_wait_minutes
    FROM appointments
    """
    return pd.read_sql(query, engine)


def fetch_monthly_kpis(engine) -> pd.DataFrame:
    return pd.read_sql(
        "SELECT * FROM v_monthly_kpis ORDER BY month DESC LIMIT 24",
        engine
    )


def fetch_department_kpis(engine) -> pd.DataFrame:
    return pd.read_sql(
        "SELECT * FROM v_department_performance ORDER BY total_revenue DESC",
        engine
    )


def fetch_top_doctors(engine) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT doctor_name, department, total_appointments,
               no_show_rate_pct, total_revenue, avg_wait_minutes
        FROM mv_doctor_performance
        ORDER BY total_revenue DESC
        LIMIT 20
        """,
        engine
    )


def fetch_resource_snapshot(engine) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT department, available_beds, occupied_beds, total_beds,
               ROUND(occupied_beds::NUMERIC / NULLIF(total_beds,0) * 100, 2) AS occupancy_pct,
               staff_count,
               ROUND(equipment_utilization * 100, 2) AS equipment_util_pct
        FROM resources
        ORDER BY occupancy_pct DESC
        """,
        engine
    )


# ─── Sheet writers ────────────────────────────────────────────────────────────

def write_sheet(spreadsheet, sheet_name: str, df: pd.DataFrame, add_timestamp: bool = True):
    """Write a DataFrame to a worksheet, creating it if needed."""
    try:
        ws = spreadsheet.worksheet(sheet_name)
        ws.clear()
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=sheet_name, rows=500, cols=30)

    # Header row
    headers = list(df.columns)
    rows    = [headers] + df.fillna("").astype(str).values.tolist()

    if add_timestamp:
        rows.insert(0, [f"🔄 Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"])
        rows.insert(1, [])  # blank spacer

    ws.update("A1", rows)

    # Bold the header row
    from openpyxl.utils import get_column_letter
    header_row = 3 if add_timestamp else 1
    last_col = get_column_letter(len(headers))
    ws.format(f"A{header_row}:{last_col}{header_row}", {
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.18, "green": 0.38, "blue": 0.62}
    })

    logger.info(f"  [OK] Sheet '{sheet_name}' updated with {len(df)} rows")
    return ws


def write_kpi_overview(spreadsheet, exec_kpi: pd.DataFrame):
    """Write a styled executive KPI card sheet."""
    try:
        ws = spreadsheet.worksheet("📊 Executive KPIs")
        ws.clear()
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title="📊 Executive KPIs", rows=30, cols=5)

    kpi = exec_kpi.iloc[0]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    data = [
        ["Hospital Operations Analytics — Executive KPI Dashboard"],
        [f"Last updated: {now}"],
        [],
        ["KPI",                    "Value",                          "Notes"],
        ["Total Patients",          f"{int(kpi.total_patients):,}",   "All registered"],
        ["Total Appointments",      f"{int(kpi.total_appointments):,}", "All time"],
        ["Total No-shows",          f"{int(kpi.total_no_shows):,}",   ""],
        ["No-show Rate",            f"{kpi.no_show_rate_pct}%",       "Target: <15%"],
        ["Total Revenue (Appts)",   f"${float(kpi.total_revenue):,.2f}", "Completed only"],
        ["Avg Waiting Time",        f"{kpi.avg_wait_minutes} min",    "All completed"],
        ["Report Date",             str(kpi.report_date),             ""],
    ]

    ws.update("A1", data)
    ws.format("A1", {"textFormat": {"bold": True, "fontSize": 14}})
    ws.format("A4:C4", {"textFormat": {"bold": True}})
    logger.info("  [OK] Executive KPI sheet updated")


def run_sheets_update():
    # Skip gracefully if credentials file is not set up yet
    if not os.path.exists(CREDENTIALS_FILE):
        logger.warning("[SKIP] Google Sheets: credentials/gsheets_key.json not found.")
        logger.warning("[SKIP] Follow the Google Sheets setup guide to enable this step.")
        return
    if SPREADSHEET_ID in ("YOUR_SPREADSHEET_ID_HERE", "", None):
        logger.warning("[SKIP] Google Sheets: SPREADSHEET_ID not set in .env file.")
        return

    logger.info("=" * 60)
    logger.info("  GOOGLE SHEETS KPI UPDATE")
    logger.info(f"  {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    engine = get_engine()
    gc     = get_sheets_client()
    ss     = gc.open_by_key(SPREADSHEET_ID)

    logger.info("Fetching KPIs from PostgreSQL...")
    exec_kpi    = fetch_executive_kpis(engine)
    monthly     = fetch_monthly_kpis(engine)
    departments = fetch_department_kpis(engine)
    doctors     = fetch_top_doctors(engine)
    resources   = fetch_resource_snapshot(engine)

    logger.info("Writing to Google Sheets...")
    write_kpi_overview(ss, exec_kpi)
    write_sheet(ss, "Monthly KPIs",           monthly)
    write_sheet(ss, "Department Performance", departments)
    write_sheet(ss, "Top Doctors",          doctors)
    write_sheet(ss, "Resource Snapshot",      resources)

    logger.info("\n[DONE] Google Sheets update complete")


if __name__ == "__main__":
    run_sheets_update()
