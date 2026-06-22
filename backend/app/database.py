from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import config

engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# --- DATABASE MODELS ---

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user") # "admin" or "user"

class AccessLog(Base):
    __tablename__ = "access_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False) # "Granted" or "Denied"
    confidence = Column(Float, nullable=False)
    signal_sent = Column(String, nullable=False) # "Yes", "No", "Failed"

class IntruderAlert(Base):
    __tablename__ = "intruder_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    snapshot_path = Column(String, nullable=False)
    email_sent = Column(Boolean, default=False)

class AuthorizedUser(Base):
    __tablename__ = "authorized_users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    image_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    message = Column(String, nullable=False)
    type = Column(String, nullable=False) # "Alert", "System", "Lock"
    is_read = Column(Boolean, default=False)

def get_db():
    """
    Dependency injection helper to yield database sessions.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
