# Power BI Dashboard — Design Specification & DAX Measures

## Overview
4 dashboard pages connecting to PostgreSQL via DirectQuery or imported CSV.
Data source: PostgreSQL views (`v_appointment_detail`, `v_monthly_kpis`,
`mv_monthly_revenue`, `mv_doctor_performance`, `v_department_performance`, `resources`).

---

## Page 1 — Executive Dashboard

### Visuals
| Visual | Type | Fields |
|--------|------|--------|
| Total Revenue | Card | [Total Revenue] |
| Total Patients | Card | [Total Patients] |
| Total Appointments | Card | [Total Appointments] |
| No-show Rate | Card | [No-show Rate %] |
| Avg Occupancy | Card | [Avg Bed Occupancy %] |
| Revenue Trend | Line Chart | month, [Monthly Revenue] |
| Appointments by Status | Donut | appointment_status, Count |
| Top 5 Departments | Bar Chart | department, [Total Revenue] |

---

## Page 2 — Operations Dashboard

| Visual | Type | Fields |
|--------|------|--------|
| Avg Wait Time by Dept | Bar | department, avg_wait_minutes |
| Bed Occupancy by Dept | Clustered Bar | department, occupied_beds, total_beds |
| Equipment Utilization | Gauge | equipment_utilization |
| No-show Heatmap | Matrix | weekday vs department, no_show_rate_pct |
| Resource Status | Table | department, occupancy_pct, capacity_status |

---

## Page 3 — Patient Dashboard

| Visual | Type | Fields |
|--------|------|--------|
| Gender Distribution | Pie | gender, Count |
| Age Distribution | Histogram | age (binned) |
| Patients by City | Map / Bar | city, Count(patient_id) |
| Monthly New Patients | Line | registration_date (month), Count |
| Diagnosis Breakdown | Treemap | diagnosis, Count |

---

## Page 4 — Financial Dashboard

| Visual | Type | Fields |
|--------|------|--------|
| Monthly Revenue | Area Chart | month, [Monthly Revenue] |
| Revenue by Treatment Type | Bar | treatment_type, SUM(treatment_cost) |
| QoQ Growth | Column Chart | quarter, [QoQ Revenue Growth %] |
| Revenue vs No-show Loss | Combo | month, revenue, [Estimated Lost Revenue] |
| Top 10 Revenue Doctors | Bar | doctor_name, [Doctor Revenue] |

---

## DAX Measures

```dax
-- ─── Core Measures ────────────────────────────────────────────────────────

Total Revenue =
CALCULATE(
    SUM(appointments[appointment_cost]),
    appointments[appointment_status] = "Completed"
)

Total Appointments =
COUNTROWS(appointments)

Total Patients =
DISTINCTCOUNT(appointments[patient_id])

Total No-shows =
CALCULATE(
    COUNTROWS(appointments),
    appointments[appointment_status] = "No-show"
)

No-show Rate % =
DIVIDE(
    [Total No-shows],
    [Total Appointments],
    0
) * 100

Avg Waiting Time =
CALCULATE(
    AVERAGE(appointments[waiting_time_minutes]),
    appointments[appointment_status] = "Completed"
)

-- ─── Treatment Revenue ────────────────────────────────────────────────────

Total Treatment Revenue =
SUM(treatments[treatment_cost])

Grand Total Revenue =
[Total Revenue] + [Total Treatment Revenue]

-- ─── Rolling / Time Intelligence ─────────────────────────────────────────

Monthly Revenue =
CALCULATE(
    [Total Revenue],
    DATESMTD(appointments[appointment_date])
)

YTD Revenue =
CALCULATE(
    [Total Revenue],
    DATESYTD(appointments[appointment_date])
)

Revenue MoM Growth % =
VAR CurrentMonth = [Monthly Revenue]
VAR PrevMonth    = CALCULATE(
    [Total Revenue],
    DATEADD(appointments[appointment_date], -1, MONTH)
)
RETURN
DIVIDE(CurrentMonth - PrevMonth, PrevMonth, 0) * 100

Rolling 3M Revenue =
CALCULATE(
    [Total Revenue],
    DATESINPERIOD(
        appointments[appointment_date],
        LASTDATE(appointments[appointment_date]),
        -3, MONTH
    )
)

-- ─── Resource / Operations ────────────────────────────────────────────────

Bed Occupancy % =
DIVIDE(
    SUM(resources[occupied_beds]),
    SUM(resources[total_beds]),
    0
) * 100

Avg Equipment Utilization =
AVERAGE(resources[equipment_utilization]) * 100

-- ─── Estimated No-show Revenue Loss ──────────────────────────────────────

Avg Appointment Value =
DIVIDE([Total Revenue], CALCULATE([Total Appointments], appointments[appointment_status]="Completed"), 0)

Estimated Lost Revenue =
[Total No-shows] * [Avg Appointment Value]

-- ─── Doctor Ranking ───────────────────────────────────────────────────────

Doctor Revenue Rank =
RANKX(
    ALL(mv_doctor_performance[doctor_name]),
    [Total Revenue],
    ,
    DESC, DENSE
)
```

---

## Setup Instructions

1. Open Power BI Desktop.
2. **Get Data → PostgreSQL** → enter host/credentials → select views:
   - `v_appointment_detail`
   - `v_monthly_kpis`
   - `v_department_performance`
   - `mv_monthly_revenue`
   - `mv_doctor_performance`
   - `resources`
3. Use **Import** mode for faster performance (schedule daily refresh).
4. Create a **Date table**: `CALENDARAUTO()` and mark as Date table.
5. Set relationships:
   - `appointments[patient_id]` → `patients[patient_id]`
   - `appointments[doctor_id]`  → `doctors[doctor_id]`
6. Create all DAX measures above in a dedicated "Measures" table.
7. Build pages following the visual spec above.
8. Publish to Power BI Service and set daily scheduled refresh.

---

## Color Theme
```json
{
  "name": "Hospital Analytics",
  "dataColors": ["#1A6FA8","#2ECC71","#E74C3C","#F39C12","#9B59B6","#1ABC9C"],
  "background": "#FFFFFF",
  "foreground": "#2C3E50",
  "tableAccent": "#1A6FA8"
}
```
Save as `.json` and import via View → Themes → Browse for themes.
