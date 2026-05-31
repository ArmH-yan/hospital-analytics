"""
Hospital Analytics - Data Quality Validation Module
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

VALID_GENDERS    = {"Male", "Female", "Other"}
VALID_STATUSES   = {"Completed", "No-show", "Cancelled", "Rescheduled"}
VALID_TREATMENTS = {
    "Surgery", "Medication", "Physiotherapy", "Chemotherapy",
    "Radiation", "Counseling", "Observation", "Diagnostic Imaging"
}


def _record(table, check, col, severity, n_issues, total, detail=""):
    pct = round(n_issues / total * 100, 3) if total else 0
    return {
        "table":        table,
        "check":        check,
        "column":       col,
        "severity":     severity,
        "issues_found": n_issues,
        "total_rows":   total,
        "pct_affected": pct,
        "detail":       detail,
        "checked_at":   datetime.utcnow().isoformat()
    }


def check_patients(df):
    results = []
    n = len(df)
    results.append(_record("patients", "Null primary key",    "patient_id",       "HIGH",   int(df["patient_id"].isna().sum()), n))
    results.append(_record("patients", "Duplicate primary key","patient_id",      "HIGH",   int(df["patient_id"].dropna().duplicated().sum()), n))
    results.append(_record("patients", "Null value",           "age",             "MEDIUM", int(df["age"].isna().sum()), n))
    results.append(_record("patients", "Out-of-range value",   "age",             "HIGH",   int(((df["age"].dropna() <= 0) | (df["age"].dropna() > 120)).sum()), n, "age must be 1-120"))
    results.append(_record("patients", "Invalid category",     "gender",          "MEDIUM", int((~df["gender"].isin(VALID_GENDERS) & df["gender"].notna()).sum()), n))
    results.append(_record("patients", "Null value",           "gender",          "LOW",    int(df["gender"].isna().sum()), n))
    results.append(_record("patients", "Future date",          "registration_date","HIGH",  int((pd.to_datetime(df["registration_date"]) > datetime.now()).sum()), n))
    return results


def check_appointments(df):
    results = []
    n = len(df)
    results.append(_record("appointments", "Duplicate primary key",               "appointment_id",      "HIGH",   int(df["appointment_id"].dropna().duplicated().sum()), n))
    results.append(_record("appointments", "Null foreign key",                    "patient_id",          "HIGH",   int(df["patient_id"].isna().sum()), n))
    results.append(_record("appointments", "Invalid category",                    "appointment_status",  "HIGH",   int((~df["appointment_status"].isin(VALID_STATUSES) & df["appointment_status"].notna()).sum()), n))
    results.append(_record("appointments", "Negative value",                      "appointment_cost",    "HIGH",   int((df["appointment_cost"].dropna() < 0).sum()), n))
    results.append(_record("appointments", "Null value",                          "appointment_cost",    "MEDIUM", int(df["appointment_cost"].isna().sum()), n))
    results.append(_record("appointments", "Null waiting time on completed record","waiting_time_minutes","MEDIUM", int(((df["appointment_status"] == "Completed") & df["waiting_time_minutes"].isna()).sum()), n))
    return results


def check_treatments(df):
    results = []
    n = len(df)
    results.append(_record("treatments", "Duplicate primary key", "treatment_id",  "HIGH",   int(df["treatment_id"].dropna().duplicated().sum()), n))
    results.append(_record("treatments", "Future date",           "treatment_date","HIGH",   int((pd.to_datetime(df["treatment_date"]) > datetime.now()).sum()), n))
    results.append(_record("treatments", "Negative value",        "treatment_cost","HIGH",   int((df["treatment_cost"].dropna() < 0).sum()), n))
    results.append(_record("treatments", "Null value",            "diagnosis",     "MEDIUM", int(df["diagnosis"].isna().sum()), n))
    return results


def clean_patients(df):
    df = df.drop_duplicates(subset=["patient_id"])
    df = df[df["patient_id"].notna()]
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    df = df[(df["age"].isna()) | ((df["age"] >= 1) & (df["age"] <= 120))]
    df["gender"] = df["gender"].where(df["gender"].isin(VALID_GENDERS), other="Other")
    return df.reset_index(drop=True)


def clean_appointments(df):
    df = df.drop_duplicates(subset=["appointment_id"])
    df = df[df["patient_id"].notna()]
    df = df[df["appointment_status"].isin(VALID_STATUSES)]
    df = df[df["appointment_cost"].isna() | (df["appointment_cost"] >= 0)]
    df = df[df["waiting_time_minutes"].isna() | (df["waiting_time_minutes"] >= 0)]
    return df.reset_index(drop=True)


def clean_treatments(df):
    df = df.drop_duplicates(subset=["treatment_id"])
    df = df[pd.to_datetime(df["treatment_date"]) <= datetime.now()]
    df = df[df["treatment_cost"].isna() | (df["treatment_cost"] >= 0)]
    df["diagnosis"] = df["diagnosis"].fillna("Unspecified")
    return df.reset_index(drop=True)


def run_quality_checks(raw_dir="data/raw", clean_dir="data/cleaned", report_dir="reports"):
    os.makedirs(clean_dir,   exist_ok=True)
    os.makedirs(report_dir,  exist_ok=True)

    logger.info("Loading raw data...")
    patients     = pd.read_csv(f"{raw_dir}/patients_raw.csv")
    appointments = pd.read_csv(f"{raw_dir}/appointments_raw.csv")
    treatments   = pd.read_csv(f"{raw_dir}/treatments_raw.csv")

    all_results = []
    all_results.extend(check_patients(patients))
    all_results.extend(check_appointments(appointments))
    all_results.extend(check_treatments(treatments))

    report_df = pd.DataFrame(all_results)
    report_df.to_csv(f"{report_dir}/quality_report.csv", index=False)
    logger.info(f"Quality report saved -> {report_dir}/quality_report.csv")

    summary = (
        report_df.groupby(["table", "severity"])
        .agg(total_issues=("issues_found", "sum"), checks=("check", "count"))
        .reset_index()
    )
    summary.to_csv(f"{report_dir}/quality_summary.csv", index=False)

    high_issues = report_df[report_df["severity"] == "HIGH"]["issues_found"].sum()
    logger.info(f"Total HIGH severity issues: {high_issues:,}")

    # Print report using only plain ASCII box characters
    print("\n" + "-" * 80)
    print("  DATA QUALITY REPORT")
    print("-" * 80)
    print(report_df[["table", "check", "column", "severity", "issues_found", "pct_affected"]]
          .to_string(index=False))
    print("-" * 80 + "\n")

    clean_patients(patients).to_csv(f"{clean_dir}/patients_clean.csv",         index=False)
    clean_appointments(appointments).to_csv(f"{clean_dir}/appointments_clean.csv", index=False)
    clean_treatments(treatments).to_csv(f"{clean_dir}/treatments_clean.csv",   index=False)

    pd.read_csv(f"{raw_dir}/doctors.csv").to_csv(f"{clean_dir}/doctors.csv",   index=False)
    pd.read_csv(f"{raw_dir}/resources.csv").to_csv(f"{clean_dir}/resources.csv", index=False)

    logger.info("Cleaned data saved to data/cleaned/")
    return report_df


if __name__ == "__main__":
    run_quality_checks()
