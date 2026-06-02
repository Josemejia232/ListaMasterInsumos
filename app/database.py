import os
import sys
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL no encontrada.\n"
        "En Render: Web Service > Environment > agregar variable DATABASE_URL\n"
        "En local: crear archivo .env con DATABASE_URL=<url>"
    )

POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "4"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "6"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "300"))

engine = create_engine(
    DATABASE_URL,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,
    connect_args={
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 3,
    },
)

@event.listens_for(engine, "connect")
def _set_session_attrs(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("SET statement_timeout = '30000'")
    cursor.execute("SET idle_in_transaction_session_timeout = '60000'")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
