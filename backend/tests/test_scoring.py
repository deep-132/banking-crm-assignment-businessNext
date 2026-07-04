from app.tools.customer_data import CustomerFilters, get_customers
from app.tools.recommend import check_eligibility_and_recommend
from app.tools.scoring import compute_hvc_score, estimate_conversion_probability


def test_hvc_score_in_range_and_correlates_with_balance():
    df = get_customers(CustomerFilters())
    scored = compute_hvc_score(df)
    assert scored["hvc_score"].between(0, 100).all()

    top = scored.sort_values("hvc_score", ascending=False).iloc[0]
    bottom = scored.sort_values("hvc_score", ascending=True).iloc[0]
    assert top["avg_monthly_balance_6m"] >= bottom["avg_monthly_balance_6m"]


def test_conversion_probability_bounded_and_has_breakdown():
    df = get_customers(CustomerFilters())
    scored = estimate_conversion_probability(df, product_type="personal_loan")
    assert scored["conversion_probability"].between(0, 1).all()
    assert all(isinstance(b, dict) and "loan_inquiry_signal" in b for b in scored["conversion_breakdown"])


def test_recommend_respects_eligibility_thresholds():
    df = get_customers(CustomerFilters())
    recommended = check_eligibility_and_recommend(df, product_type="personal_loan")
    eligible_rows = recommended[recommended["recommended_product"].notna()]
    for _, row in eligible_rows.iterrows():
        assert row["recommended_amount"] > 0
        assert row["recommended_rate"] > 0

    ineligible_rows = recommended[recommended["recommended_product"].isna()]
    for _, row in ineligible_rows.iterrows():
        assert "Not eligible" in row["eligibility_reason"]
