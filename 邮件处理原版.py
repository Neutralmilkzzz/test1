# 导入必要的库
import imaplib
import email
from email.header import decode_header
import datetime
import time
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# ==========================================================================================
# 写在前面,部署教程
# 作者121abcd,hku cds student
# 此代码100%由deepseekcoder生成,然后由我人工精校(精校到能用就行,话说这叫精校吗?)
# 本人不保证代码质量和可读性以及安全性,但是我保证此代码基本可以正常工作,完成邮件转发总结的服务,下面是配置教程
#
# 你需要修改下面*配置信息*部分里面末端注释了"<-修改这里---------------"的部分
# 然后想办法搞个能运行这个代码的设备来运行这个代码
# 你需要安装requests这个依赖
# 安装方法:在终端运行pip install requests
#
# 你需要准备一个网易163邮箱,在网易163邮箱网页版,找到设置->POP3/SMTP/IMAP,
# 在里面打开imap的服务,此时这个网易邮箱会给你一个邮箱授权码,或者说是一个令牌或者说是一个密钥,请你妥善保存这个密钥,下面要使用
# 你需要在outlook邮箱里开启自动转发至你的163邮箱！！！
# 你还需要一个deepseek开放平台的api,
# 在deepseek官网deepseek.com,上面有个开放平台的按钮,点进去注册,然后注册账号,然后充值,很便宜的,理论上总结一条花0.003人民币
# 然后再左边点到API keys,然后创建一个key以备使用
#
# 你还可以修改检测邮箱内容的时间,在下面修改,单位:秒

# ==================== 配置信息 ====================

# 刷新频率<-修改这里---------------
TIME_GAP = 3600

# 邮箱登录信息 - 163邮箱专用配置
EMAIL_ACCOUNT = "11111"  # 你的163邮箱地址<-修改这里---------------
EMAIL_PASSWORD = "1111"  # 163邮箱授权码（不是登录密码）<-修改这里---------------
IMAP_SERVER = "imap.163.com"  # 163邮箱的IMAP服务器
IMAP_PORT = 993  # IMAP的安全端口号

# DeepSeek API配置
DEEPSEEK_API_KEY = "1111"  # DeepSeek API密钥<-修改这里---------------
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"  # DeepSeek API网址

# 发送邮件的配置 - 163邮箱SMTP配置
SMTP_SERVER = "smtp.163.com"  # 163邮箱的SMTP服务器
SMTP_PORT = 465  # 163邮箱SMTP的SSL端口号
RECIPIENT_EMAIL = "1111"  # 接收总结邮件的邮箱地址<-修改这里---------------

# 文件路径配置
SUMMARY_DIR = "daily_summaries"  # 存放每日总结的文件夹名称
LAST_UPDATE_FILE = "last_update.txt"  # 记录上次更新时间的文件


# ==================== 初始化函数 ====================
def initialize_system():
    """
    初始化系统，创建必要的文件夹和文件
    """
    # 创建存放每日总结的文件夹（如果不存在）
    if not os.path.exists(SUMMARY_DIR):
        os.makedirs(SUMMARY_DIR)
        print(f"创建文件夹: {SUMMARY_DIR}")

    # 创建上次更新时间记录文件（如果不存在）
    if not os.path.exists(LAST_UPDATE_FILE):
        with open(LAST_UPDATE_FILE, "w", encoding="utf-8") as f:
            f.write("1970-01-01 00:00:00")  # 初始时间


# ==================== 邮箱连接函数 ====================
def connect_to_email():
    """
    连接到163邮箱服务器
    返回: 已连接的邮箱对象（已选择INBOX文件夹）
    """
    try:
        # 建立SSL连接
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)

        imaplib.Commands['ID'] = ('NONAUTH','AUTH', 'SELECTED')
        args = ("name", "imaplib", "version", "1.0.0")
        typ, dat = mail._simple_command('ID', '("' + '" "'.join(args)+'")')
        # 登录邮箱
        mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        print("✅ 登录163邮箱成功")



        # 必须选择文件夹才能进入SELECTED状态
        status, data = mail.select("INBOX")
        if status != "OK":
            print(f"❌ 选择INBOX文件夹失败: {data}")
            mail.logout()
            return None

        print("✅ 已选择INBOX文件夹，进入SELECTED状态")
        return mail

    except imaplib.IMAP4.error as e:
        print(f"❌ IMAP协议错误: {e}")
        return None
    except Exception as e:
        print(f"❌ 邮箱连接失败: {e}")
        return None


# ==================== 邮件处理函数 ====================
def fetch_unread_emails(mail):
    """
    获取未读邮件（必须在SELECTED状态下调用）
    参数mail: 已连接并选择文件夹的邮箱对象
    返回: 未读邮件的ID列表
    """
    try:
        # 检查邮箱状态，确保在SELECTED状态
        status, messages = mail.search(None, "UNSEEN")
        if status == "OK":
            email_ids = messages[0].split()
            print(f"📧 发现 {len(email_ids)} 封未读邮件")
            return email_ids
        else:
            print(f"⚠️  搜索未读邮件失败: {status} - {messages}")
            return []
    except imaplib.IMAP4.error as e:
        print(f"❌ SEARCH命令执行失败（状态错误）: {e}")
        return []
    except Exception as e:
        print(f"❌ 获取未读邮件失败: {e}")
        return []


def parse_email(mail, email_id):
    """
    解析邮件内容（必须在SELECTED状态下调用）
    参数mail: 已连接的邮箱对象
    参数email_id: 邮件的唯一标识符
    返回: 包含邮件信息的字典
    """
    try:
        # 获取邮件原始数据
        status, msg_data = mail.fetch(email_id, "(RFC822)")
        if status != "OK":
            print(f"❌ 获取邮件内容失败: {status}")
            return None

        # 解析邮件
        msg = email.message_from_bytes(msg_data[0][1])

        # 解码邮件主题
        subject, encoding = decode_header(msg["Subject"])[0] if msg["Subject"] else ("无主题", None)
        if isinstance(subject, bytes):
            subject = subject.decode(encoding if encoding else "utf-8")

        # 获取发件人信息
        from_ = msg.get("From", "未知发件人")

        # 简化发件人信息（去除多余内容）
        if "<" in from_ and ">" in from_:
            from_ = from_.split("<")[1].split(">")[0]

        # 获取邮件日期
        date_str = msg.get("Date", "")
        try:
            # 尝试解析邮件日期
            email_date = email.utils.parsedate_to_datetime(date_str) if date_str else datetime.datetime.now()
        except:
            email_date = datetime.datetime.now()

        # 获取邮件正文
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                # 只处理文本内容，忽略附件
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode('utf-8', errors='ignore')
                            break
                    except:
                        continue
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode('utf-8', errors='ignore')
            except:
                body = "无法解码邮件内容"

        # 清理邮件正文（去除过长内容）
        if len(body) > 2000:
            body = body[:2000] + "..."

        return {
            "subject": subject,
            "from": from_,
            "body": body,
            "date": email_date,
            "id": email_id
        }

    except Exception as e:
        print(f"❌ 解析邮件失败: {e}")
        return None


# ==================== AI总结函数 ====================
def summarize_with_deepseek(email_content):
    """
    使用DeepSeek API总结邮件内容
    参数email_content: 邮件内容字符串
    返回: API返回的总结内容
    """
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "你是一个专业的邮件总结助手。请用简洁的中文总结邮件核心内容，突出重要信息和行动项，不超过80字。"
            },
            {
                "role": "user",
                "content": f"请总结以下邮件内容，提取关键信息：\n\n{email_content}"
            }
        ],
        "temperature": 0.3,
        "max_tokens": 250
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        summary = result["choices"][0]["message"]["content"]
        return summary.strip()
    except requests.Timeout:
        print("⏰ DeepSeek API请求超时")
        return "总结生成超时，请稍后重试"
    except Exception as e:
        print(f"❌ DeepSeek API调用失败: {e}")
        return "AI总结暂时不可用"


# ==================== 文件操作函数 ====================
def get_today_summary_filename():
    """
    获取当天总结文件的完整路径
    返回: 格式为 YYYY-MM-DD.txt 的文件路径
    """
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    return os.path.join(SUMMARY_DIR, f"{today}.txt")


def update_daily_summary(email_subject, email_from, summary):
    """
    更新每日总结文件
    参数email_subject: 邮件主题
    参数email_from: 发件人信息
    参数summary: 邮件总结
    返回: 是否成功更新
    """
    try:
        filename = get_today_summary_filename()
        file_exists = os.path.exists(filename)

        with open(filename, "a", encoding="utf-8") as f:
            # 如果是新文件，写入日期标题
            if not file_exists:
                f.write(f"📧 每日邮件总结 - {datetime.datetime.now().strftime('%Y年%m月%d日')}\n")
                f.write("=" * 60 + "\n\n")

            # 写入邮件总结
            f.write(f"📋 主题: {email_subject}\n")
            f.write(f"👤 发件人: {email_from}\n")
            f.write(f"💡 总结: {summary}\n")
            f.write(f"⏰ 时间: {datetime.datetime.now().strftime('%H:%M:%S')}\n")
            f.write("-" * 50 + "\n\n")

        print(f"✅ 已更新总结文件: {filename}")
        return True

    except Exception as e:
        print(f"❌ 更新总结文件失败: {e}")
        return False


def read_today_summary():
    """
    读取当天的总结文件内容
    返回: 文件内容字符串
    """
    try:
        filename = get_today_summary_filename()
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                return f.read()
        return "📭 今日尚无邮件总结"
    except Exception as e:
        print(f"❌ 读取总结文件失败: {e}")
        return "❌ 读取文件失败"


# ==================== 邮件发送函数 ====================
def send_update_notification():
    """
    发送更新通知邮件，包含最新的总结内容
    使用163邮箱的SMTP服务发送
    """
    try:
        # 读取当前总结内容
        summary_content = read_today_summary()

        # 创建邮件对象
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ACCOUNT
        msg["To"] = RECIPIENT_EMAIL
        msg["Subject"] = f"邮件总结更新 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # 添加邮件正文
        body = f"""您好！

这是最新的邮件总结更新：

{summary_content}

此邮件由自动监控系统生成
生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # 连接163邮箱SMTP服务器并发送
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)  # 163需要使用SSL
        server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)  # 使用授权码登录
        server.sendmail(EMAIL_ACCOUNT, RECIPIENT_EMAIL, msg.as_string())
        server.quit()

        print("✅ 更新通知邮件发送成功")
        return True

    except Exception as e:
        print(f"❌ 发送更新通知失败: {e}")
        return False


def get_last_update_time():
    """
    获取上次更新时间
    返回: datetime对象
    """
    try:
        with open(LAST_UPDATE_FILE, "r", encoding="utf-8") as f:
            time_str = f.read().strip()
            return datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    except:
        return datetime.datetime(1970, 1, 1)


def update_last_update_time():
    """
    更新上次更新时间记录
    """
    try:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LAST_UPDATE_FILE, "w", encoding="utf-8") as f:
            f.write(current_time)
        print(f"✅ 更新时间记录: {current_time}")
    except Exception as e:
        print(f"❌ 更新最后更新时间失败: {e}")


# ==================== 主监控循环 ====================
def check_and_process_emails():
    """
    检查并处理新邮件的核心函数
    返回: 是否处理了邮件
    """
    mail = connect_to_email()
    if not mail:
        return False

    try:
        # 获取未读邮件（现在在SELECTED状态，可以执行SEARCH）
        unread_emails = fetch_unread_emails(mail)
        if not unread_emails:
            # 没有新邮件，正常关闭连接
            mail.close()
            mail.logout()
            return False

        print(f"📥 开始处理 {len(unread_emails)} 封新邮件")
        processed_count = 0

        for email_id in unread_emails:
            email_data = parse_email(mail, email_id)
            if email_data:
                # 准备邮件内容供AI总结
                email_content = f"""
发件人: {email_data['from']}
主题: {email_data['subject']}
时间: {email_data['date'].strftime('%Y-%m-%d %H:%M')}
内容: {email_data['body']}
"""

                # 使用AI总结邮件
                print(f"🤖 正在总结邮件: {email_data['subject']}")
                summary = summarize_with_deepseek(email_content)

                # 更新每日总结文件
                if update_daily_summary(email_data["subject"], email_data["from"], summary):
                    processed_count += 1
                    print(f"✅ 已处理: {email_data['subject']}")

        # 正常关闭连接
        mail.close()
        mail.logout()

        # 如果有处理邮件，发送更新通知
        if processed_count > 0:
            send_update_notification()
            update_last_update_time()
            return True

        return False

    except Exception as e:
        print(f"❌ 处理邮件时出错: {e}")
        try:
            mail.logout()  # 尝试正常退出
        except:
            pass
        return False


def main():
    """
    主函数 - 每分钟检查一次邮箱
    """
    print("🚀 启动邮箱自动监控系统...")
    print(f"📁 总结文件存放位置: {os.path.abspath(SUMMARY_DIR)}")
    print(f"⏰ 每{TIME_GAP}秒检查一次新邮件")

    # 初始化系统
    initialize_system()

    try:
        while True:
            # 记录开始时间
            start_time = datetime.datetime.now()
            current_time = start_time.strftime('%H:%M:%S')

            # 检查并处理邮件
            processed = check_and_process_emails()

            if processed:
                print(f"[{current_time}] ✅ 邮件处理完成，等待下一{TIME_GAP}秒...")
            else:
                print(f"[{current_time}] 📭 无新邮件，等待下一{TIME_GAP}秒...")

            # 计算剩余等待时间（确保每分钟执行一次）
            elapsed = (datetime.datetime.now() - start_time).total_seconds()
            wait_time = max(0, TIME_GAP - elapsed)  # 总共等待60秒

            time.sleep(wait_time)

    except KeyboardInterrupt:
        print("\n🛑 程序已手动停止")
    except Exception as e:
        print(f"❌ 程序异常: {e}")


# ==================== 程序入口 ====================
if __name__ == "__main__":
    main()
