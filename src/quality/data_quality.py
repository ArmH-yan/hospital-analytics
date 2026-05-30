"""
Hospital Analytics - Data Quality Validation Module
Runs automated checks across all tables and generates quality reports.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import logging
import json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

VALID_GENDERS  = {"Male", "Female", "Other"}
VALID_STATUSES = {"Completed", "No-show", "Cancelled", "Rescheduled"}
VALID_TREATMENTS = {
    "Surgery", "Medication", "Physiotherapy", "Chemotherapy",
    "Radiation", "Counseling", "Observation", "Diagnostic Imaging"
}


def _record(table, check, col, severity, n_issues, total, detail=""):
    pct = round(n_issues / total * 100, 3) if total else 0
    return {
        "table":       table,
        "check":       check,
        "column":      col,
        "severity":    severity,   # HIGH / MEDIUM / LOW
        "issues_found": n_issues,
        "total_rows":  total,
        "pct_affected": pct,
        "detail":      detail,
        "checked_at":  datetime.utcnow().isoformat()
    }


def check_patients(df: pd.DataFrame) -> list:
    results = []
    n = len(df)

    # 1. Null patient_id
    null_ids = df["patient_id"].isna().sum()
    results.append(_record("patients", "Null primary key", "patient_id", "HIGH", int(null_ids), n))

    # 2. Duplicate patient_id
    dupes = df["patient_id"].dropna().duplicated().sum()
    results.append(_record("patients", "Duplicate primary key", "patient_id", "HIGH", int(dupes), n))

    # 3. Null age
    null_age = df["age"].isna().sum()
    results.append(_record("patients", "Null value", "age", "MEDIUM", int(null_age), n))

    # 4. Invalid age (<=0 or >120)
    invalid_age = ((df["age"].dropna() <= 0) | (df["age"].dropna() > 120)).sum()
    results.append(_record("patients", "Out-of-range value", "age", "HIGH", int(invalid_age), n,
                           "age must be 1-120"))

    # 5. Invalid gender
    invalid_gender = (~df["gender"].isin(VALID_GENDERS) & df["gender"].notna()).sum()
    results.append(_record("patients", "Invalid category", "gender", "MEDIUM", int(invalid_gender), n,
                           f"valid: {VALID_GENDERS}"))

    # 6. Null gender
    null_gender = df["gender"].isna().sum()
    results.append(_record("patients", "Null value", "gender", "LOW", int(null_gender), n))

    # 7. Future registration_date
    future_reg = (pd.to_datetime(df["registration_date"]) > datetime.now()).sum()
    results.append(_record("patients", "Future date", "registration_date", "HIGH", int(future_reg), n))

    return results


def check_appointments(df: pd.DataFrame) -> list:
    results = []
    n = len(df)

    # 1. Duplicate appointment_id
    dupes = df["appointment_id"].dropna().duplicated().sum()
    results.append(_record("appointments", "Duplicate primary key", "appointment_id", "HIGH", int(dupes), n))

    # 2. Null patient_id (FK)
    null_pat = df["patient_id"].isna().sum()
    results.append(_record("appointments", "Null foreign key", "patient_id", "HIGH", int(null_pat), n))

    # 3. Invalid status
    invalid_status = (~df["appointment_status"].isin(VALID_STATUSES) & df["appointment_status"].notna()).sum()
    results.append(_record("appointments", "Invalid category", "appointment_status", "HIGH", int(invalid_status), n,
                           f"valid: {VALID_STATUSES}"))

    # 4. Negative appointment_cost
    neg_cost = (df["appointment_cost"].dropna() < 0).sum()
    results.append(_record("appointments", "Negative value", "appointment_cost", "HIGH", int(neg_cost), n))

    # 5. Null appointment_cost
    null_cost = df["appointment_cost"].isna().sum()
    results.append(_record("appointments", "Null value", "appointment_cost", "MEDIUM", int(null_cost), n))

    # 6. Negative waiting time
    neg_wait = (df["waiting_time_minutes"].dropna() < 0).sum()
    results.append(_record("appointments", "Negative value", "waiting_time_minutes", "MEDIUM", int(neg_wait), n))

    # 7. Null waiting_time for completed appointments
    completed_null_wait = (
        (df["appointment_status"] == "Completed") & df["waiting_time_minutes"].isna()
    ).sum()
    results.append(_record("appointments", "Null waiting time on completed record",
                           "waiting_time_minutes", "MEDIUM", int(completed_null_wait), n))

    return results


def check_treatments(df: pd.DataFrame) -> list:
    results = []
    n = len(df)

    # 1. Duplicate treatment_id
    dupes = df["treatment_id"].dropna().duplicated().sum()
    results.append(_record("treatments", "Duplicate primary key", "treatment_id", "HIGH", int(dupes), n))

    # 2. Future treatment_date
    future = (pd.to_datetime(df["treatment_date"]) > datetime.now()).sum()
    results.append(_record("treatments", "Future date", "treatment_date", "HIGH", int(future), n))

    # 3. Negative treatment_cost
    neg_cost = (df["treatment_cost"].dropna() < 0).sum()
    results.append(_record("treatments", "Negative value", "treatment_cost", "HIGH", int(neg_cost), n))

    # 4. Null diagnosis
    null_diag = df["diagnosis"].isna().sum()
    results.append(_record("treatments", "Null value", "diagnosis", "MEDIUM", int(null_diag), n))

    # 5. Invalid treatment_type
    invalid_type = (~df["treatment_type"].isin(VALID_TREATMENTS) & df["treatment_type"].notna()).sum()
    results.append(_record("treatments", "Invalid category", "treatment_type", "MEDIUM", int(invalid_type), n))

    return results


def clean_patients(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Cleaning patients...")
    df = df.drop_duplicates(subset=["patient_id"])
    df = df[df["patient_id"].notna()]
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    df = df[(df["age"].isna()) | ((df["age"] >= 1) & (df["age"] <= 120))]
    df["gender"] = df["gender"].where(df["gender"].isin(VALID_GENDERS), other="Other")
    return df.reset_index(drop=True)


def clean_appointments(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Cleaning appointments...")
    df = df.drop_duplicates(subset=["appointment_id"])
    df = df[df["patient_id"].notna()]
    df = df[df["appointment_status"].isin(VALID_STATUSES)]
    df = df[df["appointment_cost"].isna() | (df["appointment_cost"] >= 0)]
    df = df[df["waiting_time_minutes"].isna() | (df["waiting_time_minutes"] >= 0)]
    return df.reset_index(drop=True)


def clean_treatments(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Cleaning treatments...")
    df = df.drop_duplicates(subset=["treatment_id"])
    df = df[pd.to_datetime(df["treatment_date"]) <= datetime.now()]
    df = df[df["treatment_cost"].isna() | (df["treatment_cost"] >= 0)]
    df["diagnosis"] = df["diagnosis"].fillna("Unspecified")
    return df.reset_index(drop=True)


def run_quality_checks(raw_dir="data/raw", clean_dir="data/cleaned", report_dir="reports"):
    os.makedirs(clean_dir, exist_ok=True)
    os.makedirs(report_dir, exist_ok=True)

    logger.info("Loading raw data...")
    patients     = pd.read_csv(f"{raw_dir}/patients_raw.csv")
    appointments = pd.read_csv(f"{raw_dir}/appointments_raw.csv")
    treatments   = pd.read_csv(f"{raw_dir}/treatments_raw.csv")

    # ── Run checks ────────────────────────────────────────────────────────────
    all_results = []
    all_results.extend(check_patients(patients))
    all_results.extend(check_appointments(appointments))
    all_results.extend(check_treatments(treatments))

    report_df = pd.DataFrame(all_results)
    report_df.to_csv(f"{report_dir}/quality_report.csv", index=False)
    logger.info(f"✅ Quality report saved → {report_dir}/quality_report.csv")

    # ── Summary stats ─────────────────────────────────────────────────────────
    summary = (
        report_df.groupby(["table", "severity"])
        .agg(total_issues=("issues_found", "sum"), checks=("check", "count"))
        .reset_index()
    )
    summary.to_csv(f"{report_dir}/quality_summary.csv", index=False)

    high_issues = report_df[report_df["severity"] == "HIGH"]["issues_found"].sum()
    logger.info(f"⚠️  Total HIGH severity issues: {high_issues:,}")

    # ── Print table ───────────────────────────────────────────────────────────
    print("\n" + "═"*80)
    print("  DATA QUALITY REPORT")
    print("═"*80)
    print(report_df[["table","check","column","severity","issues_found","pct_affected"]]
          .to_string(index=False))
    print("═"*80 + "\n")

    # ── Clean ─────────────────────────────────────────────────────────────────
    clean_patients(patients).to_csv(f"{clean_dir}/patients_clean.csv", index=False)
    clean_appointments(appointments).to_csv(f"{clean_dir}/appointments_clean.csv", index=False)
    clean_treatments(treatments).to_csv(f"{clean_dir}/treatments_clean.csv", index=False)

    # Copy doctors & resources unchanged (no issues injected)
    pd.read_csv(f"{raw_dir}/doctors.csv").to_csv(f"{clean_dir}/doctors.csv", index=False)
    pd.read_csv(f"{raw_dir}/resources.csv").to_csv(f"{clean_dir}/resources.csv", index=False)

    logger.info("✅ Cleaned data saved to data/cleaned/")
    return report_df


if __name__ == "__main__":
    run_quality_checks()
