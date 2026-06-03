# Architecture Notes

## Data Flow
1. **generate_data.py** → Creates 55K+ appointment records with injected quality issues
2. **data_quality.py** → Validates all tables, produces `quality_report.csv`, cleans data
3. **load_to_postgres.py** → Loads cleaned data, applies schema DDL, refreshes mat views
4. **sheets_kpi_update.py** → Pulls KPIs from PostgreSQL, writes to Google Sheets
5. **no_show_prediction.py** → Trains Random Forest / XGBoost on historical appointment data

## PostgreSQL Schema Design Decisions
- **Materialized views** (`mv_monthly_revenue`, `mv_doctor_performance`) pre-aggregate
  heavy queries so dashboards load instantly; refreshed nightly via scheduler.
- **15 indexes** cover the most common query patterns (appointment_date, patient_id, status).
- **Generated column** (`resources.total_beds`) ensures occupied + available always sums correctly.
- **CHECK constraints** enforce business rules at the DB layer, not just application layer.
  Includes `gender IN ('Male','Female')` for both `patients` and `doctors`.
- **`doctors.gender` column** added so dashboards can segment performance by doctor gender.

## Why these tools?
- **Google Sheets API**: demonstrates automation of recurring reports — easy to share with non-technical stakeholders.
- **PostgreSQL**: enterprise DB with full SQL feature support, including window functions, CTEs, and materialised views.

## Data model
| Table | Rows (approx) | Notes |
|-------|---------------|-------|
| patients     | 10,000 | One row per unique patient, with cleaned/imputed demographics |
| doctors      | 80     | Reference table with name, gender, specialty, department |
| appointments | 55,000 | Fact table linked to patients + doctors |
| treatments   | 18,000 | Fact table linked to patients, with diagnosis + cost |
| resources    | 10     | Per-department daily snapshot of beds / staff / equipment |

## Data-quality strategy
- **Detect** in `data_quality.py` (no DB writes — pure pandas report).
- **Clean** in the same module: drop duplicates, drop bad-gender rows, impute out-of-range ages with the median, fillna for diagnosis.
- **Enforce** at the DB layer via `CHECK` constraints so bad rows can't re-enter via a manual SQL insert.
- The `reports/quality_report.csv` and `quality_summary.csv` are committed to the repo only as historical artifacts — they are gitignored in normal use.
