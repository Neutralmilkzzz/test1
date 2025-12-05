from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.db import Base, engine
from app import auth, accounts, summaries, web
from app.settings import get_settings

Base.metadata.create_all(bind=engine)

settings = get_settings()
app = FastAPI(title="163 邮件总结服务")

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="session",
    max_age=60 * 60 * 24 * 7,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(web.router)
app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(summaries.router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
