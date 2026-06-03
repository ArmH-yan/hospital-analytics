-- ===========================================================================
-- Hospital Operations Analytics — PostgreSQL Schema
-- ===========================================================================

-- -- 0. Extensions ------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- fuzzy text search on names

-- -- 1. Core Tables -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS patients (
    patient_id        VARCHAR(12)  PRIMARY KEY,
    age               SMALLINT     CHECK (age BETWEEN 1 AND 120),
    gender            VARCHAR(10)  NOT NULL CHECK (gender IN ('Male','Female')),
    city              VARCHAR(60),
    registration_date DATE         NOT NULL DEFAULT CURRENT_DATE,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE patients IS 'Core patient master table. One row per unique patient.';


CREATE TABLE IF NOT EXISTS doctors (
    doctor_id   VARCHAR(8)   PRIMARY KEY,
    doctor_name VARCHAR(100) NOT NULL,
    gender      VARCHAR(10)  NOT NULL CHECK (gender IN ('Male','Female')),
    specialty   VARCHAR(60)  NOT NULL,
    department  VARCHAR(80)  NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE doctors IS 'Doctor registry with specialty and department mapping.';


CREATE TABLE IF NOT EXISTS appointments (
    appointment_id      VARCHAR(12)    PRIMARY KEY,
    patient_id          VARCHAR(12)    REFERENCES patients(patient_id) ON DELETE SET NULL,
    doctor_id           VARCHAR(8)     REFERENCES doctors(doctor_id)   ON DELETE SET NULL,
    appointment_date    DATE           NOT NULL,
    appointment_status  VARCHAR(20)    NOT NULL
                        CHECK (appointment_status IN ('Completed','No-show','Cancelled','Rescheduled')),
    waiting_time_minutes SMALLINT      CHECK (waiting_time_minutes >= 0),
    appointment_cost    NUMERIC(10,2)  CHECK (appointment_cost >= 0),
    created_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE appointments IS 'All patient–doctor appointment records.';


CREATE TABLE IF NOT EXISTS treatments (
    treatment_id    VARCHAR(10)   PRIMARY KEY,
    patient_id      VARCHAR(12)   REFERENCES patients(patient_id) ON DELETE SET NULL,
    diagnosis       VARCHAR(100),
    treatment_type  VARCHAR(60)   NOT NULL
                    CHECK (treatment_type IN (
                        'Surgery','Medication','Physiotherapy','Chemotherapy',
                        'Radiation','Counseling','Observation','Diagnostic Imaging'
                    )),
    treatment_cost  NUMERIC(10,2) CHECK (treatment_cost >= 0),
    treatment_date  DATE          NOT NULL
                    CHECK (treatment_date <= CURRENT_DATE),
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE treatments IS 'Diagnosis and treatment records per patient.';


CREATE TABLE IF NOT EXISTS resources (
    resource_id           SERIAL       PRIMARY KEY,
    department            VARCHAR(80)  NOT NULL,
    available_beds        SMALLINT     NOT NULL CHECK (available_beds >= 0),
    occupied_beds         SMALLINT     NOT NULL CHECK (occupied_beds >= 0),
    total_beds            SMALLINT     GENERATED ALWAYS AS (available_beds + occupied_beds) STORED,
    staff_count           SMALLINT     NOT NULL CHECK (staff_count >= 0),
    equipment_utilization NUMERIC(4,2) NOT NULL CHECK (equipment_utilization BETWEEN 0 AND 1),
    snapshot_date         DATE         NOT NULL DEFAULT CURRENT_DATE,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE resources IS 'Daily snapshot of department resource utilization.';


CREATE TABLE IF NOT EXISTS quality_report (
    id            SERIAL       PRIMARY KEY,
    table_name    VARCHAR(50)  NOT NULL,
    check_name    VARCHAR(100) NOT NULL,
    column_name   VARCHAR(60),
    severity      VARCHAR(10)  NOT NULL CHECK (severity IN ('HIGH','MEDIUM','LOW')),
    issues_found  INTEGER      NOT NULL DEFAULT 0,
    total_rows    INTEGER      NOT NULL,
    pct_affected  NUMERIC(6,3),
    detail        TEXT,
    checked_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE quality_report IS 'Automated data quality audit log.';


-- -- 2. Indexes ----------------------------------------------------------------

-- Appointments — most queried table
CREATE INDEX IF NOT EXISTS idx_apt_patient_id    ON appointments(patient_id);
CREATE INDEX IF NOT EXISTS idx_apt_doctor_id     ON appointments(doctor_id);
CREATE INDEX IF NOT EXISTS idx_apt_date          ON appointments(appointment_date);
CREATE INDEX IF NOT EXISTS idx_apt_status        ON appointments(appointment_status);
CREATE INDEX IF NOT EXISTS idx_apt_date_status   ON appointments(appointment_date, appointment_status);

-- Treatments
CREATE INDEX IF NOT EXISTS idx_trt_patient_id    ON treatments(patient_id);
CREATE INDEX IF NOT EXISTS idx_trt_date          ON treatments(treatment_date);
CREATE INDEX IF NOT EXISTS idx_trt_diagnosis     ON treatments(diagnosis);

-- Patients
CREATE INDEX IF NOT EXISTS idx_pat_city          ON patients(city);
CREATE INDEX IF NOT EXISTS idx_pat_reg_date      ON patients(registration_date);
CREATE INDEX IF NOT EXISTS idx_pat_gender        ON patients(gender);

-- Resources
CREATE INDEX IF NOT EXISTS idx_res_department    ON resources(department);
CREATE INDEX IF NOT EXISTS idx_res_snapshot_date ON resources(snapshot_date);

-- GiST index for fuzzy doctor name search
CREATE INDEX IF NOT EXISTS idx_doc_name_trgm     ON doctors USING GIN (doctor_name gin_trgm_ops);


-- -- 3. Views ------------------------------------------------------------------

CREATE OR REPLACE VIEW v_appointment_detail AS
SELECT
    a.appointment_id,
    a.appointment_date,
    a.appointment_status,
    a.waiting_time_minutes,
    a.appointment_cost,
    p.patient_id,
    p.age,
    p.gender,
    p.city,
    d.doctor_id,
    d.doctor_name,
    d.specialty,
    d.department
FROM appointments a
LEFT JOIN patients p ON a.patient_id = p.patient_id
LEFT JOIN doctors  d ON a.doctor_id  = d.doctor_id;

COMMENT ON VIEW v_appointment_detail IS 'Flat view joining appointments with patient and doctor details.';


CREATE OR REPLACE VIEW v_monthly_kpis AS
SELECT
    DATE_TRUNC('month', appointment_date)::DATE          AS month,
    COUNT(*)                                              AS total_appointments,
    COUNT(*) FILTER (WHERE appointment_status = 'Completed') AS completed,
    COUNT(*) FILTER (WHERE appointment_status = 'No-show')   AS no_shows,
    COUNT(*) FILTER (WHERE appointment_status = 'Cancelled')  AS cancelled,
    ROUND(
        COUNT(*) FILTER (WHERE appointment_status = 'No-show')::NUMERIC
        / NULLIF(COUNT(*), 0) * 100, 2
    )                                                     AS no_show_rate_pct,
    ROUND(AVG(appointment_cost) FILTER (WHERE appointment_status = 'Completed'), 2) AS avg_revenue,
    ROUND(SUM(appointment_cost) FILTER (WHERE appointment_status = 'Completed'), 2) AS total_revenue,
    ROUND(AVG(waiting_time_minutes), 1)                  AS avg_wait_minutes
FROM appointments
GROUP BY DATE_TRUNC('month', appointment_date)
ORDER BY month;

COMMENT ON VIEW v_monthly_kpis IS 'Monthly KPI summary for executive reporting.';


CREATE OR REPLACE VIEW v_department_performance AS
SELECT
    d.department,
    COUNT(a.appointment_id)                               AS total_appointments,
    COUNT(*) FILTER (WHERE a.appointment_status = 'Completed') AS completed,
    COUNT(*) FILTER (WHERE a.appointment_status = 'No-show')   AS no_shows,
    ROUND(
        COUNT(*) FILTER (WHERE a.appointment_status = 'No-show')::NUMERIC
        / NULLIF(COUNT(*), 0) * 100, 2
    )                                                     AS no_show_rate_pct,
    ROUND(SUM(a.appointment_cost) FILTER (WHERE a.appointment_status = 'Completed'), 2) AS total_revenue,
    ROUND(AVG(a.waiting_time_minutes), 1)                AS avg_wait_minutes,
    COUNT(DISTINCT a.patient_id)                         AS unique_patients
FROM appointments a
JOIN doctors d ON a.doctor_id = d.doctor_id
GROUP BY d.department;

COMMENT ON VIEW v_department_performance IS 'Per-department KPIs: revenue, no-show rate, avg wait.';


CREATE OR REPLACE VIEW v_no_show_risk_features AS
-- Feature table for ML no-show prediction
SELECT
    a.appointment_id,
    a.patient_id,
    p.age,
    d.department,
    EXTRACT(DOW FROM a.appointment_date)::SMALLINT   AS appointment_weekday,
    a.appointment_date - p.registration_date         AS days_since_registration,
    COUNT(prev.appointment_id) FILTER (
        WHERE prev.appointment_status = 'No-show'
          AND prev.appointment_date < a.appointment_date
    )                                                AS prior_no_shows,
    COUNT(prev.appointment_id) FILTER (
        WHERE prev.appointment_date < a.appointment_date
    )                                                AS prior_total_appointments,
    CASE WHEN a.appointment_status = 'No-show' THEN 1 ELSE 0 END AS no_show
FROM appointments a
JOIN patients p ON a.patient_id = p.patient_id
JOIN doctors  d ON a.doctor_id  = d.doctor_id
LEFT JOIN appointments prev ON a.patient_id = prev.patient_id
WHERE a.appointment_status IN ('Completed', 'No-show')
GROUP BY
    a.appointment_id, a.patient_id, p.age, d.department,
    a.appointment_date, p.registration_date, a.appointment_status;


-- -- 4. Materialized Views -----------------------------------------------------

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_monthly_revenue AS
SELECT
    DATE_TRUNC('month', a.appointment_date)::DATE   AS month,
    d.department,
    COUNT(a.appointment_id)                          AS total_appointments,
    ROUND(SUM(a.appointment_cost)
          FILTER (WHERE a.appointment_status = 'Completed'), 2) AS appointment_revenue,
    ROUND(SUM(t.treatment_cost), 2)                  AS treatment_revenue,
    ROUND(
        COALESCE(SUM(a.appointment_cost) FILTER (WHERE a.appointment_status = 'Completed'), 0)
        + COALESCE(SUM(t.treatment_cost), 0), 2
    )                                                AS total_revenue
FROM appointments a
JOIN doctors  d ON a.doctor_id  = d.doctor_id
LEFT JOIN treatments t ON a.patient_id = t.patient_id
    AND DATE_TRUNC('month', t.treatment_date) = DATE_TRUNC('month', a.appointment_date)
GROUP BY DATE_TRUNC('month', a.appointment_date), d.department
ORDER BY month, total_revenue DESC
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_monthly_revenue
    ON mv_monthly_revenue (month, department);

COMMENT ON MATERIALIZED VIEW mv_monthly_revenue
    IS 'Pre-aggregated monthly revenue by department. Refresh nightly.';


CREATE MATERIALIZED VIEW IF NOT EXISTS mv_doctor_performance AS
SELECT
    d.doctor_id,
    d.doctor_name,
    d.specialty,
    d.department,
    COUNT(a.appointment_id)                                     AS total_appointments,
    COUNT(*) FILTER (WHERE a.appointment_status = 'Completed') AS completed,
    COUNT(*) FILTER (WHERE a.appointment_status = 'No-show')   AS no_shows,
    ROUND(
        COUNT(*) FILTER (WHERE a.appointment_status = 'No-show')::NUMERIC
        / NULLIF(COUNT(*), 0) * 100, 2
    )                                                           AS no_show_rate_pct,
    ROUND(AVG(a.waiting_time_minutes), 1)                      AS avg_wait_minutes,
    ROUND(SUM(a.appointment_cost)
          FILTER (WHERE a.appointment_status = 'Completed'), 2) AS total_revenue,
    COUNT(DISTINCT a.patient_id)                               AS unique_patients
FROM doctors d
LEFT JOIN appointments a ON d.doctor_id = a.doctor_id
GROUP BY d.doctor_id, d.doctor_name, d.specialty, d.department
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_doctor_perf
    ON mv_doctor_performance (doctor_id);

COMMENT ON MATERIALIZED VIEW mv_doctor_performance
    IS 'Pre-aggregated doctor performance KPIs. Refresh nightly.';


-- -- 5. Refresh helper ---------------------------------------------------------
-- Run this nightly after ETL load:
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_monthly_revenue;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_doctor_performance;
