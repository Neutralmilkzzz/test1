import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from app import models
from app.settings import get_settings
from app.security import decrypt_secret
from app.email_client import fetch_unseen
from app.mailer import send_summary
from app import deepseek

settings = get_settings()


async def process_account(db: Session, account: models.EmailAccount, summary_max_chars: int = None):
    summary_max_chars = summary_max_chars or settings.summary_max_chars
    app_password = decrypt_secret(account.app_password_enc)
    messages = fetch_unseen(
        account.imap_host,
        account.imap_port,
        account.login_email,
        app_password,
        last_uid=account.last_uid,
        limit=settings.fetch_limit,
    )
    if not messages:
        account.last_checked_at = datetime.utcnow()
        db.commit()
        return 0

    processed = 0
    for msg in messages:
        content = f"发件人: {msg['from']}\n主题: {msg['subject']}\n时间: {msg['received_at']}\n内容: {msg['body'][:summary_max_chars]}"
        try:
            summary = await deepseek.summarize(content)
            send_summary(
                account.smtp_host,
                account.smtp_port,
                account.login_email,
                app_password,
                account.destination_email,
                msg['subject'],
                summary,
                msg['body'],
            )
            record = models.Summary(
                email_account_id=account.id,
                subject=msg['subject'],
                sender=msg['from'],
                summary_text=summary,
                received_at=msg['received_at'],
                source_uid=msg['uid'],
            )
            db.add(record)
            processed += 1
            account.last_uid = msg['uid']
        except Exception as exc:  # best-effort; log upstream
            print(f"process failed for uid {msg['uid']}: {exc}")
            continue

    account.last_checked_at = datetime.utcnow()
    db.commit()
    return processed


async def process_all(db_factory, interval: int):
    while True:
        db = db_factory()
        try:
            accounts = db.query(models.EmailAccount).filter(models.EmailAccount.active == True).all()
            for account in accounts:
                await process_account(db, account)
        finally:
            db.close()
        await asyncio.sleep(interval)
