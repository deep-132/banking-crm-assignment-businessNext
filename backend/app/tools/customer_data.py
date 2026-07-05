"""Data retrieval tools — the agent's window into the CRM database.

Every function here does a plain SQL/pandas read; no scoring or LLM logic
lives in this module so it stays independently testable and swappable for a
real core-banking data source later.
"""

from dataclasses import dataclass, field

import pandas as pd

from app.db.database import get_connection


@dataclass
class CustomerFilters:
    city: str | None = None
    segment: str | None = None
    min_monthly_income: float | None = None
    exclude_active_product_types: list[str] = field(default_factory=list)


def get_customers(filters: CustomerFilters | None = None) -> pd.DataFrame:
    """Returns a customer x account-summary frame, optionally filtered.

    Joins customers with their savings account so downstream scoring has
    balance data without a second round trip.
    """
    filters = filters or CustomerFilters()
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            """
            SELECT c.customer_id, c.name, c.age, c.occupation, c.city, c.segment,
                   c.tenure_years, c.credit_score, c.monthly_income, c.phone,
                   c.preferred_language, c.rm_id,
                   a.balance, a.avg_monthly_balance_6m
            FROM customers c
            LEFT JOIN accounts a ON a.customer_id = c.customer_id
            """,
            conn,
        )
    finally:
        conn.close()

    if filters.city:
        df = df[df["city"].str.lower() == filters.city.lower()]
    if filters.segment:
        df = df[df["segment"].str.lower() == filters.segment.lower()]
    if filters.min_monthly_income is not None:
        df = df[df["monthly_income"] >= filters.min_monthly_income]

    if filters.exclude_active_product_types:
        held = get_products_held(df["customer_id"].tolist())
        held_active = held[held["status"] == "active"]
        excluded_ids = set(
            held_active[
                held_active["product_type"].isin(filters.exclude_active_product_types)
            ]["customer_id"]
        )
        df = df[~df["customer_id"].isin(excluded_ids)]

    return df.reset_index(drop=True)


def get_transactions(customer_ids: list[str], lookback_days: int = 180) -> pd.DataFrame:
    if not customer_ids:
        return pd.DataFrame(
            columns=[
                "txn_id",
                "customer_id",
                "txn_date",
                "amount",
                "txn_type",
                "category",
                "channel",
            ]
        )
    conn = get_connection()
    try:
        placeholders = ",".join("?" for _ in customer_ids)
        df = pd.read_sql_query(
            f"""
            SELECT txn_id, customer_id, txn_date, amount, txn_type, category, channel
            FROM transactions
            WHERE customer_id IN ({placeholders})
              AND date(txn_date) >= date('now', ?)
            """,
            conn,
            params=[*customer_ids, f"-{lookback_days} days"],
        )
    finally:
        conn.close()
    return df


def get_products_held(customer_ids: list[str]) -> pd.DataFrame:
    if not customer_ids:
        return pd.DataFrame(
            columns=["customer_id", "product_type", "status", "start_date"]
        )
    conn = get_connection()
    try:
        placeholders = ",".join("?" for _ in customer_ids)
        df = pd.read_sql_query(
            f"""
            SELECT customer_id, product_type, status, start_date
            FROM products_held
            WHERE customer_id IN ({placeholders})
            """,
            conn,
            params=customer_ids,
        )
    finally:
        conn.close()
    return df


def get_interactions(customer_ids: list[str], lookback_days: int = 90) -> pd.DataFrame:
    if not customer_ids:
        return pd.DataFrame(
            columns=[
                "interaction_id",
                "customer_id",
                "channel",
                "interaction_type",
                "interaction_date",
                "notes",
            ]
        )
    conn = get_connection()
    try:
        placeholders = ",".join("?" for _ in customer_ids)
        df = pd.read_sql_query(
            f"""
            SELECT interaction_id, customer_id, channel, interaction_type, interaction_date, notes
            FROM interactions
            WHERE customer_id IN ({placeholders})
              AND date(interaction_date) >= date('now', ?)
            """,
            conn,
            params=[*customer_ids, f"-{lookback_days} days"],
        )
    finally:
        conn.close()
    return df


def get_loan_offers(product_type: str | None = None) -> pd.DataFrame:
    conn = get_connection()
    try:
        if product_type:
            df = pd.read_sql_query(
                "SELECT * FROM loan_offers WHERE product_type = ?",
                conn,
                params=[product_type],
            )
        else:
            df = pd.read_sql_query("SELECT * FROM loan_offers", conn)
    finally:
        conn.close()
    return df


def get_customer_by_id(customer_id: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT c.*, a.balance, a.avg_monthly_balance_6m
            FROM customers c
            LEFT JOIN accounts a ON a.customer_id = c.customer_id
            WHERE c.customer_id = ?
            """,
            (customer_id,),
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None
