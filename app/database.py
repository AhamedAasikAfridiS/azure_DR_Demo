import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()


def normalize_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def build_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return normalize_database_url(database_url)

    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "drdemo")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")
    sslmode = os.getenv("DB_SSLMODE", "disable")

    user_safe = quote_plus(user)
    password_safe = quote_plus(password)

    return (
        f"postgresql+psycopg://{user_safe}:{password_safe}"
        f"@{host}:{port}/{name}?sslmode={sslmode}"
    )


DATABASE_URL = build_database_url()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def get_database_info() -> dict:
    safe_host = os.getenv("DB_HOST", "from DATABASE_URL")
    safe_db = os.getenv("DB_NAME", "from DATABASE_URL")
    safe_user = os.getenv("DB_USER", "from DATABASE_URL")

    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT
                        current_database() AS database_name,
                        current_user AS current_user,
                        inet_server_addr()::text AS server_ip,
                        inet_server_port() AS server_port,
                        version() AS version
                    """
                )
            ).mappings().first()

            return {
                "configured_host": safe_host,
                "configured_database": safe_db,
                "configured_user": safe_user,
                "connected": True,
                "database_name": row["database_name"],
                "current_user": row["current_user"],
                "server_ip": row["server_ip"],
                "server_port": row["server_port"],
                "version": row["version"],
            }

    except Exception as exc:
        return {
            "configured_host": safe_host,
            "configured_database": safe_db,
            "configured_user": safe_user,
            "connected": False,
            "error": str(exc),
        }