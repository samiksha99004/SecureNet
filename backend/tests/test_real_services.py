"""No local database and no faked emails."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.utils import email as email_mod


def _settings(**overrides):
    base = {"JWT_SECRET": "x" * 40, "ALLOW_LOCAL_DATABASE": False, "_env_file": None}
    return Settings(**{**base, **overrides})


@pytest.mark.parametrize("url", [
    "sqlite+aiosqlite:///securenet.db",
    "postgresql+asyncpg://u:p@localhost:5432/securenet",
    "postgresql+asyncpg://u:p@127.0.0.1/securenet",
])
def test_local_database_is_refused(url):
    with pytest.raises(ValidationError, match="local database"):
        _settings(DATABASE_URL=url)


def test_cloud_database_is_accepted_and_sender_defaults_to_smtp_user():
    s = _settings(DATABASE_URL="postgresql+asyncpg://u:p@ep-x.aws.neon.tech/neondb?ssl=require",
                  SMTP_USER="owner@gmail.com")
    assert s.SMTP_FROM_EMAIL == "owner@gmail.com"


@pytest.mark.parametrize("user,password,expected", [
    ("your-email@gmail.com", "abcdefghijklmnop", "misconfigured"),
    ("owner@gmail.com", "your-app-password", "misconfigured"),
    ("owner@gmail.com", "", "misconfigured"),
    ("owner@gmail.com", "abcdefghijklmnop", "enabled"),
])
def test_placeholder_credentials_are_detected(monkeypatch, user, password, expected):
    monkeypatch.setattr(settings, "EMAIL_ENABLED", True)
    monkeypatch.setattr(settings, "SMTP_USER", user)
    monkeypatch.setattr(settings, "SMTP_PASSWORD", password)
    assert email_mod.email_delivery_status() == expected


async def test_disabled_email_raises_instead_of_pretending(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_ENABLED", False)
    with pytest.raises(email_mod.EmailDeliveryError, match="EMAIL_ENABLED"):
        await email_mod.send_otp_email("someone@gmail.com", "123456")


async def test_signup_without_email_setup_is_refused(client):
    r = await client.post("/api/auth/signup", json={
        "fullName": "Real Person", "email": "real.person@gmail.com", "phoneNumber": "+919876543210",
    })
    assert r.status_code == 503
    assert "can't send emails yet" in r.json()["message"] and ".env" not in r.json()["message"]
    # nothing half-created: no pending account, no code to verify
    r2 = await client.post("/api/auth/otp/verify", json={"email": "real.person@gmail.com", "otp": "123456"})
    assert r2.status_code == 400 and "No verification code" in r2.json()["message"]
