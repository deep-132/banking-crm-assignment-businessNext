import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True, scope="session")
def _seeded_test_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("data") / "test_banking_crm.db"
    os.environ["DATABASE_PATH"] = str(db_path)
    os.environ["SEED_CUSTOMER_COUNT"] = "60"
    os.environ["SEED_RANDOM_STATE"] = "1"

    from app.config import get_settings

    get_settings.cache_clear()

    from app.db.database import init_schema
    from app.db.seed_data import generate

    init_schema()
    generate(60, 1)
    yield
