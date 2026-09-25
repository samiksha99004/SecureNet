"""Setup check (run by SETUP.ps1 from backend/): configuration, cloud database, email delivery.

Read-only: it only counts users. Never prints secrets.
"""

import asyncio
import os
import sys
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text  # noqa: E402

from app.core.config import settings  # noqa: E402  (exits with a readable message if .env is incomplete)
from app.db.base import engine  # noqa: E402
from app.utils.email import email_delivery_status  # noqa: E402

EMAIL_STATUS = {
    "enabled": "configured - confirm with Settings > Notifications > Send test email",
    "disabled": "TURNED OFF - set EMAIL_ENABLED=true in backend/.env (sign-up needs email)",
    "misconfigured": "NOT CONFIGURED - put a real Gmail address + App Password in backend/.env",
}


async def check_database() -> None:
    host = urlsplit(settings.DATABASE_URL).hostname
    try:
        async with engine.connect() as conn:
            users = (await conn.execute(text("select count(*) from users"))).scalar()
    except Exception as exc:  # noqa: BLE001 - report any connection problem plainly
        sys.exit(f"Database: cannot connect to {host}: {exc.__class__.__name__}: {exc}\n"
                 "Check the internet connection and DATABASE_URL in backend/.env.")
    finally:
        await engine.dispose()
    print(f"Database: connected to {host} ({users} registered user(s))")


asyncio.run(check_database())
print("Email:", EMAIL_STATUS[email_delivery_status()])
