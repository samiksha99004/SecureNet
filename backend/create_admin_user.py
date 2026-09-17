"""Create an admin test user for IDS control testing"""
import asyncio
import sys
from sqlalchemy import select
from app.db.base import get_db
from app.models.user import User, UserRole, AccountStatus
from app.core.security import hash_password

async def create_admin_user():
    """Create admin test user"""
    async for db in get_db():
        # Check if user exists
        result = await db.execute(
            select(User).where(User.email == "admin@securenet.com")
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update to admin role
            existing.role = UserRole.ADMIN
            existing.account_status = AccountStatus.ACTIVE
            await db.commit()
            print(f"✓ Updated existing user to admin role: admin@securenet.com")
        else:
            # Create new admin user
            admin_user = User(
                email="admin@securenet.com",
                full_name="Admin Test User",
                password_hash=hash_password("AdminPassword123!"),
                role=UserRole.ADMIN,
                account_status=AccountStatus.ACTIVE
            )
            db.add(admin_user)
            await db.commit()
            print(f"✓ Created new admin user: admin@securenet.com")
        
        print(f"  Email: admin@securenet.com")
        print(f"  Password: AdminPassword123!")
        print(f"  Role: admin")
        break

if __name__ == "__main__":
    asyncio.run(create_admin_user())
