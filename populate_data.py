import asyncio
from database.session import init_db

async def populate():
    await init_db()
    print("Success: Database initialized. Add vacancy posts via admin panel.")

if __name__ == "__main__":
    asyncio.run(populate())
