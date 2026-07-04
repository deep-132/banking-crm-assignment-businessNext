"""Scoring tools: high-value-customer (HVC) score and conversion propensity.

Both scores are rules-based by default and every weight is a named constant
below, so a reviewer (or a bank's compliance team) can see exactly why a
customer scored the way they did — this is exposed verbatim via
`explain.py`. `estimate_conversion_probability` can optionally delegate to a
trained logistic-regression model (see `train_model.py`) when
`SCORING_MODE=ml`, to demonstrate the rules -> ML upgrade path without making
ML the default (there is no real historical conversion dataset to train on
in this take-home).
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.config import get_settings
from app.tools.customer_data import get_interactions, get_products_held, get_transactions

# --- HVC score weights (must sum to 1.0) -----------------------------------
HVC_WEIGHTS = {
    "balance_percentile": 0.40,
    "income_percentile": 0.25,
    "tenure_percentile": 0.15,
    "product_depth_percentile": 0.20,
}

# --- Conversion propensity weights (points out of 100) ---------------------
CONVERSION_WEIGHTS = {
    "salary_regularity": 25,
    "recent_large_discretionary_spend": 25,
    "loan_inquiry_signal": 30,
    "credit_score_band": 15,
    "low_debt_load": 5,
}

MODEL_PATH = Path(__file__).resolve().parents[1] / "db" / "conversion_model.joblib"


def _percentile_rank(series: pd.Series) -> pd.Series:
    if series.nunique(dropna=True) <= 1:
        return pd.Series(0.5, index=series.index)
    return series.rank(pct=True, na_option="bottom")


def compute_hvc_score(customers_df: pd.DataFrame) -> pd.DataFrame:
    """Adds hvc_score (0-100) and a breakdown dict per row.

    Uses percentile rank within the current candidate set rather than fixed
    absolute thresholds, so the score stays meaningful whether it's run over
    300 customers or a filtered slice of 20.
    """
    df = customers_df.copy()
    held = get_products_held(df["customer_id"].tolist())
    active_counts = (
        held[held["status"] == "active"].groupby("customer_id").size().rename("product_depth")
    )
    df = df.merge(active_counts, on="customer_id", how="left")
    df["product_depth"] = df["product_depth"].fillna(0)

    balance_pct = _percentile_rank(df["avg_monthly_balance_6m"].fillna(0))
    income_pct = _percentile_rank(df["monthly_income"].fillna(0))
    tenure_pct = _percentile_rank(df["tenure_years"].fillna(0))
    depth_pct = _percentile_rank(df["product_depth"])

    df["hvc_score"] = (
        HVC_WEIGHTS["balance_percentile"] * balance_pct
        + HVC_WEIGHTS["income_percentile"] * income_pct
        + HVC_WEIGHTS["tenure_percentile"] * tenure_pct
        + HVC_WEIGHTS["product_depth_percentile"] * depth_pct
    ) * 100
    df["hvc_score"] = df["hvc_score"].round(1)

    df["hvc_breakdown"] = [
        {
            "balance_percentile": round(float(b) * 100, 1),
            "income_percentile": round(float(inc) * 100, 1),
            "tenure_percentile": round(float(t) * 100, 1),
            "product_depth_percentile": round(float(d) * 100, 1),
            "active_product_count": int(pd_count),
        }
        for b, inc, t, d, pd_count in zip(balance_pct, income_pct, tenure_pct, depth_pct, df["product_depth"])
    ]
    return df


def _rules_based_conversion(customers_df: pd.DataFrame, product_type: str) -> pd.DataFrame:
    df = customers_df.copy()
    customer_ids = df["customer_id"].tolist()
    txns = get_transactions(customer_ids, lookback_days=180)
    interactions = get_interactions(customer_ids, lookback_days=60)

    salary_counts = (
        txns[txns["category"] == "salary"].groupby("customer_id").size().rename("salary_months")
    )
    recent_spend = txns[(txns["category"] == "discretionary")].copy()
    recent_spend["txn_date"] = pd.to_datetime(recent_spend["txn_date"])
    recent_spend_cutoff = pd.Timestamp.now() - pd.Timedelta(days=90)
    recent_large_spend_ids = set(
        recent_spend[recent_spend["txn_date"] >= recent_spend_cutoff]
        .merge(df[["customer_id", "monthly_income"]], on="customer_id")
        .query("amount >= monthly_income * 1.5")["customer_id"]
    )
    emi_ids = set(txns[txns["category"] == "emi"]["customer_id"])
    inquiry_ids = set(interactions[interactions["interaction_type"] == "loan_inquiry"]["customer_id"])

    scores = []
    breakdowns = []
    for _, row in df.iterrows():
        cid = row["customer_id"]
        points = 0.0
        breakdown = {}

        has_regular_salary = bool(salary_counts.get(cid, 0) >= 4)
        pts = CONVERSION_WEIGHTS["salary_regularity"] if has_regular_salary else 0
        points += pts
        breakdown["salary_regularity"] = {"met": has_regular_salary, "points": pts}

        has_recent_spend = cid in recent_large_spend_ids
        pts = CONVERSION_WEIGHTS["recent_large_discretionary_spend"] if has_recent_spend else 0
        points += pts
        breakdown["recent_large_discretionary_spend"] = {"met": has_recent_spend, "points": pts}

        has_inquiry = cid in inquiry_ids
        pts = CONVERSION_WEIGHTS["loan_inquiry_signal"] if has_inquiry else 0
        points += pts
        breakdown["loan_inquiry_signal"] = {"met": has_inquiry, "points": pts}

        credit_score = row["credit_score"]
        if credit_score >= 750:
            band_fraction = 1.0
        elif credit_score >= 700:
            band_fraction = 0.7
        elif credit_score >= 650:
            band_fraction = 0.4
        else:
            band_fraction = 0.0
        pts = CONVERSION_WEIGHTS["credit_score_band"] * band_fraction
        points += pts
        breakdown["credit_score_band"] = {"credit_score": int(credit_score), "points": round(pts, 1)}

        has_low_debt = cid not in emi_ids
        pts = CONVERSION_WEIGHTS["low_debt_load"] if has_low_debt else 0
        points += pts
        breakdown["low_debt_load"] = {"met": has_low_debt, "points": pts}

        scores.append(round(points, 1))
        breakdowns.append(breakdown)

    df["conversion_probability"] = [round(s / 100, 3) for s in scores]
    df["conversion_score"] = scores
    df["conversion_breakdown"] = breakdowns
    return df


def _ml_based_conversion(customers_df: pd.DataFrame, product_type: str) -> pd.DataFrame:
    """Loads a small logistic-regression model trained by train_model.py.

    Falls back to the rules-based path if no model artifact exists yet, so
    switching SCORING_MODE=ml never breaks the demo if training hasn't run.
    """
    if not MODEL_PATH.exists():
        return _rules_based_conversion(customers_df, product_type)

    df = _rules_based_conversion(customers_df, product_type)  # reuse feature breakdown
    bundle = joblib.load(MODEL_PATH)
    model, feature_names = bundle["model"], bundle["feature_names"]

    features = pd.DataFrame(
        {
            "salary_regularity": [b["salary_regularity"]["met"] for b in df["conversion_breakdown"]],
            "recent_large_discretionary_spend": [
                b["recent_large_discretionary_spend"]["met"] for b in df["conversion_breakdown"]
            ],
            "loan_inquiry_signal": [b["loan_inquiry_signal"]["met"] for b in df["conversion_breakdown"]],
            "credit_score": df["credit_score"].values,
            "low_debt_load": [b["low_debt_load"]["met"] for b in df["conversion_breakdown"]],
        }
    )[feature_names].astype(float)

    probabilities = model.predict_proba(features)[:, 1]
    df["conversion_probability"] = np.round(probabilities, 3)
    df["conversion_score"] = np.round(probabilities * 100, 1)
    return df


def estimate_conversion_probability(customers_df: pd.DataFrame, product_type: str = "personal_loan") -> pd.DataFrame:
    settings = get_settings()
    if settings.scoring_mode == "ml":
        return _ml_based_conversion(customers_df, product_type)
    return _rules_based_conversion(customers_df, product_type)
