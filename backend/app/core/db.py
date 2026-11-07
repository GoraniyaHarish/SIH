"""Engine + session factory."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=10,
    echo=settings.db_echo,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@event.listens_for(engine, "connect")
def _set_timeouts(dbapi_conn, _record):  # pragma: no cover - driver level
    """Bound statement time so a pathological query cannot pin a worker."""
    with dbapi_conn.cursor() as cur:
        cur.execute("SET statement_timeout = 15000")
        cur.execute("SET idle_in_transaction_session_timeout = 20000")
