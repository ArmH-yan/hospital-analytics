# Architecture Notes

## Data Flow
1. **generate_data.py** → Creates 55K+ appointment records with injected quality issues
2. **data_quality.py** → Validates all tables, produces quality_report.csv, cleans data
3. **load_to_postgres.py** → Loads cleaned data, applies schema DDL, refreshes mat views
4. **sheets_kpi_update.py** → Pulls KPIs from PostgreSQL, writes to Google Sheets
5. **no_show_prediction.py** → Trains Random Forest / XGBoost on historical appointment data

## PostgreSQL Schema Design Decisions
- **Materialized views** (mv_monthly_revenue, mv_doctor_performance) pre-aggregate heavy
  queries so dashboards load instantly; refreshed nightly via scheduler.
- **14 indexes** cover the most common query patterns (appointment_date, patient_id, status).
- **Generated column** (resources.total_beds) ensures occupied + available always sums correctly.
- **CHECK constraints** enforce business rules at the DB layer, not just application layer.

## Why these tools?
- **Metabase**: explicitly named in BostonGene job listing; free, Docker-friendly, non-technical users can self-serve.
- **Google Sheets API**: demonstrates automation of recurring reports — the job asks for exactly this.
- **PostgreSQL**: enterprise DB with full SQL feature support; Greenplum (also in the listing) shares the same query syntax.
