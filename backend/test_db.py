import asyncio
from sqlalchemy import text
from app.db.base import AsyncSessionLocal

async def test():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text('SELECT version()'))
        row = result.fetchone()
        print('✓ PASS: PostgreSQL connection')
        print(f'  Version: {row[0].split()[1]}')

asyncio.run(test())
