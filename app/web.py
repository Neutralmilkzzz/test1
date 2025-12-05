from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db import get_db
from app import models
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    encrypt_secret,
)
from app.settings import get_settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


def _flash(request: Request, text: str, category: str = "success"):
    request.session["flash"] = {"text": text, "category": category}


def _pop_flash(request: Request):
    return request.session.pop("flash", None)


def _current_user(request: Request, db: Session | None):
    token = request.session.get("token")
    if not token:
        return None
    user_id = decode_access_token(token)
    if not user_id:
        return None
    if not db:
        return None
    return db.query(models.User).filter(models.User.id == user_id).first()


def _require_user(request: Request, db: Session):
    user = _current_user(request, db)
    if not user:
        raise RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return user


@router.get("/")
async def root(request: Request):
    token = request.session.get("token")
    if token:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login")
async def login_page(request: Request):
    flash = _pop_flash(request)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "message": flash["text"] if flash else None, "message_type": flash["category"] if flash else None, "user": _current_user(request, None)},
    )


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db), email: str = Form(...), password: str = Form(...)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        _flash(request, "账号或密码错误", "error")
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    token = create_access_token(user.id)
    request.session["token"] = token
    _flash(request, "登录成功", "success")
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/register")
async def register_page(request: Request):
    flash = _pop_flash(request)
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "message": flash["text"] if flash else None, "message_type": flash["category"] if flash else None, "user": _current_user(request, None)},
    )


@router.post("/register")
async def register(request: Request, db: Session = Depends(get_db), email: str = Form(...), password: str = Form(...)):
    exists = db.query(models.User).filter(models.User.email == email).first()
    if exists:
        _flash(request, "邮箱已注册", "error")
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)
    user = models.User(email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    request.session["token"] = token
    _flash(request, "注册成功", "success")
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/dashboard")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    flash = _pop_flash(request)
    user = _current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    accounts = db.query(models.EmailAccount).filter(models.EmailAccount.user_id == user.id).order_by(models.EmailAccount.created_at.desc()).all()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "accounts": accounts,
            "message": flash["text"] if flash else None,
            "message_type": flash["category"] if flash else None,
            "defaults": {
                "imap_host": settings.imap_host,
                "imap_port": settings.imap_port,
                "smtp_host": settings.smtp_host,
                "smtp_port": settings.smtp_port,
            },
        },
    )


@router.post("/accounts/create")
async def create_account(
    request: Request,
    db: Session = Depends(get_db),
    login_email: str = Form(...),
    app_password: str = Form(...),
    destination_email: str = Form(...),
    imap_host: str | None = Form(None),
    imap_port: int | None = Form(None),
    smtp_host: str | None = Form(None),
    smtp_port: int | None = Form(None),
):
    user = _current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    acct = models.EmailAccount(
        user_id=user.id,
        login_email=login_email,
        app_password_enc=encrypt_secret(app_password),
        destination_email=destination_email,
        imap_host=imap_host or settings.imap_host,
        imap_port=imap_port or settings.imap_port,
        smtp_host=smtp_host or settings.smtp_host,
        smtp_port=smtp_port or settings.smtp_port,
    )
    db.add(acct)
    db.commit()
    _flash(request, "账号已保存并开始轮询", "success")
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/accounts/{account_id}/delete")
async def delete_account(request: Request, account_id: str, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    acct = db.query(models.EmailAccount).filter(models.EmailAccount.id == account_id, models.EmailAccount.user_id == user.id).first()
    if not acct:
        _flash(request, "未找到该账号", "error")
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    db.delete(acct)
    db.commit()
    _flash(request, "已删除账号并停止服务", "success")
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
