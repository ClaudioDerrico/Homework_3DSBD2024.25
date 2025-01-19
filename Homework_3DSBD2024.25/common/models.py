from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean
from .database import Base
import datetime

class User(Base):
    __tablename__ = 'users'
    email = Column(String, primary_key=True, index=True)
    ticker = Column(String)
    high_value = Column(Float, nullable=True)
    low_value = Column(Float, nullable=True)
    high_notification_sent = Column(Boolean, default=False)
    low_notification_sent = Column(Boolean, default=False)

class FinancialData(Base):
    __tablename__ = 'financial_data'
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    value = Column(Float)
    timestamp = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
