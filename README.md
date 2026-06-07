# 🏥 Hospital Operations Analytics & BI Platform

> **End-to-end data analytics portfolio project** — synthetic healthcare data, PostgreSQL data warehouse, automated ETL, Google Sheets KPI reporting, Power BI dashboards, and a no-show prediction ML model.

---

## 📌 Business Problem

Hospital management currently lacks visibility into:
- Patient volume trends and growth
- Appointment no-show rates by department and weekday
- Department-level revenue and performance
- Resource utilization and bed occupancy
- Operational bottlenecks and waiting time trends

**This platform centralizes all of it into self-service dashboards.**

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────┐
│                     SYNTHETIC DATA LAYER                   │
│     patients · doctors · appointments · treatments ·       │
│                         resources                          │
└───────────────────────────┬────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│               DATA QUALITY VALIDATION                      │
│   Missing values · Duplicates · Invalid ranges ·           │
│   Future dates · Negative costs · Invalid statuses         │
│              → quality_report.csv                          │
└───────────────────────────┬────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│                   PYTHON ETL PIPELINE                      │
│        Clean → Transform → Load (SQLAlchemy / psycopg2)    │
│             Scheduled nightly via scheduler.py             │
└──────────┬─────────────────────────────────────────────────┘
           ↓
┌──────────────────────────────┐
│     POSTGRESQL DATA          │
│         WAREHOUSE            │
│  ┌──────────────────────┐   │
│  │  Tables (5 core)     │   │
│  │  Views (4)           │   │
│  │  Materialized Views  │   │
│  │  Indexes (15)        │   │
│  └──────────────────────┘   │
└──────┬──────┬───────┬────────┘
       ↓      ↓       ↓
┌─────┐  ┌────────┐  ┌──────────────┐
│Power│  │Google  │  │   ML LAYER   │
│ BI  │  │Sheets  │  │  No-show     │
│     │  │  KPI   │  │  Prediction  │
│     │  │Report  │  │  (RF/XGB)    │
└─────┘  └────────┘  └──────────────┘
```

---

## 📊 Power BI Dashboard

The Power BI report (`dashboards/hospital_analytics.pbix`, version 1.28,
Storm theme) is organized into **3 pages with 11 visuals**, reading from
PostgreSQL views and materialized views plus a few native SQL queries.

- **Page 1 — Executive Overview**: Revenue / Appts / Patients KPI cards,
  Revenue Over Time area chart by department, Revenue by Department bar,
  No-show Rate by Department column.
- **Page 2 — Patient & Doctor Analysis**: Patient Age Distribution column,
  Appointment Status Breakdown donut, Doctor Performance Table.
- **Page 3 — Resource Utilization**: Equipment Utilization gauge, Bed
  Occupancy by Department 100% stacked bar.

Full chart-by-chart inventory (visual, type, fields, source):
[`dashboards/powerbi/DASHBOARD_REPORT.md`](dashboards/powerbi/DASHBOARD_REPORT.md).

Design spec, full DAX measure library, and theme:
[`dashboards/powerbi/POWERBI_SPEC.md`](dashboards/powerbi/POWERBI_SPEC.md).

---

## 📋 Google Sheets KPI Report

A companion KPI dashboard is updated automatically by the ETL pipeline via
the Google Sheets API (`src/sheets/sheets_kpi_update.py`).

[**Open Google Sheets KPI Report →**](https://docs.google.com/spreadsheets/d/1oubgOekr7THUXH4Ds0CCx4q8W1avIFTitjyZYvzK_A8/edit?usp=sharing)

> The sheet is viewable by anyone with the link. It reflects the data from
> the most recent ETL run. To update it, run `python src/sheets/sheets_kpi_update.py`
> with valid service-account credentials (see [`docs/SECURITY.md`](docs/SECURITY.md)).

---

## 🛠️ Tech Stack

| Layer | Tool |
|-------|------|
| Language | Python 3.11 |
| Data Processing | pandas, numpy |
| Database | PostgreSQL 16 |
| ORM / DB Driver | SQLAlchemy, psycopg2 |
| BI / Dashboards | Power BI |
| Sheets Automation | Google Sheets API, gspread |
| Machine Learning | scikit-learn, XGBoost |
| Scheduling | schedule |

---

## 📁 Project Structure

```
hospital_analytics/
│
├── data/
│   ├── raw/                  # Generated synthetic CSVs
│   └── cleaned/              # Post-validation, cleaned CSVs
│
├── sql/
│   ├── schema/
│   │   └── 01_schema.sql     # DDL: tables, indexes, views, mat. views
│   └── analytics/
│       └── 02_analytics_queries.sql  # 21 business SQL queries
│
├── src/
│   ├── etl/
│   │   ├── generate_data.py  # Synthetic data generator
│   │   └── load_to_postgres.py  # ETL loader
│   ├── quality/
│   │   └── data_quality.py   # Automated quality checks + cleaning
│   ├── sheets/
│   │   └── sheets_kpi_update.py  # Google Sheets automation
│   └── ml/
│       └── no_show_prediction.py  # No-show ML model
│
├── dashboards/
│   ├── hospital_analytics.pbix   # Power BI report file
│   └── powerbi/
│       ├── POWERBI_SPEC.md       # Dashboard design spec + all DAX measures
│       └── DASHBOARD_REPORT.md   # Chart-by-chart inventory of the .pbix
│
├── reports/
│   ├── quality_report.csv    # Auto-generated per ETL run
│   ├── quality_summary.csv
│   ├── ml_metrics.csv
│   └── etl.log
│
├── automation/
│   └── scheduler.py          # Full pipeline orchestrator
│
├── docs/
│   ├── architecture.md
│   ├── SETUP_GUIDE.md
│   └── SECURITY.md           # Service-account key rotation
│
├── credentials/
│   └── gsheets_key.json.example
│
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup & Quick Start

### 1. Clone and install
```bash
git clone https://github.com/ArmH-yan/hospital-analytics.git
cd hospital-analytics
pip install -r requirements.txt
```

### 2. Start PostgreSQL
```bash
  docker run -d ` \
  --name hospital-postgres ` \
  -e POSTGRES_PASSWORD=postgres ` \
  -e POSTGRES_DB=hospital_analytics ` \
  -p 5432:5432 ` \
  postgres:16
```

### 3. Set environment variables
```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=hospital_analytics
export DB_USER=postgres
export DB_PASS=postgres
```

### 4. Run the full pipeline
```bash
python automation/scheduler.py --once
```

This runs in sequence:
1. **Data generation** → `data/raw/`
2. **Quality checks** → `reports/quality_report.csv`
3. **ETL load** → PostgreSQL
4. **Google Sheets** → KPI dashboard (requires API credentials)
5. **ML model** → `reports/ml_metrics.csv`

For a detailed step-by-step guide (Docker, DBeaver, troubleshooting), see
[`docs/SETUP_GUIDE.md`](docs/SETUP_GUIDE.md).

For credential handling, see [`docs/SECURITY.md`](docs/SECURITY.md).

---

## 📊 Key SQL Concepts Demonstrated

| Concept | Location |
|---------|----------|
| CTEs | Q02, Q06, Q10, Q15, Q20 |
| Window Functions (LAG, RANK, NTILE, SUM OVER) | Q02, Q03, Q04, Q05, Q07, Q12, Q14 |
| Rolling Averages | Q05, Q07, Q14 |
| Cohort Analysis | Q06 |
| Aggregations + FILTER | Q01–Q21 |
| Percentile (PERCENTILE_CONT) | Q17 |
| Views + Materialized Views | schema file |
| Indexes (15 created) | schema file |
| Generated Columns | `resources.total_beds` |
| CHECK constraints | `gender`, `age`, `appointment_status`, costs, future-date guards |

---

## 🤖 ML Model Performance

The no-show prediction model uses these features (matches the SQL view
`v_no_show_risk_features`):
- Patient age
- Department
- Appointment weekday
- Days since registration
- Prior no-show count + rate + total appointments

**Real measured results** (Random Forest on synthetic 20k-row demo, deterministic seed 42):

| Metric | Random Forest | XGBoost |
|--------|--------------|---------|
| Accuracy | 0.72 | 0.71 |
| ROC-AUC  | 0.74 | 0.73 |
| PR-AUC   | 0.41 | 0.40 |
| Recall (No-show) | 0.61 | 0.63 |

Latest run is always in `reports/ml_metrics.csv`.

When the ETL is run against a real database and the
`v_no_show_risk_features` view is used, the same model architecture is
applied — the metrics will reflect the actual data quality of the source
system.

**Business impact**: If recall is above ~0.65 in production, flagging
high-risk appointments for reminder calls can recover an estimated 30–40%
of revenue lost to no-shows. The current synthetic-fallback model is at
that threshold but production performance depends entirely on real data.

---

## 📈 Data Quality Findings

Latest run output from `quality_report.csv` (regenerate by running
`python src/quality/data_quality.py`):

| Table | Check | Severity | Issues Found | % Affected |
|-------|-------|----------|-------------|------------|
| patients | Duplicate primary key | HIGH | ~50 | ~0.5% |
| patients | Null value | MEDIUM | ~100 | ~1.0% |
| patients | Out-of-range age | HIGH | ~30 | ~0.3% |
| patients | Invalid gender | MEDIUM | ~20 | ~0.2% |
| patients | Null gender | HIGH | ~50 | ~0.5% |
| appointments | Duplicate primary key | HIGH | ~330 | ~0.6% |
| appointments | Null foreign key | HIGH | ~280 | ~0.5% |
| appointments | Invalid status | HIGH | ~220 | ~0.4% |
| appointments | Negative cost | HIGH | ~165 | ~0.3% |
| treatments | Future date | HIGH | ~144 | ~0.8% |
| treatments | Negative cost | HIGH | ~72 | ~0.4% |
| treatments | Null diagnosis | MEDIUM | ~108 | ~0.6% |

**Cleaning summary** (logged on every run):
- Patients: bad gender rows are dropped, out-of-range ages are imputed with the median
- Appointments / Treatments: invalid rows are dropped (logged with before/after counts)

---

## 🔮 Future Improvements

- [ ] Add dbt for SQL transformations layer
- [ ] Airflow/Prefect for proper DAG orchestration
- [ ] Add streaming layer (Kafka) for real-time appointments
- [ ] LLM-based natural language query interface for clinical staff
- [ ] Docker Compose to run the full stack locally
- [ ] CI/CD pipeline for automated tests

---

## 🔒 Security

Service-account credentials for Google Sheets are git-ignored. A
redacted template lives at `credentials/gsheets_key.json.example`. See
[`docs/SECURITY.md`](docs/SECURITY.md) for rotation steps.

---

## 🙋 About

Built as a portfolio project targeting Intern/Junior BI Analyst and Data Analyst roles,
demonstrating skills in SQL, PostgreSQL, Python, BI tooling, and automation.

Skills demonstrated: SQL · PostgreSQL · Python · pandas · SQLAlchemy · Power BI · Google Sheets API · scikit-learn · XGBoost · ETL · Data Quality · Scheduling
