# Power BI Dashboard — Chart Inventory

This document catalogs every visual in `dashboards/hospital_analytics.pbix`
exactly as it is built in the file. It is the operational counterpart to
[`POWERBI_SPEC.md`](POWERBI_SPEC.md), which describes the design intent and
contains the DAX measure library.

---

## File Metadata

| Property | Value |
|----------|-------|
| File | `dashboards/hospital_analytics.pbix` |
| Power BI version | 1.28 |
| Theme | Storm (built-in) |
| Total pages | 3 |
| Total visuals | 11 |

---

## Data Sources

The report reads from PostgreSQL via Import mode and a mix of native SQL
queries. Each visual is bound directly to one of the following.

| Source | Type | Used by |
|--------|------|---------|
| `public v_department_performance` | View | Page 1 — Revenue card |
| `public v_appointment_detail` | View | Page 1 cards · Page 2 age chart |
| `mv_monthly_revenue` | Materialized view | Page 1 revenue trend |
| `mv_doctor_performance` | Materialized view | Page 2 doctor table |
| `public resources` | Table | Page 3 equipment gauge |
| `department_rev_sql` | Native SQL query | Page 1 — Revenue by Department |
| `nsr_by_dep_sql` | Native SQL query | Page 1 — No-show Rate by Department |
| `appointment_status_sql` | Native SQL query | Page 2 — Status donut |
| `Query1` | Native SQL query | Page 3 — Bed Occupancy |

---

## Page 1 — Executive Overview

KPI cards plus revenue trend and department-level breakdowns.

| # | Visual | Type | Fields / Measure | Source |
|---|--------|------|------------------|--------|
| 1 | Revenue | Card | `SUM(total_revenue)` | `v_department_performance` |
| 2 | Appts | Card | `COUNT(appointment_id)` | `v_appointment_detail` |
| 3 | Patients | Card | `COUNT(patient_id)` (distinct) | `v_appointment_detail` |
| 4 | Revenue Over Time | Area chart | `total_revenue` × Date Hierarchy (Year → Quarter → Month → Day), split by `department` | `mv_monthly_revenue` |
| 5 | Revenue by Department | Clustered bar | `department`, `SUM(revenue)` — sorted descending | `department_rev_sql` |
| 6 | No-show Rate by Department | Column chart | `department`, `SUM(no_show_pct)` — sorted descending | `nsr_by_dep_sql` |

---

## Page 2 — Patient & Doctor Analysis

Patient demographics, appointment status mix, and a doctor performance
leaderboard.

| # | Visual | Type | Fields / Measure | Source |
|---|--------|------|------------------|--------|
| 1 | Patient Age Distribution | Clustered column | `age (bins)`, `COUNT(patient_id)` — sorted descending | `v_appointment_detail` |
| 2 | Appointment Status Breakdown | Donut | `appointment_status`, `SUM(total)` | `appointment_status_sql` |
| 3 | Doctor Performance Table | Table | `doctor_name`, `department`, `total_revenue`, `no_show_rate_pct`, `avg_wait_minutes` — sorted by `total_revenue` desc | `mv_doctor_performance` |

---

## Page 3 — Resource Utilization

Operational view of physical resources: equipment and bed capacity.

| # | Visual | Type | Fields / Measure | Source |
|---|--------|------|------------------|--------|
| 1 | Equipment Utilization Gauge | Gauge | `AVERAGE(equipment_utilization)` | `resources` |
| 2 | Bed Occupancy by Department | 100% stacked bar | `department`, `occupied_beds`, `available_beds` — sorted by available beds desc | `Query1` |

---

## Notes

This report reflects the 3 pages currently built in the `.pbix` file.
[`POWERBI_SPEC.md`](POWERBI_SPEC.md) describes a 4th **Financial Dashboard**
page (Monthly Revenue area, Revenue by Treatment Type, QoQ Growth, Revenue
vs No-show Loss combo, Top 10 Revenue Doctors) that is documented in the
spec but is not yet present in the saved file.

If/when that page is added, append it here with the same table format used
above and bump the totals in the *File Metadata* section.

---

## See Also

- [`POWERBI_SPEC.md`](POWERBI_SPEC.md) — design spec, full DAX measure
  library, color theme, and setup instructions.
- `../hospital_analytics.pbix` — the report file itself.
