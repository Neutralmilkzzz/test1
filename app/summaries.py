from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.db import get_db
from app.deps import get_current_user

router = APIRouter(prefix="/summaries", tags=["summaries"])


@router.get("/", response_model=list[schemas.SummaryOut])
def list_summaries(account_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    acct = db.query(models.EmailAccount).filter(models.EmailAccount.id == account_id, models.EmailAccount.user_id == user.id).first()
    if not acct:
        raise HTTPException(status_code=404, detail="account not found")
    summaries = db.query(models.Summary).filter(models.Summary.email_account_id == account_id).order_by(models.Summary.sent_at.desc()).all()
    return summaries
