"""
Hospital Operations Analytics - Synthetic Data Generator
Generates realistic hospital data with intentionally injected data quality issues.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

np.random.seed(142)
random.seed(142)

# ─── Config ───────────────────────────────────────────────────────────────────
N_PATIENTS     = 10_000
N_DOCTORS      = 80
N_APPOINTMENTS = 55_000
N_TREATMENTS   = 18_000
OUTPUT_DIR     = "data/raw"

SPECIALTIES = [
    "Cardiology", "Oncology", "Neurology", "Orthopedics",
    "Pediatrics", "General Medicine", "Emergency", "Radiology",
    "Dermatology", "Psychiatry"
]

DEPARTMENTS = [
    "Cardiology Dept", "Oncology Dept", "Neurology Dept", "Orthopedics Dept",
    "Pediatrics Dept", "General Medicine Dept", "Emergency Dept", "Radiology Dept",
    "Dermatology Dept", "Psychiatry Dept"
]

CITIES = [
    "Yerevan", "Gyumri", "Vanadzor", "Vagharshapat", "Abovyan",
    "Kapan", "Hrazdan", "Charentsavan", "Goris", "Ashtarak"
]

GENDERS = ["Male", "Female"]

STATUSES = ["Completed", "No-show", "Cancelled", "Rescheduled"]

DIAGNOSES = [
    "Hypertension", "Diabetes Type 2", "Coronary Artery Disease", "Lung Cancer",
    "Breast Cancer", "Stroke", "Fracture", "Appendicitis", "Pneumonia",
    "Depression", "Anxiety", "Migraine", "Arthritis", "Asthma", "Obesity",
    "Kidney Disease", "Liver Disease", "Anemia", "Thyroid Disorder", "Skin Infection"
]

TREATMENT_TYPES = [
    "Surgery", "Medication", "Physiotherapy", "Chemotherapy",
    "Radiation", "Counseling", "Observation", "Diagnostic Imaging"
]


def generate_patients(n: int) -> pd.DataFrame:
    logger.info(f"Generating {n} patients...")
    ids = [f"PAT{str(i).zfill(6)}" for i in range(1, n + 1)]
    ages = np.random.normal(loc=45, scale=18, size=n).astype(int).clip(1, 100)
    genders = np.random.choice(GENDERS, size=n, p=[0.48, 0.52])
    cities = np.random.choice(CITIES, size=n)
    reg_dates = [
        datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1460))
        for _ in range(n)
    ]

    df = pd.DataFrame({
        "patient_id": ids,
        "age": ages,
        "gender": genders,
        "city": cities,
        "registration_date": reg_dates
    })

    # --- Inject quality issues ---
    # Null ages (~1%)
    df.loc[df.sample(frac=0.01).index, "age"] = np.nan
    # Negative ages (~0.3%)
    df.loc[df.sample(frac=0.003).index, "age"] = -random.randint(1, 5)
    # Null gender (~0.5%)
    df.loc[df.sample(frac=0.005).index, "gender"] = np.nan
    # Invalid gender (~0.2%) — leftover from old 'Other' era
    df.loc[df.sample(frac=0.002).index, "gender"] = "Unknown_XYZ"
    # Duplicate rows (~0.5%)
    dupes = df.sample(frac=0.005)
    df = pd.concat([df, dupes], ignore_index=True)

    logger.info(f"  → {len(df)} rows (including {len(dupes)} injected duplicates)")
    return df


MALE_FIRST_NAMES = [
    "Armen", "Davit", "Hovhannes", "Vahe", "Tigran",
    "Aram", "Hayk", "Narek", "Mkrtich", "Artur"
]

FEMALE_FIRST_NAMES = [
    "Ani", "Nare", "Lilit", "Mariam", "Sona",
    "Tatevik", "Lusine", "Astghik", "Diana", "Nune"
]

LAST_NAMES = [
    "Sargsyan", "Petrosyan", "Hovhannisyan", "Grigoryan",
    "Harutyunyan", "Mkrtchyan", "Karapetyan", "Ghazaryan",
    "Avagyan", "Danielyan"
]


def generate_doctors(n: int) -> pd.DataFrame:
    logger.info(f"Generating {n} doctors...")
    ids = [f"DOC{str(i).zfill(4)}" for i in range(1, n + 1)]
    genders = np.random.choice(GENDERS, size=n, p=[0.50, 0.50])
    firsts = [
        random.choice(MALE_FIRST_NAMES if g == "Male" else FEMALE_FIRST_NAMES)
        for g in genders
    ]
    lasts  = [random.choice(LAST_NAMES) for _ in range(n)]
    names  = [f"Dr. {f} {l}" for f, l in zip(firsts, lasts)]
    specialties = np.random.choice(SPECIALTIES, size=n)
    departments = [DEPARTMENTS[SPECIALTIES.index(s)] for s in specialties]

    df = pd.DataFrame({
        "doctor_id":    ids,
        "doctor_name":  names,
        "gender":       genders,
        "specialty":    specialties,
        "department":   departments
    })
    logger.info(f"  → {len(df)} rows ({int((genders=='Male').sum())} male, {int((genders=='Female').sum())} female)")
    return df


def generate_appointments(n: int, patient_ids, doctor_ids) -> pd.DataFrame:
    logger.info(f"Generating {n} appointments...")
    ids = [f"APT{str(i).zfill(7)}" for i in range(1, n + 1)]
    p_ids = np.random.choice(patient_ids, size=n)
    d_ids = np.random.choice(doctor_ids, size=n)

    base_date = datetime(2021, 1, 1)
    dates = [base_date + timedelta(days=random.randint(0, 1095)) for _ in range(n)]

    # Realistic status distribution
    statuses = np.random.choice(
        STATUSES, size=n, p=[0.65, 0.18, 0.10, 0.07]
    )
    waiting_times = np.random.exponential(scale=25, size=n).astype(int).clip(2, 180)
    costs = np.random.normal(loc=120, scale=60, size=n).round(2).clip(20, 600)

    df = pd.DataFrame({
        "appointment_id":     ids,
        "patient_id":         p_ids,
        "doctor_id":          d_ids,
        "appointment_date":   dates,
        "appointment_status": statuses,
        "waiting_time_minutes": waiting_times,
        "appointment_cost":   costs
    })

    # --- Inject quality issues ---
    # Null patient_id (~0.5%)
    df.loc[df.sample(frac=0.005).index, "patient_id"] = np.nan
    # Negative costs (~0.3%)
    df.loc[df.sample(frac=0.003).index, "appointment_cost"] = -random.uniform(10, 100)
    # Invalid status (~0.4%)
    df.loc[df.sample(frac=0.004).index, "appointment_status"] = "INVALID_STATUS"
    # Duplicate appointments (~0.6%)
    dupes = df.sample(frac=0.006)
    df = pd.concat([df, dupes], ignore_index=True)
    # Zero waiting time for some completed (edge case)
    mask = (df["appointment_status"] == "Completed") & (df["waiting_time_minutes"] < 1)
    df.loc[mask, "waiting_time_minutes"] = np.nan

    logger.info(f"  → {len(df)} rows")
    return df


def generate_treatments(n: int, patient_ids) -> pd.DataFrame:
    logger.info(f"Generating {n} treatments...")
    ids = [f"TRT{str(i).zfill(6)}" for i in range(1, n + 1)]
    p_ids = np.random.choice(patient_ids, size=n)
    diagnoses = np.random.choice(DIAGNOSES, size=n)
    t_types = np.random.choice(TREATMENT_TYPES, size=n)
    costs = np.random.normal(loc=800, scale=400, size=n).round(2).clip(50, 5000)

    base_date = datetime(2021, 1, 1)
    dates = [base_date + timedelta(days=random.randint(0, 1095)) for _ in range(n)]

    df = pd.DataFrame({
        "treatment_id":    ids,
        "patient_id":      p_ids,
        "diagnosis":       diagnoses,
        "treatment_type":  t_types,
        "treatment_cost":  costs,
        "treatment_date":  dates
    })

    # --- Inject quality issues ---
    # Future dates (~0.8%)
    future_mask = df.sample(frac=0.008).index
    df.loc[future_mask, "treatment_date"] = datetime.now() + timedelta(days=random.randint(10, 365))
    # Negative costs (~0.4%)
    df.loc[df.sample(frac=0.004).index, "treatment_cost"] = -random.uniform(50, 200)
    # Null diagnosis (~0.6%)
    df.loc[df.sample(frac=0.006).index, "diagnosis"] = np.nan

    logger.info(f"  → {len(df)} rows")
    return df


def generate_resources() -> pd.DataFrame:
    logger.info("Generating resources table...")
    records = []
    for dept, spec in zip(DEPARTMENTS, SPECIALTIES):
        total_beds = random.randint(20, 100)
        occupied   = random.randint(int(total_beds * 0.4), int(total_beds * 0.95))
        records.append({
            "department":              dept,
            "available_beds":          total_beds - occupied,
            "occupied_beds":           occupied,
            "total_beds":              total_beds,
            "staff_count":             random.randint(10, 60),
            "equipment_utilization":   round(random.uniform(0.50, 0.98), 2),
            "snapshot_date":           datetime.today().date()
        })
    df = pd.DataFrame(records)
    logger.info(f"  → {len(df)} rows")
    return df


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    patients     = generate_patients(N_PATIENTS)
    doctors      = generate_doctors(N_DOCTORS)
    appointments = generate_appointments(
        N_APPOINTMENTS,
        patients["patient_id"].dropna().unique(),
        doctors["doctor_id"].unique()
    )
    treatments   = generate_treatments(
        N_TREATMENTS,
        patients["patient_id"].dropna().unique()
    )
    resources    = generate_resources()

    patients.to_csv(f"{OUTPUT_DIR}/patients_raw.csv",         index=False)
    doctors.to_csv(f"{OUTPUT_DIR}/doctors.csv",               index=False)
    appointments.to_csv(f"{OUTPUT_DIR}/appointments_raw.csv", index=False)
    treatments.to_csv(f"{OUTPUT_DIR}/treatments_raw.csv",     index=False)
    resources.to_csv(f"{OUTPUT_DIR}/resources.csv",           index=False)

    logger.info("✅ All raw data files saved to data/raw/")
    logger.info(f"   patients:     {len(patients):,} rows")
    logger.info(f"   doctors:      {len(doctors):,} rows")
    logger.info(f"   appointments: {len(appointments):,} rows")
    logger.info(f"   treatments:   {len(treatments):,} rows")
    logger.info(f"   resources:    {len(resources):,} rows")


if __name__ == "__main__":
    main()
