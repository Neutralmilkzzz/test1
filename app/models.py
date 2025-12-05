import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db import Base


def default_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=default_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    accounts = relationship("EmailAccount", back_populates="user", cascade="all, delete-orphan")


class EmailAccount(Base):
    __tablename__ = "email_accounts"
    id = Column(String, primary_key=True, default=default_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    login_email = Column(String, nullable=False)
    app_password_enc = Column(String, nullable=False)
    destination_email = Column(String, nullable=False)
    imap_host = Column(String, nullable=False)
    imap_port = Column(Integer, nullable=False)
    smtp_host = Column(String, nullable=False)
    smtp_port = Column(Integer, nullable=False)
    active = Column(Boolean, default=True)
    last_uid = Column(String, nullable=True)
    last_checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="accounts")
    summaries = relationship("Summary", back_populates="account", cascade="all, delete-orphan")


class Summary(Base):
    __tablename__ = "summaries"
    id = Column(String, primary_key=True, default=default_uuid)
    email_account_id = Column(String, ForeignKey("email_accounts.id", ondelete="CASCADE"), nullable=False)
    subject = Column(String, nullable=False)
    sender = Column(String, nullable=False)
    summary_text = Column(Text, nullable=False)
    received_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    source_uid = Column(String, nullable=True)

    account = relationship("EmailAccount", back_populates="summaries")
