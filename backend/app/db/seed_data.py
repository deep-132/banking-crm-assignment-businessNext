"""Generates a deterministic, synthetic banking CRM dataset.

The distributions below are hand-tuned (not just uniform randomness) so that a
meaningful, explainable subset of customers score high on both "high value"
and "likely to convert for a personal loan" — otherwise a demo over pure
random noise would produce arbitrary-looking results.

Run directly: `python -m app.db.seed_data`
"""

import random
from datetime import date, timedelta

import numpy as np
from faker import Faker

from app.config import get_settings
from app.db.database import connection_scope, init_schema, reset_database

CITIES = ["Mumbai", "Delhi", "Bengaluru", "Pune", "Hyderabad", "Chennai", "Ahmedabad", "Kolkata"]
OCCUPATIONS = ["Salaried - IT", "Salaried - Govt", "Salaried - Other", "Self-Employed", "Business Owner"]
SEGMENTS = ["Retail", "Mass Affluent", "HNI"]
LANGUAGES = ["English", "Hindi", "Marathi", "Tamil", "Telugu", "Bengali", "Gujarati"]
RM_IDS = ["RM-101", "RM-102", "RM-103", "RM-104"]

LOAN_OFFERS = [
    ("PL-STARTER", "Personal Loan Starter", "personal_loan", 25000, 500000, 13.5, 36, 650),
    ("PL-PRIME", "Personal Loan Prime", "personal_loan", 60000, 1500000, 11.5, 60, 700),
    ("PL-ELITE", "Personal Loan Elite", "personal_loan", 150000, 3500000, 10.5, 60, 750),
    ("HL-STD", "Home Loan Standard", "home_loan", 40000, 8000000, 8.7, 240, 700),
    ("CC-REWARDS", "Rewards Credit Card", "credit_card", 20000, 300000, 0.0, 0, 650),
]


def _random_date_within(rng: random.Random, days_back: int) -> date:
    return date.today() - timedelta(days=rng.randint(0, days_back))


def generate(customer_count: int, seed: int) -> None:
    fake = Faker("en_IN")
    Faker.seed(seed)
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    reset_database()

    customers = []
    accounts = []
    transactions = []
    products_held = []
    interactions = []

    txn_id_counter = 1

    # ~35% of customers are seeded as "strong personal loan candidates": stable
    # salary credit, decent-to-good credit score, a recent large discretionary
    # spend, no existing personal loan, and for a third of those a direct
    # loan_inquiry interaction. The rest of the population is a realistic mix
    # so the scoring pipeline has to do real work to separate signal from noise.
    strong_candidate_flags = np_rng.random(customer_count) < 0.35

    for i in range(customer_count):
        customer_id = f"CUST-{i + 1:04d}"
        is_strong_candidate = bool(strong_candidate_flags[i])

        segment_weights = [0.55, 0.32, 0.13]
        segment = rng.choices(SEGMENTS, weights=segment_weights, k=1)[0]

        age = rng.randint(24, 60)
        occupation = rng.choice(OCCUPATIONS)
        city = rng.choice(CITIES)
        tenure_years = round(rng.uniform(0.5, 15), 1)
        preferred_language = rng.choice(LANGUAGES)
        rm_id = rng.choice(RM_IDS)

        base_income = {
            "Retail": rng.uniform(30000, 80000),
            "Mass Affluent": rng.uniform(80000, 200000),
            "HNI": rng.uniform(200000, 600000),
        }[segment]
        if is_strong_candidate:
            base_income *= rng.uniform(1.0, 1.3)
        monthly_income = round(base_income, -2)

        credit_score = int(np.clip(np_rng.normal(680, 60), 550, 850))
        if is_strong_candidate:
            credit_score = int(np.clip(credit_score + rng.randint(20, 60), 550, 850))

        customers.append(
            (
                customer_id,
                fake.name(),
                age,
                occupation,
                city,
                segment,
                tenure_years,
                credit_score,
                monthly_income,
                fake.phone_number(),
                preferred_language,
                rm_id,
            )
        )

        # --- accounts ---
        balance_multiplier = {"Retail": 1.0, "Mass Affluent": 3.5, "HNI": 12.0}[segment]
        avg_balance = max(5000, np_rng.normal(monthly_income * balance_multiplier * 0.6, monthly_income * 0.3))
        account_id = f"ACC-{i + 1:04d}"
        accounts.append(
            (
                account_id,
                customer_id,
                "Savings",
                round(avg_balance * rng.uniform(0.8, 1.2), 2),
                round(avg_balance, 2),
                _random_date_within(rng, int(tenure_years * 365)).isoformat(),
            )
        )

        # --- transactions (last 6 months) ---
        # Salary credit: strong candidates and most salaried customers get a
        # consistent monthly salary credit; irregular for self-employed/business.
        is_salaried = occupation.startswith("Salaried")
        has_regular_salary = is_salaried or (is_strong_candidate and rng.random() < 0.7)
        if has_regular_salary:
            for month_back in range(6):
                txn_date = date.today().replace(day=1) - timedelta(days=month_back * 30)
                transactions.append(
                    (
                        f"TXN-{txn_id_counter:06d}",
                        customer_id,
                        txn_date.isoformat(),
                        round(monthly_income * rng.uniform(0.95, 1.0), 2),
                        "credit",
                        "salary",
                        "neft",
                    )
                )
                txn_id_counter += 1

        # Existing EMI debits (reduces conversion propensity if heavy debt load)
        has_existing_emi = rng.random() < (0.2 if is_strong_candidate else 0.4)
        if has_existing_emi:
            emi_amount = round(monthly_income * rng.uniform(0.1, 0.35), 2)
            for month_back in range(6):
                txn_date = date.today().replace(day=5) - timedelta(days=month_back * 30)
                transactions.append(
                    (
                        f"TXN-{txn_id_counter:06d}",
                        customer_id,
                        txn_date.isoformat(),
                        emi_amount,
                        "debit",
                        "emi",
                        "neft",
                    )
                )
                txn_id_counter += 1

        # Recent large discretionary spend — a classic personal-loan trigger
        # (wedding, travel, renovation, education, medical).
        discretionary_labels = ["wedding", "travel", "home_renovation", "education", "medical", "electronics"]
        has_recent_large_spend = is_strong_candidate or rng.random() < 0.25
        if has_recent_large_spend:
            spend_amount = round(monthly_income * rng.uniform(1.5, 5.0), 2)
            spend_days_back = rng.randint(1, 60) if is_strong_candidate else rng.randint(1, 180)
            transactions.append(
                (
                    f"TXN-{txn_id_counter:06d}",
                    customer_id,
                    (date.today() - timedelta(days=spend_days_back)).isoformat(),
                    spend_amount,
                    "debit",
                    "discretionary",
                    rng.choice(["card", "upi", "neft"]),
                )
            )
            txn_id_counter += 1

        # A handful of routine smaller transactions for realism
        for _ in range(rng.randint(3, 8)):
            transactions.append(
                (
                    f"TXN-{txn_id_counter:06d}",
                    customer_id,
                    _random_date_within(rng, 180).isoformat(),
                    round(rng.uniform(500, 8000), 2),
                    rng.choice(["debit", "debit", "credit"]),
                    rng.choice(["utility", "transfer", "other"]),
                    rng.choice(["upi", "card", "cash"]),
                )
            )
            txn_id_counter += 1

        # --- products held ---
        if rng.random() < 0.5:
            products_held.append((customer_id, "credit_card", "active", _random_date_within(rng, 1500).isoformat()))
        if segment in ("Mass Affluent", "HNI") and rng.random() < 0.4:
            products_held.append((customer_id, "fd", "active", _random_date_within(rng, 1000).isoformat()))
        has_active_personal_loan = (not is_strong_candidate) and rng.random() < 0.15
        if has_active_personal_loan:
            products_held.append(
                (customer_id, "personal_loan", "active", _random_date_within(rng, 500).isoformat())
            )
        if rng.random() < 0.1:
            products_held.append((customer_id, "home_loan", "active", _random_date_within(rng, 2000).isoformat()))

        # --- interactions ---
        if is_strong_candidate and rng.random() < 0.35:
            interactions.append(
                (
                    customer_id,
                    rng.choice(["app", "branch", "call_center"]),
                    "loan_inquiry",
                    _random_date_within(rng, 30).isoformat(),
                    "Customer asked about personal loan eligibility and rates.",
                )
            )
        if rng.random() < 0.2:
            interactions.append(
                (
                    customer_id,
                    rng.choice(["app", "website"]),
                    "browse",
                    _random_date_within(rng, 60).isoformat(),
                    "Viewed loan products page.",
                )
            )

    with connection_scope() as conn:
        conn.executemany(
            "INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", customers
        )
        conn.executemany("INSERT INTO accounts VALUES (?,?,?,?,?,?)", accounts)
        conn.executemany("INSERT INTO transactions VALUES (?,?,?,?,?,?,?)", transactions)
        conn.executemany(
            "INSERT INTO products_held (customer_id, product_type, status, start_date) VALUES (?,?,?,?)",
            products_held,
        )
        conn.executemany("INSERT INTO loan_offers VALUES (?,?,?,?,?,?,?,?)", LOAN_OFFERS)
        conn.executemany(
            "INSERT INTO interactions (customer_id, channel, interaction_type, interaction_date, notes) "
            "VALUES (?,?,?,?,?)",
            interactions,
        )

    print(
        f"Seeded {len(customers)} customers, {len(accounts)} accounts, "
        f"{len(transactions)} transactions, {len(products_held)} product holdings, "
        f"{len(interactions)} interactions, {len(LOAN_OFFERS)} loan offers."
    )


def main() -> None:
    settings = get_settings()
    init_schema()
    generate(settings.seed_customer_count, settings.seed_random_state)


if __name__ == "__main__":
    main()
