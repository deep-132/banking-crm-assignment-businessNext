-- Banking CRM synthetic schema

CREATE TABLE IF NOT EXISTS customers (
    customer_id         TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    age                 INTEGER NOT NULL,
    occupation          TEXT NOT NULL,
    city                TEXT NOT NULL,
    segment             TEXT NOT NULL,           -- e.g. Retail, Mass Affluent, HNI
    tenure_years        REAL NOT NULL,
    credit_score        INTEGER NOT NULL,
    monthly_income      REAL NOT NULL,
    phone               TEXT NOT NULL,
    preferred_language  TEXT NOT NULL,
    rm_id               TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id              TEXT PRIMARY KEY,
    customer_id             TEXT NOT NULL REFERENCES customers(customer_id),
    account_type            TEXT NOT NULL,       -- Savings, Current, FD
    balance                 REAL NOT NULL,
    avg_monthly_balance_6m  REAL NOT NULL,
    opened_date             TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id      TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    txn_date    TEXT NOT NULL,
    amount      REAL NOT NULL,
    txn_type    TEXT NOT NULL,   -- credit, debit
    category    TEXT NOT NULL,   -- salary, emi, discretionary, transfer, utility, other
    channel     TEXT NOT NULL    -- upi, neft, card, cash, cheque
);

CREATE TABLE IF NOT EXISTS products_held (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id  TEXT NOT NULL REFERENCES customers(customer_id),
    product_type TEXT NOT NULL,   -- personal_loan, home_loan, credit_card, fd, demat
    status       TEXT NOT NULL,   -- active, closed
    start_date   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS loan_offers (
    product_id        TEXT PRIMARY KEY,
    product_name      TEXT NOT NULL,
    product_type      TEXT NOT NULL,  -- personal_loan, home_loan, etc.
    min_income        REAL NOT NULL,
    max_amount        REAL NOT NULL,
    interest_rate     REAL NOT NULL,
    tenure_months     INTEGER NOT NULL,
    min_credit_score  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS interactions (
    interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id    TEXT NOT NULL REFERENCES customers(customer_id),
    channel        TEXT NOT NULL,   -- branch, app, call_center, website
    interaction_type TEXT NOT NULL, -- loan_inquiry, complaint, service_request, browse
    interaction_date TEXT NOT NULL,
    notes          TEXT
);

CREATE INDEX IF NOT EXISTS idx_txn_customer ON transactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_accounts_customer ON accounts(customer_id);
CREATE INDEX IF NOT EXISTS idx_products_customer ON products_held(customer_id);
CREATE INDEX IF NOT EXISTS idx_interactions_customer ON interactions(customer_id);
