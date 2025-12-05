from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class Login(BaseModel):
    email: EmailStr
    password: str


class EmailAccountCreate(BaseModel):
    login_email: EmailStr
    app_password: str
    destination_email: EmailStr
    imap_host: str | None = None
    imap_port: int | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None


class EmailAccountOut(BaseModel):
    id: str
    login_email: EmailStr
    destination_email: EmailStr
    active: bool
    last_checked_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class SummaryOut(BaseModel):
    id: str
    subject: str
    sender: str
    summary_text: str
    received_at: Optional[datetime]
    sent_at: datetime

    class Config:
        from_attributes = True
