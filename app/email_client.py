import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from typing import List, Dict, Any


def _decode_subject(raw_subject):
    subject, encoding = decode_header(raw_subject)[0] if raw_subject else ("无主题", None)
    if isinstance(subject, bytes):
        return subject.decode(encoding or "utf-8", errors="ignore")
    return subject or "无主题"


def fetch_recent(imap_host: str, imap_port: int, login_email: str, app_password: str, hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
    mail = imaplib.IMAP4_SSL(imap_host, imap_port)
    imaplib.Commands['ID'] = ('NONAUTH','AUTH', 'SELECTED')
    args = ("name", "imaplib", "version", "1.0.0")
    mail._simple_command('ID', '("' + '" "'.join(args)+'")')
    mail.login(login_email, app_password)
    mail.select("INBOX")

    since_date = (datetime.utcnow() - timedelta(hours=hours)).strftime('%d-%b-%Y')
    status, data = mail.search(None, "SINCE", since_date)
    if status != "OK":
        mail.logout()
        return []

    uids = data[0].split()
    if not uids:
        mail.logout()
        return []

    selected_uids = uids[-limit:]
    messages: List[Dict[str, Any]] = []

    for uid in selected_uids:
        status, msg_data = mail.uid('fetch', uid, '(RFC822)')
        if status != "OK" or not msg_data:
            continue
        msg = email.message_from_bytes(msg_data[0][1])
        subject = _decode_subject(msg.get("Subject"))
        from_ = msg.get("From", "未知发件人")
        if "<" in from_ and ">" in from_:
            from_ = from_.split("<")[1].split(">")[0]
        date_str = msg.get("Date", "")
        try:
            received_at = email.utils.parsedate_to_datetime(date_str) if date_str else datetime.utcnow()
        except Exception:
            received_at = datetime.utcnow()

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disp = str(part.get("Content-Disposition"))
                if content_type == "text/plain" and "attachment" not in disp:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode('utf-8', errors='ignore')
                        break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode('utf-8', errors='ignore')

        # 只保留过去 hours 内的邮件
        if received_at >= datetime.utcnow() - timedelta(hours=hours):
            messages.append({
                "uid": uid.decode(),
                "subject": subject,
                "from": from_,
                "body": body,
                "received_at": received_at,
            })

    mail.logout()
    # 按时间倒序
    return sorted(messages, key=lambda m: m["received_at"], reverse=True)
