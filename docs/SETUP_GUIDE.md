# 🏥 Complete Setup Guide — Hospital Analytics Project
# Every command you need, in exact order.
# Written for Windows 10/11 with PowerShell.

---

## BEFORE YOU START — Read This

The pipeline has 5 steps. Steps 1 and 2 work immediately.
Steps 3, 4, 5 need extra setup (PostgreSQL running + packages installed).
This guide fixes everything one by one.

---

## PART A — Install Python packages correctly
## PART B — Start PostgreSQL with Docker
## PART C — Run the ETL (Step 3)
## PART D — Google Sheets (Step 4) — optional, skip for now
## PART E — Run ML model (Step 5)
## PART F — Run the full pipeline successfully

---

# ════════════════════════════════════════════════
# PART A — Install Python packages
# ════════════════════════════════════════════════

# Open PowerShell (search "PowerShell" in Start menu).
# Navigate to your project folder first:

cd C:\path\to\hospital_analytics
# Example: cd C:\Users\Arm\Desktop\hospital_analytics

# Check which Python you have:
python --version
# Must be 3.9 or higher. If you see "not recognized", install Python from:
# https://www.python.org/downloads
# ⚠️ During install, CHECK the box "Add Python to PATH"

# Install ALL required packages in one command:
pip install pandas numpy sqlalchemy psycopg2-binary scikit-learn schedule gspread google-auth

# If pip gives an "externally managed" error, add --break-system-packages:
pip install pandas numpy sqlalchemy psycopg2-binary scikit-learn schedule gspread google-auth --break-system-packages

# Verify packages installed correctly:
python -c "import pandas, numpy, sqlalchemy, psycopg2, sklearn, schedule; print('All packages OK')"
# Should print: All packages OK
# If any package fails, install it individually:
# pip install psycopg2-binary
# pip install sqlalchemy
# etc.

---

# ════════════════════════════════════════════════
# PART B — Start PostgreSQL with Docker
# ════════════════════════════════════════════════

# ── B1. Make sure Docker Desktop is running ──────────────────────────────────
# Open Docker Desktop from your Start menu or taskbar.
# Wait until you see a GREEN dot and "Engine running" in the bottom left.
# This takes 20-30 seconds after opening.

# ── B2. Check Docker works ───────────────────────────────────────────────────
docker --version
# Expected: Docker version 26.x.x, build ...
# If "docker is not recognized": Docker Desktop isn't installed or not in PATH.
# Fix: Close and reopen PowerShell after installing Docker Desktop.

# ── B3. Start PostgreSQL container ───────────────────────────────────────────
docker run -d `
  --name hospital-postgres `
  -e POSTGRES_PASSWORD=postgres `
  -e POSTGRES_DB=hospital_analytics `
  -p 5432:5432 `
  postgres:16

# This downloads the PostgreSQL 16 image (~150MB, first time only) and starts it.
# Expected output: a long string like "3f8a2c91d7b4..." (the container ID)

# ── B4. Verify PostgreSQL is actually running ─────────────────────────────────
docker ps
# You should see a row with:
#   NAMES               STATUS
#   hospital-postgres   Up X seconds

# ── B5. Quick connection test ─────────────────────────────────────────────────
docker exec -it hospital-postgres psql -U postgres -d hospital_analytics -c "\l"
# Expected output: lists databases including hospital_analytics
# If you see "Error response from daemon: No such container":
#   → the container didn't start. Run step B3 again.

# ── TROUBLESHOOTING: port 5432 already in use ────────────────────────────────
# Error: "Bind for 0.0.0.0:5432 failed: port is already allocated"
# Fix: Change the HOST port from 5432 to 5433:
docker run -d `
  --name hospital-postgres `
  -e POSTGRES_PASSWORD=postgres `
  -e POSTGRES_DB=hospital_analytics `
  -p 5433:5432 `
  postgres:16
# Then in .env file (created below), set DB_PORT=5433

---

# ════════════════════════════════════════════════
# PART C — Configure and run ETL (Step 3)
# ════════════════════════════════════════════════

# ── C1. Create a .env file with your database credentials ─────────────────────
# In the hospital_analytics/ folder, create a file called ".env"
# (copy from .env.example):
copy .env.example .env
# or on Mac/Linux:
# cp .env.example .env

# Open .env in any text editor (Notepad, VS Code) — it should look like this:
#   DB_HOST=localhost
#   DB_PORT=5432
#   DB_NAME=hospital_analytics
#   DB_USER=postgres
#   DB_PASS=postgres
# Leave it exactly as-is (unless you changed the port to 5433 above).

# ── C2. Install python-dotenv so scripts read .env automatically ───────────────
pip install python-dotenv
pip install python-dotenv --break-system-packages   # if you get an error

# ── C3. Test the database connection from Python ──────────────────────────────
python -c "
import psycopg2
conn = psycopg2.connect(
    host='localhost', port=5432,
    dbname='hospital_analytics',
    user='postgres', password='postgres'
)
print('PostgreSQL connection: OK')
conn.close()
"
# Expected: PostgreSQL connection: OK
# If "Connection refused": Docker container isn't running. Run: docker start hospital-postgres
# If "password authentication failed": wrong password. Should be "postgres".

# ── C4. Run the ETL step alone to verify it works ─────────────────────────────
# First make sure data/cleaned/ exists (from step 2):
python src/quality/data_quality.py
# Expected: prints quality report, saves data/cleaned/ files

# Then run ETL:
python src/etl/load_to_postgres.py
# Expected output (takes 10-30 seconds):
#   [INFO] [1/5] Applying database schema...
#   [INFO] [2/5] Loading reference data...
#   [INFO]   ✓ Loaded 80 rows into 'doctors'
#   [INFO]   ✓ Loaded 10 rows into 'resources'
#   [INFO] [3/5] Loading transactional data...
#   [INFO]   ✓ Loaded 9,xxx rows into 'patients'
#   [INFO]   ✓ Loaded 54,xxx rows into 'appointments'
#   [INFO]   ✓ Loaded 17,xxx rows into 'treatments'
#   [INFO] [4/5] Refreshing materialized views...
#   [INFO] [5/5] Validating row counts...
#   [INFO] ✅ ETL COMPLETE in X.Xs

# ── C5. Verify data in the database ───────────────────────────────────────────
docker exec -it hospital-postgres psql -U postgres -d hospital_analytics -c "
SELECT
  (SELECT COUNT(*) FROM patients)     AS patients,
  (SELECT COUNT(*) FROM doctors)      AS doctors,
  (SELECT COUNT(*) FROM appointments) AS appointments,
  (SELECT COUNT(*) FROM treatments)   AS treatments;
"
# Expected:
#  patients | doctors | appointments | treatments
# ----------+---------+--------------+------------
#    9xxx   |   80    |    54xxx     |   17xxx

---

# ════════════════════════════════════════════════
# PART D — Google Sheets (Step 4) — SKIP FOR NOW
# ════════════════════════════════════════════════

# Google Sheets requires API credentials setup (10-15 min).
# The pipeline will SKIP it gracefully and continue to Step 5.
# Come back to this after everything else is working.
# See the Google Sheets section at the bottom of this file.

---

# ════════════════════════════════════════════════
# PART E — Run ML Model (Step 5) standalone
# ════════════════════════════════════════════════

python src/ml/no_show_prediction.py
# Expected (runs in ~30-60 seconds):
#   [INFO] Loading feature data from v_no_show_risk_features...
#   [INFO]   → 35,xxx rows loaded
#   [INFO]   Class distribution: {0: 29xxx, 1: 6xxx}
#   [INFO] Training Random Forest...
#   ──────────────────────────────────────────────────
#     Random Forest
#   ──────────────────────────────────────────────────
#     Accuracy : 0.78xx
#     ROC-AUC  : 0.72xx
#   [INFO] ✅ ML metrics saved to reports/ml_metrics.csv

# If it says "No DB connection — using synthetic data for demo":
# → ETL wasn't run yet. Run Part C first, then retry this.

---

# ════════════════════════════════════════════════
# PART F — Run the FULL pipeline
# ════════════════════════════════════════════════

# After completing Parts A, B, C above:
python automation/scheduler.py --once

# Expected full output:
#   ============================================================
#   🏥 DAILY PIPELINE — 2026-XX-XX HH:MM UTC
#   ============================================================
#   ▶ Running: 1. Generate Raw Data
#   ✅ 1. Generate Raw Data — OK (1.6s)
#   ▶ Running: 2. Data Quality Checks
#   ✅ 2. Data Quality Checks — OK (0.9s)
#   ▶ Running: 3. ETL → PostgreSQL
#   ✅ 3. ETL → PostgreSQL — OK (25s)
#   ▶ Running: 4. Google Sheets Update
#   ❌ 4. Google Sheets Update — FAILED   ← OK to ignore until configured
#   ▶ Running: 5. ML No-show Model
#   ✅ 5. ML No-show Model — OK (45s)
#   ============================================================
#   Pipeline summary:
#     ✅ OK  1. Generate Raw Data
#     ✅ OK  2. Data Quality Checks
#     ✅ OK  3. ETL → PostgreSQL
#     ❌ FAILED  4. Google Sheets Update   ← expected until API set up
#     ✅ OK  5. ML No-show Model

---

# ════════════════════════════════════════════════
# PART G — Start Metabase
# ════════════════════════════════════════════════

docker run -d `
  --name hospital-metabase `
  -p 3000:3000 `
  metabase/metabase:latest

# Wait 60-90 seconds (Java is slow to start), then open:
# http://localhost:3000

# Setup wizard:
#   1. Language: English
#   2. Create admin account: use any email + password (it's local only)
#   3. "Add your data":
#       Database type: PostgreSQL
#       Display name:  Hospital Analytics
#       Host:          host.docker.internal    ← NOT localhost!
#       Port:          5432
#       Database name: hospital_analytics
#       Username:      postgres
#       Password:      postgres
#   4. Click "Connect" → success
#   5. Finish setup

# Test it: New → SQL Query → paste this:
# SELECT department, total_revenue FROM v_department_performance ORDER BY total_revenue DESC;
# Click Run → you should see your departments with revenue numbers.

# ── TROUBLESHOOTING: Metabase can't connect to PostgreSQL ─────────────────────
# Error: "Connection refused" in Metabase setup
# Cause: "localhost" inside a Docker container means the container itself, not your PC.
# Fix: Use "host.docker.internal" as the host — this is a special Docker DNS name
#      that points from inside a container back to your Windows/Mac host machine.
# On Linux: use your machine's local IP instead (usually 172.17.0.1)
#   Find it with: docker inspect hospital-postgres | grep IPAddress

# ── TROUBLESHOOTING: Metabase stuck on loading screen ─────────────────────────
# It just needs more time. Wait 2 minutes, then refresh the browser.
# Check if it's ready: docker logs hospital-metabase 2>&1 | tail -5
# When you see "Metabase Initialization COMPLETE", it's ready.

---

# ════════════════════════════════════════════════
# PART H — Connect DBeaver (optional but useful)
# ════════════════════════════════════════════════

# DBeaver lets you browse tables and run SQL queries visually.
# Download: https://dbeaver.io/download (Community Edition, free)

# After installing, create a new connection:
#   File → New Database Connection → PostgreSQL → Next
#   Host:     localhost
#   Port:     5432
#   Database: hospital_analytics
#   Username: postgres
#   Password: postgres
#   → Test Connection → Finish

# You can now:
#   - Browse all tables in the left panel
#   - Open SQL editor: right-click database → SQL Editor
#   - Run any query from sql/analytics/02_analytics_queries.sql

---

# ════════════════════════════════════════════════
# PART I — Google Sheets Setup (when ready)
# ════════════════════════════════════════════════

# Step 1: Go to https://console.cloud.google.com
# Step 2: Top left dropdown → "New Project" → name it "hospital-analytics" → Create
# Step 3: With the project selected, search "Google Sheets API" → Enable
# Step 4: Search "Google Drive API" → Enable
# Step 5: Left sidebar → IAM & Admin → Service Accounts → + Create Service Account
#           Name: hospital-sheets-bot → Create and Continue → Done
# Step 6: Click on the service account → Keys tab → Add Key → Create new key → JSON
#           A .json file downloads automatically
# Step 7: Rename it to gsheets_key.json
# Step 8: Create a "credentials" folder in hospital_analytics/:
#           mkdir credentials
# Step 9: Move gsheets_key.json into hospital_analytics/credentials/
# Step 10: Go to https://sheets.google.com → create a blank sheet
# Step 11: Copy the ID from the URL:
#           https://docs.google.com/spreadsheets/d/THIS_IS_THE_ID/edit
# Step 12: Click Share → paste the service account email
#           (from the JSON file, field "client_email") → Editor → Share
# Step 13: Set the environment variable in PowerShell:
#           $env:SPREADSHEET_ID = "paste_your_sheet_id_here"
# Step 14: Run:
#           python src/sheets/sheets_kpi_update.py
# Step 15: Open your Google Sheet — 5 tabs of KPI data should be there!

---

# ════════════════════════════════════════════════
# DAILY USAGE — after everything is set up
# ════════════════════════════════════════════════

# Every time you restart your PC, Docker containers stop.
# To start them again:
docker start hospital-postgres
docker start hospital-metabase

# Then run the pipeline:
cd C:\path\to\hospital_analytics
python automation/scheduler.py --once

# To stop when done:
docker stop hospital-postgres hospital-metabase

---

# ════════════════════════════════════════════════
# QUICK REFERENCE — all useful commands
# ════════════════════════════════════════════════

# See running containers:        docker ps
# See ALL containers (stopped):  docker ps -a
# Start a container:             docker start hospital-postgres
# Stop a container:              docker stop hospital-postgres
# See container logs:            docker logs hospital-postgres
# Delete a container:            docker rm -f hospital-postgres
# Connect to postgres directly:  docker exec -it hospital-postgres psql -U postgres -d hospital_analytics
# List tables in psql:           \dt
# Exit psql:                     \q
