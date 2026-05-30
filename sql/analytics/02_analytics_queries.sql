-- ═══════════════════════════════════════════════════════════════════════════
-- Hospital Analytics — Business SQL Queries (20+)
-- ═══════════════════════════════════════════════════════════════════════════

-- ── Q01. Top 10 Departments by Total Revenue ─────────────────────────────────
SELECT
    department,
    total_revenue,
    RANK() OVER (ORDER BY total_revenue DESC) AS revenue_rank
FROM v_department_performance
ORDER BY total_revenue DESC
LIMIT 10;


-- ── Q02. Monthly Patient Growth with MoM % Change ────────────────────────────
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', registration_date)::DATE AS month,
        COUNT(*) AS new_patients
    FROM patients
    GROUP BY 1
)
SELECT
    month,
    new_patients,
    SUM(new_patients) OVER (ORDER BY month ROWS UNBOUNDED PRECEDING) AS cumulative_patients,
    ROUND(
        (new_patients - LAG(new_patients) OVER (ORDER BY month))::NUMERIC
        / NULLIF(LAG(new_patients) OVER (ORDER BY month), 0) * 100, 2
    ) AS mom_growth_pct
FROM monthly
ORDER BY month;


-- ── Q03. No-Show Rate by Department and Weekday ───────────────────────────────
SELECT
    d.department,
    TO_CHAR(a.appointment_date, 'Day')               AS weekday,
    EXTRACT(DOW FROM a.appointment_date)::INT         AS weekday_num,
    COUNT(*)                                          AS total_appointments,
    COUNT(*) FILTER (WHERE a.appointment_status = 'No-show') AS no_shows,
    ROUND(
        COUNT(*) FILTER (WHERE a.appointment_status = 'No-show')::NUMERIC
        / NULLIF(COUNT(*), 0) * 100, 2
    )                                                 AS no_show_rate_pct
FROM appointments a
JOIN doctors d ON a.doctor_id = d.doctor_id
GROUP BY d.department, TO_CHAR(a.appointment_date, 'Day'),
         EXTRACT(DOW FROM a.appointment_date)
ORDER BY no_show_rate_pct DESC;


-- ── Q04. Doctor Performance Ranking (Revenue + No-show Rate) ─────────────────
SELECT
    doctor_name,
    department,
    total_appointments,
    no_show_rate_pct,
    total_revenue,
    avg_wait_minutes,
    RANK() OVER (PARTITION BY department ORDER BY total_revenue DESC) AS dept_revenue_rank,
    NTILE(4) OVER (ORDER BY no_show_rate_pct ASC)                    AS no_show_quartile
FROM mv_doctor_performance
ORDER BY total_revenue DESC;


-- ── Q05. 3-Month Rolling Average Revenue per Department ──────────────────────
SELECT
    month,
    department,
    total_revenue,
    ROUND(
        AVG(total_revenue) OVER (
            PARTITION BY department
            ORDER BY month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 2
    ) AS rolling_3m_revenue
FROM mv_monthly_revenue
ORDER BY department, month;


-- ── Q06. Patient Retention Cohort Analysis ───────────────────────────────────
-- Which registration cohorts return for subsequent appointments?
WITH cohorts AS (
    SELECT
        patient_id,
        DATE_TRUNC('quarter', registration_date)::DATE AS cohort_quarter
    FROM patients
),
activity AS (
    SELECT
        a.patient_id,
        DATE_TRUNC('quarter', a.appointment_date)::DATE AS activity_quarter
    FROM appointments a
    WHERE a.appointment_status = 'Completed'
)
SELECT
    c.cohort_quarter,
    a.activity_quarter,
    DATE_PART('quarter', AGE(a.activity_quarter::DATE, c.cohort_quarter::DATE))
    + DATE_PART('year', AGE(a.activity_quarter::DATE, c.cohort_quarter::DATE)) * 4
                                                        AS quarters_since_reg,
    COUNT(DISTINCT c.patient_id)                        AS active_patients
FROM cohorts c
JOIN activity a USING (patient_id)
WHERE a.activity_quarter >= c.cohort_quarter
GROUP BY 1, 2, 3
ORDER BY 1, 3;


-- ── Q07. Average Waiting Time Trend (30-day rolling) ─────────────────────────
SELECT
    appointment_date,
    ROUND(AVG(waiting_time_minutes), 1)                 AS daily_avg_wait,
    ROUND(
        AVG(AVG(waiting_time_minutes)) OVER (
            ORDER BY appointment_date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ), 1
    )                                                   AS rolling_30d_avg_wait
FROM appointments
WHERE appointment_status = 'Completed'
GROUP BY appointment_date
ORDER BY appointment_date;


-- ── Q08. Bed Occupancy Rate by Department ────────────────────────────────────
SELECT
    department,
    occupied_beds,
    total_beds,
    ROUND(occupied_beds::NUMERIC / NULLIF(total_beds, 0) * 100, 2) AS occupancy_rate_pct,
    equipment_utilization * 100                                      AS equipment_util_pct,
    staff_count,
    ROUND(occupied_beds::NUMERIC / NULLIF(staff_count, 0), 2)       AS patients_per_staff
FROM resources
ORDER BY occupancy_rate_pct DESC;


-- ── Q09. Top 10 Most Common Diagnoses ────────────────────────────────────────
SELECT
    diagnosis,
    COUNT(*)                                         AS total_cases,
    ROUND(AVG(treatment_cost), 2)                   AS avg_treatment_cost,
    ROUND(SUM(treatment_cost), 2)                   AS total_revenue,
    ROUND(COUNT(*)::NUMERIC / SUM(COUNT(*)) OVER () * 100, 2) AS pct_of_total
FROM treatments
WHERE diagnosis IS NOT NULL
GROUP BY diagnosis
ORDER BY total_cases DESC
LIMIT 10;


-- ── Q10. Revenue vs. No-show Impact Estimation ───────────────────────────────
WITH no_show_loss AS (
    SELECT
        DATE_TRUNC('month', appointment_date)::DATE AS month,
        COUNT(*) FILTER (WHERE appointment_status = 'No-show') AS no_show_count,
        ROUND(AVG(appointment_cost), 2)              AS avg_appointment_cost
    FROM appointments
    GROUP BY 1
)
SELECT
    month,
    no_show_count,
    avg_appointment_cost,
    ROUND(no_show_count * avg_appointment_cost, 2)  AS estimated_revenue_lost
FROM no_show_loss
ORDER BY month;


-- ── Q11. Patients with Multiple Diagnoses (High-complexity Cases) ─────────────
SELECT
    patient_id,
    COUNT(DISTINCT diagnosis) AS distinct_diagnoses,
    COUNT(*)                  AS total_treatments,
    ROUND(SUM(treatment_cost), 2) AS total_spend,
    STRING_AGG(DISTINCT diagnosis, ', ') AS diagnoses_list
FROM treatments
WHERE diagnosis IS NOT NULL
GROUP BY patient_id
HAVING COUNT(DISTINCT diagnosis) >= 3
ORDER BY distinct_diagnoses DESC, total_spend DESC
LIMIT 20;


-- ── Q12. Department Revenue Growth QoQ ────────────────────────────────────────
WITH quarterly AS (
    SELECT
        DATE_TRUNC('quarter', appointment_date)::DATE AS quarter,
        d.department,
        ROUND(SUM(appointment_cost) FILTER (WHERE appointment_status = 'Completed'), 2) AS revenue
    FROM appointments a
    JOIN doctors d ON a.doctor_id = d.doctor_id
    GROUP BY 1, 2
)
SELECT
    quarter,
    department,
    revenue,
    LAG(revenue) OVER (PARTITION BY department ORDER BY quarter) AS prev_quarter_revenue,
    ROUND(
        (revenue - LAG(revenue) OVER (PARTITION BY department ORDER BY quarter))::NUMERIC
        / NULLIF(LAG(revenue) OVER (PARTITION BY department ORDER BY quarter), 0) * 100, 2
    ) AS qoq_growth_pct
FROM quarterly
ORDER BY department, quarter;


-- ── Q13. Patient Age Distribution by Department ───────────────────────────────
SELECT
    d.department,
    WIDTH_BUCKET(p.age, 0, 100, 10) * 10 - 10  AS age_bucket_start,
    WIDTH_BUCKET(p.age, 0, 100, 10) * 10        AS age_bucket_end,
    COUNT(DISTINCT a.patient_id)                 AS patient_count
FROM appointments a
JOIN patients p ON a.patient_id = p.patient_id
JOIN doctors  d ON a.doctor_id  = d.doctor_id
WHERE p.age IS NOT NULL
GROUP BY d.department, WIDTH_BUCKET(p.age, 0, 100, 10)
ORDER BY department, age_bucket_start;


-- ── Q14. Daily New Appointment Bookings (last 90 days) ────────────────────────
SELECT
    appointment_date,
    COUNT(*)                                     AS appointments_booked,
    SUM(COUNT(*)) OVER (
        ORDER BY appointment_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    )                                            AS rolling_7d_bookings
FROM appointments
WHERE appointment_date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY appointment_date
ORDER BY appointment_date;


-- ── Q15. First vs. Return Patient Revenue Split ───────────────────────────────
WITH first_visit AS (
    SELECT
        patient_id,
        MIN(appointment_date) AS first_appointment_date
    FROM appointments
    WHERE appointment_status = 'Completed'
    GROUP BY patient_id
)
SELECT
    CASE WHEN a.appointment_date = f.first_appointment_date
         THEN 'New Patient' ELSE 'Return Patient' END  AS patient_type,
    COUNT(*)                                            AS appointments,
    ROUND(SUM(a.appointment_cost), 2)                  AS total_revenue,
    ROUND(AVG(a.appointment_cost), 2)                  AS avg_revenue_per_visit
FROM appointments a
JOIN first_visit f ON a.patient_id = f.patient_id
WHERE a.appointment_status = 'Completed'
GROUP BY patient_type;


-- ── Q16. Hour-of-Day Appointment Density (simulated from day of week) ─────────
-- Using weekday as a proxy for scheduling density patterns
SELECT
    TO_CHAR(appointment_date, 'Day')          AS weekday,
    EXTRACT(DOW FROM appointment_date)::INT   AS weekday_num,
    COUNT(*)                                   AS total_appointments,
    ROUND(AVG(waiting_time_minutes), 1)        AS avg_wait_minutes,
    ROUND(AVG(appointment_cost), 2)            AS avg_cost
FROM appointments
WHERE appointment_status = 'Completed'
GROUP BY TO_CHAR(appointment_date, 'Day'), EXTRACT(DOW FROM appointment_date)
ORDER BY weekday_num;


-- ── Q17. Treatment Type Revenue Analysis ──────────────────────────────────────
SELECT
    treatment_type,
    COUNT(*)                                   AS total_treatments,
    ROUND(AVG(treatment_cost), 2)             AS avg_cost,
    ROUND(MIN(treatment_cost), 2)             AS min_cost,
    ROUND(MAX(treatment_cost), 2)             AS max_cost,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP
          (ORDER BY treatment_cost)::NUMERIC, 2) AS median_cost,
    ROUND(SUM(treatment_cost), 2)             AS total_revenue,
    RANK() OVER (ORDER BY SUM(treatment_cost) DESC) AS revenue_rank
FROM treatments
GROUP BY treatment_type
ORDER BY total_revenue DESC;


-- ── Q18. Repeat No-show Patients (flag for intervention) ─────────────────────
SELECT
    patient_id,
    COUNT(*) FILTER (WHERE appointment_status = 'No-show')   AS no_show_count,
    COUNT(*)                                                   AS total_appointments,
    ROUND(
        COUNT(*) FILTER (WHERE appointment_status = 'No-show')::NUMERIC
        / COUNT(*) * 100, 2
    )                                                         AS personal_no_show_rate,
    MAX(appointment_date) FILTER (WHERE appointment_status = 'No-show') AS last_no_show_date
FROM appointments
GROUP BY patient_id
HAVING COUNT(*) FILTER (WHERE appointment_status = 'No-show') >= 3
ORDER BY no_show_count DESC
LIMIT 50;


-- ── Q19. Resource Bottleneck Detection ────────────────────────────────────────
SELECT
    r.department,
    r.occupied_beds,
    r.total_beds,
    ROUND(r.occupied_beds::NUMERIC / r.total_beds * 100, 2) AS occupancy_pct,
    r.staff_count,
    COALESCE(dp.total_appointments, 0)                       AS monthly_appointments,
    ROUND(
        COALESCE(dp.total_appointments, 0)::NUMERIC
        / NULLIF(r.staff_count, 0), 2
    )                                                        AS appointments_per_staff,
    CASE
        WHEN r.occupied_beds::NUMERIC / r.total_beds > 0.90 THEN '🔴 CRITICAL'
        WHEN r.occupied_beds::NUMERIC / r.total_beds > 0.75 THEN '🟡 HIGH'
        ELSE '🟢 OK'
    END                                                      AS capacity_status
FROM resources r
LEFT JOIN v_department_performance dp ON r.department = dp.department
ORDER BY occupancy_pct DESC;


-- ── Q20. Executive Summary CTE: Key Hospital KPIs ────────────────────────────
WITH kpis AS (
    SELECT
        COUNT(DISTINCT patient_id)                            AS total_patients,
        COUNT(*)                                              AS total_appointments,
        COUNT(*) FILTER (WHERE appointment_status = 'No-show') AS total_no_shows,
        ROUND(
            COUNT(*) FILTER (WHERE appointment_status = 'No-show')::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 2
        )                                                     AS overall_no_show_rate,
        ROUND(SUM(appointment_cost)
              FILTER (WHERE appointment_status = 'Completed'), 2) AS total_apt_revenue,
        ROUND(AVG(waiting_time_minutes), 1)                   AS avg_wait_minutes
    FROM appointments
),
treatment_kpis AS (
    SELECT
        COUNT(*)                              AS total_treatments,
        ROUND(SUM(treatment_cost), 2)         AS total_treatment_revenue,
        ROUND(AVG(treatment_cost), 2)         AS avg_treatment_cost
    FROM treatments
),
resource_kpis AS (
    SELECT
        ROUND(AVG(occupied_beds::NUMERIC / NULLIF(total_beds, 0)) * 100, 2) AS avg_occupancy_pct,
        ROUND(AVG(equipment_utilization) * 100, 2)                          AS avg_equipment_util_pct
    FROM resources
)
SELECT
    k.*,
    t.total_treatments,
    k.total_apt_revenue + t.total_treatment_revenue AS grand_total_revenue,
    r.avg_occupancy_pct,
    r.avg_equipment_util_pct
FROM kpis k, treatment_kpis t, resource_kpis r;


-- ── Q21. City-Level Patient Volume Map ───────────────────────────────────────
SELECT
    p.city,
    COUNT(DISTINCT p.patient_id)                AS total_patients,
    COUNT(a.appointment_id)                     AS total_appointments,
    ROUND(SUM(a.appointment_cost)
          FILTER (WHERE a.appointment_status = 'Completed'), 2) AS total_revenue,
    ROUND(AVG(p.age), 1)                        AS avg_patient_age
FROM patients p
LEFT JOIN appointments a ON p.patient_id = a.patient_id
GROUP BY p.city
ORDER BY total_patients DESC;
