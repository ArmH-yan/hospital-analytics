# Metabase Dashboard — Setup & Dashboard Specification

## Local Setup (Docker — recommended)

```bash
# 1. Pull and run Metabase with your PostgreSQL
docker run -d \
  --name hospital-metabase \
  -p 3000:3000 \
  -e MB_DB_TYPE=postgres \
  -e MB_DB_DBNAME=hospital_analytics \
  -e MB_DB_PORT=5432 \
  -e MB_DB_USER=postgres \
  -e MB_DB_PASS=postgres \
  -e MB_DB_HOST=host.docker.internal \
  metabase/metabase:latest

# 2. Open http://localhost:3000
# 3. Admin setup wizard → connect to your PostgreSQL
# 4. Sync database tables
```

---

## Dashboard 1 — Executive Summary

**Questions to create:**

### Q1 — Total Revenue (Metric)
```sql
SELECT ROUND(SUM(appointment_cost), 2) AS total_revenue
FROM appointments
WHERE appointment_status = 'Completed'
```
Display as: **Big Number**

### Q2 — Monthly Revenue Trend
```sql
SELECT
    DATE_TRUNC('month', appointment_date)::DATE AS month,
    ROUND(SUM(appointment_cost), 2)             AS revenue
FROM appointments
WHERE appointment_status = 'Completed'
GROUP BY 1
ORDER BY 1
```
Display as: **Line Chart**

### Q3 — Appointments by Status
```sql
SELECT appointment_status, COUNT(*) AS count
FROM appointments
GROUP BY appointment_status
ORDER BY count DESC
```
Display as: **Pie Chart** or **Row Chart**

### Q4 — No-show Rate
```sql
SELECT
    ROUND(
        COUNT(*) FILTER (WHERE appointment_status = 'No-show')::NUMERIC
        / NULLIF(COUNT(*), 0) * 100, 2
    ) AS no_show_rate_pct
FROM appointments
```
Display as: **Big Number** with goal line at 15%

### Q5 — Revenue by Department (Top 10)
```sql
SELECT department, total_revenue
FROM v_department_performance
ORDER BY total_revenue DESC
LIMIT 10
```
Display as: **Bar Chart**

---

## Dashboard 2 — Operations & Resources

### Q6 — Bed Occupancy by Department
```sql
SELECT
    department,
    occupied_beds,
    total_beds,
    ROUND(occupied_beds::NUMERIC / NULLIF(total_beds,0) * 100, 2) AS occupancy_pct
FROM resources
ORDER BY occupancy_pct DESC
```
Display as: **Progress bars** or **Bar Chart**

### Q7 — Average Waiting Time by Department
```sql
SELECT
    d.department,
    ROUND(AVG(a.waiting_time_minutes), 1) AS avg_wait_minutes
FROM appointments a
JOIN doctors d ON a.doctor_id = d.doctor_id
WHERE a.appointment_status = 'Completed'
GROUP BY d.department
ORDER BY avg_wait_minutes DESC
```
Display as: **Bar Chart**

### Q8 — No-show Heatmap by Weekday
```sql
SELECT
    TO_CHAR(appointment_date, 'Day')             AS weekday,
    EXTRACT(DOW FROM appointment_date)::INT       AS weekday_num,
    COUNT(*)                                      AS total,
    COUNT(*) FILTER (WHERE appointment_status = 'No-show') AS no_shows,
    ROUND(
        COUNT(*) FILTER (WHERE appointment_status = 'No-show')::NUMERIC
        / NULLIF(COUNT(*), 0) * 100, 2
    ) AS no_show_rate_pct
FROM appointments
GROUP BY 1, 2
ORDER BY 2
```
Display as: **Table** with color conditional formatting

---

## Dashboard 3 — Doctor Performance

### Q9 — Doctor Leaderboard
```sql
SELECT doctor_name, department, total_appointments,
       no_show_rate_pct, total_revenue, avg_wait_minutes
FROM mv_doctor_performance
ORDER BY total_revenue DESC
LIMIT 20
```
Display as: **Table**

### Q10 — Doctor Revenue by Specialty
```sql
SELECT specialty, ROUND(SUM(total_revenue), 2) AS revenue
FROM mv_doctor_performance
GROUP BY specialty
ORDER BY revenue DESC
```
Display as: **Bar Chart**

---

## Adding Filters

On each dashboard, add these **Filter widgets**:
- **Date Range** → `appointment_date`
- **Department** → `department`
- **Status** → `appointment_status`

This creates self-service dashboards that non-technical users can filter on their own —
exactly matching the "self-service dashboards" requirement in the BostonGene job listing.

---

## Metabase Tips for Portfolio

1. **Take screenshots** of each dashboard for your README.
2. **Record a 2-min Loom/OBS demo** — it shows Metabase live better than screenshots.
3. In your README, write: *"Built Metabase dashboards on top of PostgreSQL views,
   enabling clinical teams to self-serve data without writing SQL."*
4. Add a `docs/metabase_requirements.md` with user story:
   > "As a department head, I want to see my team's no-show rate and revenue
   >  without asking the data team for a report."
