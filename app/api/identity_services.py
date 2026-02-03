"""
Identity and password management services.
Handles password reset flows with email integration.
Follows SOLID principle: Single Responsibility.
"""

import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from app.utils.logger import setup_logger

logger = setup_logger()


class PasswordResetService:
    """
    Manages password reset workflow using tokens and email.
    
    Flow:
    1. User requests reset -> generate token -> send email (no new deps needed)
    2. User clicks link -> validate token
    3. User enters new password -> update in DB
    
    Uses Gmail SMTP (credentials provided by user in .env).
    Tokens are stored in MongoDB with expiry.
    """
    
    def __init__(self, redis_client, mongo_handler, config):
        self.redis = redis_client
        self.mongo = mongo_handler
        self.config = config
        self.token_length = 32  # 256-bit token as hex

    def generate_reset_token(self) -> str:
        """Generate cryptographically secure reset token."""
        return secrets.token_urlsafe(self.token_length)

    async def request_password_reset(self, username: str, email: str) -> Tuple[bool, str]:
        """
        Initiate password reset: generate token, store in Redis, send email.
        Returns (success: bool, message: str)
        """
        # Generate token
        token = self.generate_reset_token()
        token_expiry_hours = self.config.email.password_reset_token_expiry_hours
        token_ttl_seconds = token_expiry_hours * 3600

        # Store token in Redis with expiry (no DB write needed)
        redis_key = f"password_reset_token:{username}"
        await self.redis.setex(redis_key, token_ttl_seconds, token)

        # Send email with reset link
        reset_url = f"https://careerpilot.chickenkiller.com/reset-password?token={token}&username={username}"
        try:
            await self._send_reset_email(email, username, reset_url)
            logger.info(
                f"Password reset email sent to '{email}'",
                extra={"username": username, "email": email}
            )
            return True, f"Password reset link sent to {email}. Valid for {token_expiry_hours} hours."
        except Exception as e:
            logger.error(
                f"Failed to send reset email: {str(e)}",
                extra={"username": username, "email": email, "error": str(e)}
            )
            return False, "Failed to send reset email. Please try again."

    async def validate_reset_token(self, username: str, token: str) -> Tuple[bool, str]:
        """
        Validate that token matches stored token for user.
        Returns (valid: bool, message: str)
        """
        redis_key = f"password_reset_token:{username}"
        stored_token = await self.redis.get(redis_key)

        if not stored_token:
            return False, "Password reset link has expired."

        if stored_token != token:
            logger.warning(
                f"Invalid reset token attempt for '{username}'",
                extra={"username": username}
            )
            return False, "Invalid reset token."

        return True, "Token is valid."

    async def complete_password_reset(
        self, username: str, token: str, new_password: str
    ) -> Tuple[bool, str]:
        """
        Complete password reset: validate token, update password, clean up token.
        Password hashing is done in auth.py (not here—separation of concerns).
        Returns (success: bool, message: str)
        """
        # Validate token first
        valid, msg = await self.validate_reset_token(username, token)
        if not valid:
            return False, msg

        # Delete token (only one reset per token)
        redis_key = f"password_reset_token:{username}"
        await self.redis.delete(redis_key)

        # Update password in MongoDB (caller handles hashing)
        try:
            await self.mongo.update_user_password(username, new_password)
            logger.info(
                f"Password reset completed for '{username}'",
                extra={"username": username}
            )
            return True, "Password reset successfully. Please log in."
        except Exception as e:
            logger.error(
                f"Failed to update password: {str(e)}",
                extra={"username": username, "error": str(e)}
            )
            return False, "Failed to update password. Please try again."

    async def _send_reset_email(self, recipient_email: str, username: str, reset_url: str) -> None:
        """
        Send password reset email via Gmail SMTP.
        Uses credentials from .env (GMAIL_SENDER_EMAIL, GMAIL_APP_PASSWORD).
        No new dependencies—uses Python's smtplib.
        """
        subject = "Password Reset Request - CareerPilot"
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Password Reset Request</h2>
                <p>Hello {username},</p>
                <p>We received a request to reset your password. Click the link below to proceed:</p>
                <p><a href="{reset_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
                <p>Or copy this link: <code>{reset_url}</code></p>
                <p>This link expires in {self.config.email.password_reset_token_expiry_hours} hours.</p>
                <hr>
                <p style="color: #666; font-size: 12px;">If you didn't request this, please ignore this email.</p>
            </body>
        </html>
        """

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.config.email.sender_email
            msg["To"] = recipient_email

            msg.attach(MIMEText(html_body, "html"))

            # Send via Gmail SMTP
            with smtplib.SMTP(self.config.email.smtp_host, self.config.email.smtp_port) as server:
                server.starttls()
                server.login(self.config.email.sender_email, self.config.email.sender_password)
                server.send_message(msg)

            logger.debug(
                f"Email sent to {recipient_email}",
                extra={"recipient": recipient_email}
            )
        except smtplib.SMTPAuthenticationError as e:
            logger.error(
                "Gmail authentication failed. Check GMAIL_SENDER_EMAIL and GMAIL_APP_PASSWORD.",
                extra={"error": str(e)}
            )
            raise
        except Exception as e:
            logger.error(f"SMTP error: {str(e)}", extra={"error": str(e)})
            raise
