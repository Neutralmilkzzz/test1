import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app import models
from app.settings import get_settings
from app.security import decrypt_secret
from app.email_client import fetch_recent
from app import deepseek

settings = get_settings()


async def process_account(db: Session, account: models.EmailAccount, summary_max_chars: int = None):
    summary_max_chars = summary_max_chars or settings.summary_max_chars
    app_password = decrypt_secret(account.app_password_enc)
    messages = fetch_recent(
        account.imap_host,
        account.imap_port,
        account.login_email,
        app_password,
        hours=24,
        limit=settings.fetch_limit,
    )
    if not messages:
        account.last_checked_at = datetime.utcnow()
        db.commit()
        return 0

    processed = 0

    def _format_msg(msg):
        ts = msg['received_at'].strftime('%Y-%m-%d %H:%M')
        body_snip = (msg['body'] or '')[:summary_max_chars]
        return f"发件人: {msg['from']}\n主题: {msg['subject']}\n时间: {ts}\n内容: {body_snip}"

    formatted = [_format_msg(m) for m in messages]

    # 让 deepseek 选出最有价值的 5 条主题
    try:
        top5_subjects = await deepseek.select_top5(formatted)
    except Exception as exc:
        print(f"select_top5 failed: {exc}")
        top5_subjects = []

    for msg in messages:
        body_snip = (msg['body'] or '')[:summary_max_chars]
        record = models.Summary(
            email_account_id=account.id,
            subject=msg['subject'],
            sender=msg['from'],
            summary_text=body_snip,
            received_at=msg['received_at'],
            source_uid=msg['uid'],
        )
        db.add(record)
        processed += 1

    if top5_subjects:
        top_summary = models.Summary(
            email_account_id=account.id,
            subject="[TOP5] 过去24小时高价值主题",
            sender="system",
            summary_text="\n".join(top5_subjects),
            received_at=datetime.utcnow(),
            source_uid=None,
        )
        db.add(top_summary)

    account.last_checked_at = datetime.utcnow()
    account.last_uid = None
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
