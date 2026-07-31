# 邮件发送服务（SMTP）
# 当前形态：send_password_reset_email 为 stub。
#   - SMTP 未配置（settings.smtp_host 为空）时打日志并返回 False，
#     由调用方（forgot 接口）按 dev 模式回传明文 reset_token；
#   - 配置 SMTP 后即真实发送：SMTP_PORT 465 走 SMTP_SSL，587 走 STARTTLS，
#     其他端口走明文 SMTP（不加密）。
import logging
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

from app.config import settings

logger = logging.getLogger(__name__)


def smtp_configured() -> bool:
    """SMTP 是否已配置（以 smtp_host 是否为空判断）。"""
    return bool(settings.smtp_host)


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """发送密码重置邮件。成功返回 True；SMTP 未配置或发送失败返回 False。"""
    if not smtp_configured():
        logger.info("[邮件未配置] 跳过发送密码重置邮件 to=%s（token 由调用方按 dev 模式处理）", to_email)
        return False

    from_email = settings.smtp_from or settings.smtp_user
    subject = "【MBookTI】密码重置"
    body = (
        "您好，\n\n"
        "您正在重置 MBookTI 账户密码。请打开以下链接完成重置：\n\n"
        f"/reset-password?token={reset_token}\n\n"
        "该链接 30 分钟内有效，且只能使用一次。如非本人操作，请忽略本邮件。\n"
    )

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = formataddr(("MBookTI", from_email))
    msg["To"] = to_email

    try:
        host, port = settings.smtp_host, settings.smtp_port
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            if port == 587:
                server.starttls()
        with server:
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(from_email, [to_email], msg.as_string())
        logger.info("密码重置邮件已发送 to=%s", to_email)
        return True
    except Exception:
        logger.exception("密码重置邮件发送失败 to=%s", to_email)
        return False
