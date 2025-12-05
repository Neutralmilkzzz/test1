import asyncio
from app.db import SessionLocal
from app.email_processor import process_all
from app.settings import get_settings

settings = get_settings()


def main():
    print("worker started")
    asyncio.run(process_all(SessionLocal, settings.poll_interval_seconds))


if __name__ == "__main__":
    main()
