import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL

logger = logging.getLogger(__name__)

if not DATABASE_URL:
    logger.warning("DATABASE_URL is not set; database operations will fail until it is configured")

engine = create_engine(
    DATABASE_URL or "postgresql://localhost/unused",
    pool_pre_ping=True,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
