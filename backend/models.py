"""SQLAlchemy ORM models."""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from backend.config import DATABASE_URL

Base = declarative_base()


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(String, unique=True, index=True, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    customer_id = Column(String, index=True)
    channel = Column(String)
    message = Column(Text, nullable=False)
    agent_reply = Column(Text)
    product = Column(String)
    order_value = Column(Float)
    customer_country = Column(String)
    resolution_status = Column(String)
    # AI-generated fields
    ai_category = Column(String)
    ai_sentiment = Column(String)
    ai_frustration = Column(Float)
    ai_response = Column(Text)
    ai_confidence = Column(Float)
    processed_at = Column(DateTime)


class Insight(Base):
    __tablename__ = "insights"

    id = Column(Integer, primary_key=True)
    insight_type = Column(String)  # top_issue, anomaly, trend
    category = Column(String)
    metric_value = Column(Float)
    description = Column(Text)
    metadata_json = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)


engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()
