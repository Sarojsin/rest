from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.modules.tenancy.middleware import tenant_context

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    db_path = settings.database_url.replace("sqlite:///", "")
    if db_path.startswith("./"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    # Set branch_id for Row-Level Security:
    # branch_id = restaurant_id = tenant_id (from tenancy model)
    branch_id = getattr(tenant_context, "tenant_id", None)
    if branch_id:
        db.execute(text(f"SET LOCAL app.branch_id = '{branch_id}'"))
    try:
        yield db
    finally:
        db.close()
