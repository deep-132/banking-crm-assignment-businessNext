from app.tools.customer_data import CustomerFilters, get_customers, get_products_held, get_transactions


def test_get_customers_returns_rows():
    df = get_customers(CustomerFilters())
    assert len(df) == 60
    assert {"customer_id", "monthly_income", "avg_monthly_balance_6m"}.issubset(df.columns)


def test_get_customers_filters_by_segment():
    df = get_customers(CustomerFilters(segment="HNI"))
    assert (df["segment"] == "HNI").all()


def test_get_customers_excludes_active_product():
    all_df = get_customers(CustomerFilters())
    filtered_df = get_customers(CustomerFilters(exclude_active_product_types=["personal_loan"]))
    held = get_products_held(all_df["customer_id"].tolist())
    active_pl_ids = set(
        held[(held["status"] == "active") & (held["product_type"] == "personal_loan")]["customer_id"]
    )
    assert active_pl_ids.isdisjoint(set(filtered_df["customer_id"]))
    assert len(filtered_df) <= len(all_df)


def test_get_transactions_scoped_to_requested_customers():
    df = get_customers(CustomerFilters())
    ids = df["customer_id"].tolist()[:5]
    txns = get_transactions(ids, lookback_days=365)
    assert set(txns["customer_id"]).issubset(set(ids))
