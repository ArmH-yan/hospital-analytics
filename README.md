# 🏥 Hospital Operations Analytics & BI Platform

> **End-to-end data analytics portfolio project** — synthetic healthcare data, PostgreSQL data warehouse, automated ETL, Google Sheets KPI reporting, Power BI & Metabase dashboards, and a no-show prediction ML model.

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
│  │  Indexes (14)        │   │
│  └──────────────────────┘   │
└──────┬──────┬───────┬────────┘
       ↓      ↓       ↓
 ┌─────┐  ┌──────┐  ┌──────────────┐
 │Power│  │Meta- │  │Google Sheets │
 │ BI  │  │ base │  │  KPI Report  │
 └─────┘  └──────┘  └──────────────┘
                          ↓
              ┌─────────────────────┐
              │  ML LAYER           │
              │  No-show Prediction │
              │  (Random Forest /   │
              │    XGBoost)         │
              └─────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Tool |
|-------|------|
| Language | Python 3.11 |
| Data Processing | pandas, numpy |
| Database | PostgreSQL 16 |
| ORM / DB Driver | SQLAlchemy, psycopg2 |
| BI / Dashboards | Power BI, Metabase |
| Sheets Automation | Google Sheets API, gspread |
| Machine Learning | scikit-learn, XGBoost |
| Scheduling | schedule |
| Containerization | Docker (Metabase) |

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
│   ├── powerbi/
│   │   └── POWERBI_SPEC.md   # Dashboard spec + all DAX measures
│   └── metabase/
│       └── METABASE_SPEC.md  # Metabase setup + SQL questions
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
│   └── architecture.md
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
# Local PostgreSQL, or via Docker:
docker run -d --name hospital-pg \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=hospital_analytics \
  -p 5432:5432 postgres:16
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
| Indexes (14 created) | schema file |
| Generated Columns | resources.total_beds |

---

## 🤖 ML Model Performance

The no-show prediction model uses these features:
- Patient age
- Department
- Appointment weekday
- Days since registration
- Prior no-show count + rate

**Expected results** (varies by random seed and data):
| Metric | Random Forest | XGBoost |
|--------|--------------|---------|
| Accuracy | ~0.78 | ~0.80 |
| ROC-AUC | ~0.72 | ~0.74 |
| Recall (No-show) | ~0.65 | ~0.68 |

**Business impact**: Flagging high-risk appointments for reminder calls can reduce no-show revenue loss by an estimated 30–40%.

---

## 📈 Data Quality Findings

Sample output from `quality_report.csv`:

| Table | Check | Severity | Issues Found | % Affected |
|-------|-------|----------|-------------|------------|
| patients | Duplicate primary key | HIGH | ~50 | ~0.5% |
| patients | Negative age | HIGH | ~30 | ~0.3% |
| appointments | Invalid status | HIGH | ~220 | ~0.4% |
| appointments | Negative cost | HIGH | ~165 | ~0.3% |
| treatments | Future date | HIGH | ~144 | ~0.8% |

---

## 🔮 Future Improvements

- [ ] Add dbt for SQL transformations layer
- [ ] Airflow/Prefect for proper DAG orchestration
- [ ] Add streaming layer (Kafka) for real-time appointments
- [ ] LLM-based natural language query interface for clinical staff
- [ ] Docker Compose to run the full stack locally
- [ ] CI/CD pipeline for automated tests


---

## 🙋 About

Built as a portfolio project targeting Intern/Junior BI Analyst and Data Analyst roles,
specifically demonstrating skills in Docker, SQL, PostgreSQL, Python, BI tooling, and automation.

Skills demonstrated: SQL · PostgreSQL · Python · pandas · SQLAlchemy · Power BI · Google Sheets API · scikit-learn · XGBoost · ETL · Data Quality · Scheduling
