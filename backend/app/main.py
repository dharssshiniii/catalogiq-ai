from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.database import Base, engine
from app.models import database as database_models  # noqa: F401


def migrate_sqlite_prototype() -> None:
    """Additive prototype migration for Milestone 1 local SQLite files."""
    if engine.dialect.name != "sqlite": return
    additions = {
        "dataset_jobs": {"updated_at": "DATETIME", "processed_count": "INTEGER DEFAULT 0", "failed_count": "INTEGER DEFAULT 0", "cancelled": "BOOLEAN DEFAULT 0", "placeholder_count": "INTEGER DEFAULT 0", "duplicate_count": "INTEGER DEFAULT 0", "processing_duration_ms": "INTEGER DEFAULT 0"},
        "product_records": {"review_status": "VARCHAR(40) DEFAULT 'NEEDS_REVIEW'", "created_at": "DATETIME"},
        "enriched_fields": {"reason_codes_json": "TEXT DEFAULT '[]'", "candidates_json": "TEXT DEFAULT '[]'"},
        "review_decisions": {"product_id": "INTEGER REFERENCES product_records(id)"},
    }
    with engine.begin() as connection:
        for table, columns in additions.items():
            existing = {row[1] for row in connection.exec_driver_sql(f"PRAGMA table_info({table})")}
            for name, definition in columns.items():
                if name not in existing: connection.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    migrate_sqlite_prototype()
    yield


configure_logging()
app = FastAPI(title="CatalogIQ AI API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)
app.include_router(router)
