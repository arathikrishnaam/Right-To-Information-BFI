"""
database.py — SQLite database setup and helper functions
Uses SQLAlchemy for ORM with async support via aiosqlite
"""
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ── Load env ─────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./rti_saarthi.db")

# ── SQLAlchemy Setup ─────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── Models ───────────────────────────────────────────────────

class RTIApplication(Base):
    """Stores every RTI application filed through the platform."""
    __tablename__ = "rti_applications"

    id              = Column(Integer, primary_key=True, index=True)
    ref_number      = Column(String(30), unique=True, index=True)
    applicant_name  = Column(String(100), nullable=False)
    applicant_email = Column(String(100))
    applicant_mobile= Column(String(15))
    applicant_address= Column(Text)
    is_bpl          = Column(Boolean, default=False)
    bpl_card_no     = Column(String(30))

    original_query  = Column(Text)
    language        = Column(String(20), default="en")
    department      = Column(String(200))
    pio_id          = Column(String(20))
    pio_name        = Column(String(100))
    pio_email       = Column(String(100))
    subject         = Column(String(500))
    questions       = Column(Text)          # JSON list of formal questions
    draft_text      = Column(Text)          # Full RTI application text

    status          = Column(String(30), default="drafted")
    # Status flow: drafted → filed → acknowledged → response_received
    #              → first_appeal_filed → second_appeal_filed → closed

    filed_date      = Column(DateTime)
    deadline_date   = Column(DateTime)
    response_text   = Column(Text)
    response_date   = Column(DateTime)
    appeal_filed    = Column(Boolean, default=False)
    appeal_date     = Column(DateTime)

    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base):
    """Simple user table for authentication."""
    __tablename__ = "users"

    id       = Column(Integer, primary_key=True, index=True)
    name     = Column(String(100), nullable=False)
    email    = Column(String(100), unique=True, index=True)
    mobile   = Column(String(15))
    address  = Column(Text)
    is_bpl   = Column(Boolean, default=False)
    bpl_card = Column(String(30))
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Create all tables on startup."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency — yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def generate_ref_number(db) -> str:
    """Generate a unique RTI reference number like RTI2024-00042."""
    year = datetime.utcnow().year
    count = db.query(RTIApplication).count() + 1
    return f"RTI{year}-{count:05d}"
