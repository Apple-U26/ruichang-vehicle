from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


def ensure_column(
    table_name: str,
    column_name: str,
    column_ddl: str,
) -> None:
    inspector = inspect(engine)
    if table_name in inspector.get_table_names():
        columns = {
            column["name"] for column in inspector.get_columns(table_name)
        }
        if column_name not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        f"ADD COLUMN {column_name} {column_ddl}"
                    )
                )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
