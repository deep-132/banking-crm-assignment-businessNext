"""Optional ML extensibility demo: trains a logistic regression conversion model.

There is no real historical "did this customer take a personal loan" label in
this take-home, so this script *synthesizes* labels by sampling around the
same signals the rules engine uses (with noise), purely to demonstrate how a
`SCORING_MODE=ml` path would plug into `scoring.py` once real outcome data
exists. Do not treat the resulting model as a validated predictor.

Run: `python -m app.tools.train_model`
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
import joblib

from app.config import get_settings
from app.db.database import init_schema
from app.db.seed_data import generate
from app.tools.customer_data import CustomerFilters, get_customers
from app.tools.scoring import MODEL_PATH, _rules_based_conversion

FEATURE_NAMES = [
    "salary_regularity",
    "recent_large_discretionary_spend",
    "loan_inquiry_signal",
    "credit_score",
    "low_debt_load",
]


def _build_training_frame(seed: int = 7, n_customers: int = 800) -> pd.DataFrame:
    init_schema()
    generate(n_customers, seed)
    df = get_customers(CustomerFilters())
    scored = _rules_based_conversion(df, "personal_loan")

    features = pd.DataFrame(
        {
            "salary_regularity": [b["salary_regularity"]["met"] for b in scored["conversion_breakdown"]],
            "recent_large_discretionary_spend": [
                b["recent_large_discretionary_spend"]["met"] for b in scored["conversion_breakdown"]
            ],
            "loan_inquiry_signal": [b["loan_inquiry_signal"]["met"] for b in scored["conversion_breakdown"]],
            "credit_score": scored["credit_score"].values,
            "low_debt_load": [b["low_debt_load"]["met"] for b in scored["conversion_breakdown"]],
        }
    )
    # Synthetic label: convert with probability derived from the rules score
    # plus noise, so the model has to learn a real (if synthetic) signal
    # rather than memorizing the rules engine 1:1.
    rng = np.random.default_rng(seed)
    noisy_prob = np.clip(scored["conversion_probability"].values + rng.normal(0, 0.15, len(scored)), 0, 1)
    labels = rng.binomial(1, noisy_prob)
    features["converted"] = labels
    return features


def train_and_save(seed: int = 7) -> None:
    # _build_training_frame reseeds the DB with a larger synthetic population
    # to get enough training rows; restore the normal demo dataset afterwards
    # so this script has no lasting side effect on the running demo DB.
    data = _build_training_frame(seed=seed)
    X = data[FEATURE_NAMES].astype(float)
    y = data["converted"]

    model = LogisticRegression(max_iter=1000)
    model.fit(X, y)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_names": FEATURE_NAMES}, MODEL_PATH)
    print(f"Trained on {len(data)} synthetic samples, saved model to {MODEL_PATH}")
    print(f"Train accuracy: {model.score(X, y):.3f}")

    settings = get_settings()
    generate(settings.seed_customer_count, settings.seed_random_state)
    print("Restored demo dataset to configured seed/count.")


if __name__ == "__main__":
    train_and_save()
