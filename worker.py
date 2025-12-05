import asyncio
from app.db import Base, engine, SessionLocal
from app.email_processor import process_all
from app.settings import get_settings

settings = get_settings()


def main():
    print("worker started")
    # Ensure tables exist in worker container (useful when web hasn't initialized yet)
    Base.metadata.create_all(bind=engine)
    asyncio.run(process_all(SessionLocal, settings.poll_interval_seconds, run_once=settings.poll_run_once))


if __name__ == "__main__":
    main()
