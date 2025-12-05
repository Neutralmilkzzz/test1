from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import models, schemas
from app.db import get_db
from app.deps import get_current_user
from app.security import encrypt_secret
from app.settings import get_settings

router = APIRouter(prefix="/accounts", tags=["accounts"])
settings = get_settings()


@router.post("/", response_model=schemas.EmailAccountOut)
def create_account(payload: schemas.EmailAccountCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    imap_host = payload.imap_host or settings.imap_host
    imap_port = payload.imap_port or settings.imap_port
    smtp_host = payload.smtp_host or settings.smtp_host
    smtp_port = payload.smtp_port or settings.smtp_port

    acct = models.EmailAccount(
        user_id=user.id,
        login_email=payload.login_email,
        app_password_enc=encrypt_secret(payload.app_password),
        destination_email=payload.destination_email,
        imap_host=imap_host,
        imap_port=imap_port,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
    )
    db.add(acct)
    db.commit()
    db.refresh(acct)
    return acct


@router.get("/", response_model=list[schemas.EmailAccountOut])
def list_accounts(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(models.EmailAccount).filter(models.EmailAccount.user_id == user.id).all()


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    acct = db.query(models.EmailAccount).filter(models.EmailAccount.id == account_id, models.EmailAccount.user_id == user.id).first()
    if not acct:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="account not found")
    db.delete(acct)
    db.commit()
    return None
