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
    mail.login(login_email, app_password)
    # 某些 163/188 服务器要求登录后上报 IMAP ID 才允许 SELECT，避免 "Unsafe Login"
    imaplib.Commands['ID'] = ('NONAUTH', 'AUTH', 'SELECTED')
    args = ("name", "imaplib", "contact", login_email, "version", "1.0.0", "vendor", "app-client")
    mail._simple_command('ID', '("' + '" "'.join(args) + '")')
    mail.select("INBOX")

    if hours is None or hours <= 0:
        # Fetch ALL messages
        status, data = mail.uid('search', None, "ALL")
    else:
        since_date = (datetime.utcnow() - timedelta(hours=hours)).strftime('%d-%b-%Y')
        # 使用 UID 搜索，避免后续 UID/序列号混用导致取信失败
        status, data = mail.uid('search', None, "SINCE", since_date)

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

        # 兼容部分服务器返回的多段响应，提取第一段有效的 RFC822 正文字节
        msg_bytes = None
        for part in msg_data:
            if isinstance(part, tuple) and len(part) >= 2 and part[1]:
                msg_bytes = part[1]
                break
        if not msg_bytes:
            continue

        msg = email.message_from_bytes(msg_bytes)
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

        # 已通过 IMAP SINCE 过滤，这里不再额外丢弃，避免时区偏差导致被误判
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
