import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def send_summary(smtp_host: str, smtp_port: int, login_email: str, app_password: str, recipient: str, subject: str, summary: str, full_text: str | None = None) -> None:
    msg = MIMEMultipart()
    msg["From"] = login_email
    msg["To"] = recipient
    msg["Subject"] = f"邮件总结 - {subject}"

    body = f"您好，\n\n这是自动生成的邮件总结：\n\n{summary}\n\n时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
    if full_text:
        body += "\n原文截断预览:\n" + full_text[:500]
    msg.attach(MIMEText(body, "plain", "utf-8"))

    server = smtplib.SMTP_SSL(smtp_host, smtp_port)
    server.login(login_email, app_password)
    server.sendmail(login_email, recipient, msg.as_string())
    server.quit()
