import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_chat import router as chat_router
from app.config import get_settings
from app.db.database import init_schema
from app.db.seed_data import generate

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Banking CRM Agentic AI", version="0.1.0")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.on_event("startup")
def ensure_seeded() -> None:
    settings = get_settings()
    db_path = Path(settings.database_path)
    if not db_path.is_absolute():
        db_path = Path(__file__).resolve().parents[1] / db_path
    if not db_path.exists():
        logging.info("No existing database found at %s — seeding synthetic demo data.", db_path)
        init_schema()
        generate(settings.seed_customer_count, settings.seed_random_state)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
