"""Container entrypoint: auto-seed if DB is empty, then start uvicorn."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.constants import DATABASE_URL
from scripts.seed import main as seed_main


async def db_user_count() -> int:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(DATABASE_URL, echo=False)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM users"))
            return result.scalar_one()
    except Exception:
        return 0
    finally:
        await engine.dispose()


def main() -> None:
    count = asyncio.run(db_user_count())

    if count == 0:
        print("[entrypoint] Database is empty — running seed script...")
        asyncio.run(seed_main())
        print("[entrypoint] Seeding complete.")
    else:
        print(f"[entrypoint] Database already contains {count} user(s) — skipping seed.")

    print("[entrypoint] Starting uvicorn...")
    os.execvp(sys.executable, [sys.executable, "-m", "uvicorn", "app.main:app",
                                "--host", "0.0.0.0", "--port", "8000", "--reload"])


if __name__ == "__main__":
    main()
