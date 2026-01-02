"""Database configuration for Ticketing API."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from pathlib import Path

# Database path - defaults to database/ticketing.db
DB_PATH = os.getenv("TICKETING_DB_PATH", "database/ticketing.db")

# Ensure database directory exists
db_dir = Path(DB_PATH).parent
db_dir.mkdir(parents=True, exist_ok=True)

# Create engine
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

