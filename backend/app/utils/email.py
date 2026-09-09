"""
SecureNet Backend — Email Utilities
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
from app.utils.logger import logger


async def send_otp_email(email: str, otp_code: str) -> None:
    """
    Send OTP verification email.
    In development, logs OTP instead of sending email if EMAIL_ENABLED=False.
    """
    if not settings.EMAIL_ENABLED:
        logger.info(f"[DEV] OTP for {email}: {otp_code}")
        return
    
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = f"{settings.APP_NAME} - Verification Code"
        message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        message["To"] = email
        
        text = f"""
        Your {settings.APP_NAME} verification code is: {otp_code}
        
        This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.
        
        If you didn't request this code, please ignore this email.
        """
        
        html = f"""
        <html>
          <body>
            <h2>{settings.APP_NAME} - Email Verification</h2>
            <p>Your verification code is:</p>
            <h1 style="font-size: 32px; letter-spacing: 8px; color: #4F46E5;">{otp_code}</h1>
            <p>This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.</p>
            <p>If you didn't request this code, please ignore this email.</p>
          </body>
        </html>
        """
        
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        message.attach(part1)
        message.attach(part2)
        
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, email, message.as_string())
        
        logger.info(f"OTP email sent to {email}")
    
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {e}")
        # In development, fall back to logging
        if settings.DEBUG:
            logger.info(f"[FALLBACK] OTP for {email}: {otp_code}")
        else:
            raise
