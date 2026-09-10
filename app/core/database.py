from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import app_config

_password = quote_plus(app_config.MYSQL_PASSWORD)
DATABASE_URL = (
    f"mysql+pymysql://{app_config.MYSQL_USER}:{_password}"
    f"@{app_config.MYSQL_HOST}:{app_config.MYSQL_PORT}"
    f"/{app_config.MYSQL_DB}?charset=utf8mb4"
)

engine = create_engine(
    DATABASE_URL,
    pool_size=app_config.DB_POOL_MIN_SIZE,
    max_overflow=app_config.DB_POOL_MAX_SIZE - app_config.DB_POOL_MIN_SIZE,
    pool_recycle=app_config.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    connect_args={
        "connect_timeout": app_config.DB_CONNECT_TIMEOUT,
        "read_timeout": app_config.DB_READ_TIMEOUT,
        "write_timeout": app_config.DB_WRITE_TIMEOUT,
        "ssl": {
            "ca": app_config.MYSQL_CA_CERT,
        },
        "init_command": (
            "SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED"
        ),
    },
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and closes it afterwards."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
