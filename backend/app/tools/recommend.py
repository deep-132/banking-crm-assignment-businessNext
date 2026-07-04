"""Product recommendation tool: rules-based eligibility matching against loan_offers."""

import pandas as pd

from app.tools.customer_data import get_loan_offers

# How many months of income a customer is deemed able to service as a personal loan.
INCOME_MULTIPLE_FOR_LOAN_AMOUNT = 10


def check_eligibility_and_recommend(customers_df: pd.DataFrame, product_type: str = "personal_loan") -> pd.DataFrame:
    """Adds recommended_product, recommended_amount, recommended_rate, eligibility_reason."""
    df = customers_df.copy()
    offers = get_loan_offers(product_type=product_type)

    if offers.empty:
        df["recommended_product"] = None
        df["recommended_amount"] = None
        df["recommended_rate"] = None
        df["eligibility_reason"] = "No offers configured for this product type."
        return df

    recommended_products = []
    recommended_amounts = []
    recommended_rates = []
    reasons = []

    for _, row in df.iterrows():
        eligible = offers[
            (offers["min_income"] <= row["monthly_income"]) & (offers["min_credit_score"] <= row["credit_score"])
        ]
        if eligible.empty:
            recommended_products.append(None)
            recommended_amounts.append(None)
            recommended_rates.append(None)
            reasons.append(
                f"Not eligible for any {product_type} tier: income {row['monthly_income']:.0f} / "
                f"credit score {row['credit_score']} below minimum thresholds."
            )
            continue

        # Pick the highest tier (by min_income requirement) the customer clears —
        # i.e. the best offer they qualify for, not just the easiest one.
        best_tier = eligible.sort_values("min_income", ascending=False).iloc[0]
        income_based_amount = row["monthly_income"] * INCOME_MULTIPLE_FOR_LOAN_AMOUNT
        recommended_amount = min(best_tier["max_amount"], income_based_amount)

        recommended_products.append(best_tier["product_name"])
        recommended_amounts.append(round(float(recommended_amount), -2))
        recommended_rates.append(float(best_tier["interest_rate"]))
        reasons.append(
            f"Qualifies for {best_tier['product_name']} (income {row['monthly_income']:.0f} >= "
            f"{best_tier['min_income']:.0f}, credit score {row['credit_score']} >= "
            f"{best_tier['min_credit_score']}); amount capped at "
            f"{INCOME_MULTIPLE_FOR_LOAN_AMOUNT}x monthly income or the tier max."
        )

    df["recommended_product"] = recommended_products
    df["recommended_amount"] = recommended_amounts
    df["recommended_rate"] = recommended_rates
    df["eligibility_reason"] = reasons
    return df
