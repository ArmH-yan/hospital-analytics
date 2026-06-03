"""
Hospital Analytics — No-show Prediction Model
Predicts appointment no-shows using patient + appointment features.
Business value: flag high-risk appointments for proactive outreach/reminder calls.

This is ~10% of the project — focused on demonstrating ML awareness,
not production MLOps.
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.metrics import (
    classification_report, roc_auc_score, confusion_matrix,
    precision_recall_curve, average_precision_score
)
from sklearn.preprocessing import LabelEncoder
import logging
import os
import json

try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DB_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('DB_USER','postgres')}:{os.getenv('DB_PASS','postgres')}"
    f"@{os.getenv('DB_HOST','localhost')}:{os.getenv('DB_PORT','5432')}"
    f"/{os.getenv('DB_NAME','hospital_analytics')}"
)

FEATURE_COLS = [
    "age", "department_enc", "appointment_weekday",
    "days_since_registration", "prior_no_shows", "prior_total_appointments",
    "prior_no_show_rate"
]
TARGET = "no_show"


def load_features(engine) -> pd.DataFrame:
    """Pull ML feature view from PostgreSQL."""
    logger.info("Loading feature data from v_no_show_risk_features...")
    query = "SELECT * FROM v_no_show_risk_features WHERE age IS NOT NULL"
    df = pd.read_sql(query, engine)
    logger.info(f"  -> {len(df):,} rows loaded")
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Feature engineering on top of the SQL view."""
    # Prior no-show rate
    df["prior_no_show_rate"] = (
        df["prior_no_shows"] / df["prior_total_appointments"].replace(0, np.nan)
    ).fillna(0)

    # Encode department
    le = LabelEncoder()
    df["department_enc"] = le.fit_transform(df["department"].fillna("Unknown"))

    # Clip outliers
    df["age"] = df["age"].clip(1, 100)
    df["days_since_registration"] = df["days_since_registration"].fillna(0).clip(0, 3650)
    df["prior_no_shows"]          = df["prior_no_shows"].fillna(0).clip(0, 20)

    logger.info(f"  Class distribution: {df[TARGET].value_counts().to_dict()}")
    return df, le


def evaluate_model(model, X_test, y_test, model_name: str) -> dict:
    y_pred  = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    report  = classification_report(y_test, y_pred, output_dict=True)
    roc_auc = roc_auc_score(y_test, y_proba)
    pr_auc  = average_precision_score(y_test, y_proba)
    cm      = confusion_matrix(y_test, y_pred)

    metrics = {
        "model":     model_name,
        "accuracy":  round(report["accuracy"], 4),
        "precision": round(report["1"]["precision"], 4),
        "recall":    round(report["1"]["recall"], 4),
        "f1":        round(report["1"]["f1-score"], 4),
        "roc_auc":   round(roc_auc, 4),
        "pr_auc":    round(pr_auc, 4),
        "tn": int(cm[0][0]), "fp": int(cm[0][1]),
        "fn": int(cm[1][0]), "tp": int(cm[1][1]),
    }

    print(f"\n{'-'*50}")
    print(f"  {model_name}")
    print(f"{'-'*50}")
    print(f"  Accuracy : {metrics['accuracy']:.4f}")
    print(f"  Precision: {metrics['precision']:.4f}")
    print(f"  Recall   : {metrics['recall']:.4f}")
    print(f"  F1       : {metrics['f1']:.4f}")
    print(f"  ROC-AUC  : {metrics['roc_auc']:.4f}")
    print(f"  PR-AUC   : {metrics['pr_auc']:.4f}")
    print(f"  Confusion Matrix:\n    TN={cm[0][0]}  FP={cm[0][1]}\n    FN={cm[1][0]}  TP={cm[1][1]}")

    return metrics


def get_feature_importance(model, model_name: str) -> pd.DataFrame:
    importances = pd.DataFrame({
        "feature":    FEATURE_COLS,
        "importance": model.feature_importances_
    }).sort_values("importance", ascending=False)
    print(f"\n  Feature Importances ({model_name}):")
    print(importances.to_string(index=False))
    return importances


def run_ml_pipeline():
    engine = get_engine_safe()
    df = None

    if engine is not None:
        try:
            df = load_features(engine)
            if len(df) == 0:
                logger.warning("View returned 0 rows - ETL may not have run yet.")
                df = None
        except Exception as e:
            logger.warning(f"Could not load from DB: {e}. Using synthetic data.")
            df = None

    if df is None:
        logger.info("Using synthetic data for demo (run ETL first for real results).")
        df = generate_synthetic_features()

    df, le = engineer_features(df)

    X = df[FEATURE_COLS].copy()
    y = df[TARGET].copy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    logger.info(f"  Train: {len(X_train):,}  Test: {len(X_test):,}")

    all_metrics = []

    # ── Random Forest ─────────────────────────────────────────────────────────
    logger.info("\nTraining Random Forest...")
    rf = RandomForestClassifier(
        n_estimators=200, max_depth=8, min_samples_leaf=10,
        class_weight="balanced", random_state=42, n_jobs=-1
    )
    rf.fit(X_train, y_train)
    rf_metrics = evaluate_model(rf, X_test, y_test, "Random Forest")
    get_feature_importance(rf, "Random Forest")
    all_metrics.append(rf_metrics)

    # ── XGBoost (if available) ────────────────────────────────────────────────
    if XGBOOST_AVAILABLE:
        logger.info("\nTraining XGBoost...")
        scale_pos = (y_train == 0).sum() / (y_train == 1).sum()
        xgb = XGBClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.05,
            scale_pos_weight=scale_pos, eval_metric="auc",
            random_state=42, n_jobs=-1, verbosity=0
        )
        xgb.fit(X_train, y_train)
        xgb_metrics = evaluate_model(xgb, X_test, y_test, "XGBoost")
        get_feature_importance(xgb, "XGBoost")
        all_metrics.append(xgb_metrics)
    else:
        logger.info("  XGBoost not installed — skipping (pip install xgboost)")

    # ── Save metrics ─────────────────────────────────────────────────────────
    os.makedirs("reports", exist_ok=True)
    metrics_df = pd.DataFrame(all_metrics)
    metrics_df.to_csv("reports/ml_metrics.csv", index=False)
    logger.info("\n[DONE] ML metrics saved to reports/ml_metrics.csv")

    # ── Business interpretation ───────────────────────────────────────────────
    best = metrics_df.sort_values("roc_auc", ascending=False).iloc[0]
    print(f"""
+==========================================================+
|  BUSINESS INTERPRETATION                                 |
+==========================================================+
|  Best model : {best['model']:<43} |
|  ROC-AUC    : {best['roc_auc']:<43} |
|  Recall     : {best['recall']:<43} |
+==========================================================+
|  • A recall of {best['recall']:.0%} means the model correctly flags  |
|    ~{best['recall']:.0%} of patients who would no-show.              |
|  • These patients can receive automated SMS reminders,   |
|    phone calls, or be double-booked to reduce lost       |
|    appointment slots.                                    |
|  • If recall > 0.65, this model is worth deploying in    |
|    production: estimated 30-40% recovery of revenue      |
|    lost to no-shows.                                     |
+==========================================================+
""")

    return metrics_df


def get_engine_safe():
    try:
        engine = create_engine(DB_URL, echo=False, pool_pre_ping=True, connect_args={"connect_timeout": 3})
        with engine.connect():
            pass
        return engine
    except Exception:
        return None


def generate_synthetic_features(n=20000):
    """Fallback: generate features without a DB connection for demo/testing.

    Note: feature set mirrors the DB view `v_no_show_risk_features` so the
    model is trained on the same columns in both paths.
    """
    np.random.seed(42)
    df = pd.DataFrame({
        "age":                      np.random.randint(18, 80, n),
        "department":               np.random.choice(["Cardiology Dept","Oncology Dept",
                                                      "General Medicine Dept","Emergency Dept",
                                                      "Pediatrics Dept"], n),
        "appointment_weekday":      np.random.randint(0, 7, n),
        "days_since_registration":  np.random.randint(0, 1460, n),
        "prior_no_shows":           np.random.poisson(0.5, n).clip(0, 10),
        "prior_total_appointments": np.random.poisson(3, n).clip(0, 20),
    })
    prior_rate = df["prior_no_shows"] / (df["prior_total_appointments"] + 1)
    p = (
        0.05
        + 0.55 * prior_rate
        + 0.10 * (df["appointment_weekday"].isin([0, 4])).astype(float)  # Mon/Fri
        + 0.06 * (df["age"] < 30).astype(float)
    ).clip(0.05, 0.80)
    df["no_show"] = np.random.binomial(1, p)
    logger.info(f"  Generated {n:,} synthetic feature rows (no DB). No-show rate: {df['no_show'].mean():.2%}")
    return df


if __name__ == "__main__":
    run_ml_pipeline()
