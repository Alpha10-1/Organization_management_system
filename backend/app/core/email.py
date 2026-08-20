"""Zero-cost email sending.

By default this never talks to a paid provider. Every "sent" email is:
  1. written to the sent_emails table (so it can be viewed/audited in-app), and
  2. printed to the console/log.

That's enough to fully exercise password-reset and verification flows in
development or a small internal deployment without paying for anything.

If the operator later wants real delivery, setting SMTP_HOST (and friends)
in the environment makes send_email() additionally relay through that
SMTP server. This is entirely optional -- unset by default.
"""

import os
import smtplib
import sys
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.models.sent_email import SentEmail

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "no-reply@organization.local")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def send_email(db: Session, to_email: str, subject: str, body: str, kind: str = "generic") -> SentEmail:
    record = SentEmail(to_email=to_email, subject=subject, body=body, kind=kind)
    db.add(record)
    db.commit()
    db.refresh(record)

    print(f"[email:{kind}] to={to_email} subject={subject!r}\n{body}\n", file=sys.stderr)

    if SMTP_HOST:
        try:
            message = EmailMessage()
            message["From"] = SMTP_FROM
            message["To"] = to_email
            message["Subject"] = subject
            message.set_content(body)

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
                server.starttls()
                if SMTP_USER:
                    server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(message)
        except Exception as exc:  # pragma: no cover - best effort, never blocks the flow
            print(f"[email:{kind}] SMTP send failed, outbox record still saved: {exc}", file=sys.stderr)

    return record


def send_verification_email(db: Session, to_email: str, name: str, token: str) -> SentEmail:
    link = f"{FRONTEND_URL}/verify-email?token={token}"
    body = (
        f"Hi {name},\n\n"
        "Please verify your email address for the Organization Management System "
        f"by visiting:\n{link}\n\nThis link expires in 24 hours."
    )
    return send_email(db, to_email, "Verify your email address", body, kind="verification")


def send_password_reset_email(db: Session, to_email: str, name: str, token: str) -> SentEmail:
    link = f"{FRONTEND_URL}/reset-password?token={token}"
    body = (
        f"Hi {name},\n\n"
        "We received a request to reset your password. Visit the link below to "
        f"choose a new one:\n{link}\n\n"
        "This link expires in 1 hour. If you didn't request this, you can ignore this email."
    )
    return send_email(db, to_email, "Reset your password", body, kind="password_reset")


def send_portal_invite_email(db: Session, to_email: str, name: str, client_name: str, token: str) -> SentEmail:
    link = f"{FRONTEND_URL}/portal/set-password?token={token}"
    body = (
        f"Hi {name},\n\n"
        f"You've been invited to the client portal for {client_name}. "
        "Use the link below to set your password and log in:\n"
        f"{link}\n\nThis link expires in 24 hours."
    )
    return send_email(db, to_email, "You've been invited to the client portal", body, kind="portal_invite")


def send_portal_password_reset_email(db: Session, to_email: str, name: str, token: str) -> SentEmail:
    link = f"{FRONTEND_URL}/portal/reset-password?token={token}"
    body = (
        f"Hi {name},\n\n"
        "We received a request to reset your client portal password. Visit the link "
        f"below to choose a new one:\n{link}\n\n"
        "This link expires in 1 hour. If you didn't request this, you can ignore this email."
    )
    return send_email(db, to_email, "Reset your client portal password", body, kind="portal_password_reset")
