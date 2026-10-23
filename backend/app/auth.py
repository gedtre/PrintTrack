import hashlib
import secrets
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session as DBSession
from .config import settings
from .db import get_db
from .models import AuditLog, LoginAttempt, SessionToken, User, now
from .schemas import Language, Login, UserCreate, UserUpdate

router = APIRouter(prefix="/api")
passwords = PasswordHash.recommended()
# Comparable-cost check even when a username does not exist.
DUMMY_HASH = passwords.hash(secrets.token_urlsafe(32))


def fail(code, status=400):
    raise HTTPException(status, detail=code)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def current_user(request: Request, db: DBSession = Depends(get_db)):
    token = request.cookies.get("printtrack_session", "")
    session = db.get(SessionToken, digest(token)) if token else None
    if not session or session.expires <= now():
        fail("UNAUTHORIZED", 401)
    user = db.get(User, session.user_id)
    if not user or not user.active:
        fail("UNAUTHORIZED", 401)
    return user


def editor(user: User = Depends(current_user)):
    if user.role not in ("admin", "it"):
        fail("FORBIDDEN", 403)
    return user


def admin(user: User = Depends(current_user)):
    if user.role != "admin":
        fail("FORBIDDEN", 403)
    return user


def user_json(user):
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "language": user.language,
        "active": user.active,
    }


@router.post("/auth/login")
def login(
    data: Login, request: Request, response: Response, db: DBSession = Depends(get_db)
):
    # Per-account persisted limiter works across workers. Never trust forwarded IP headers.
    key = digest(data.username.lower())
    db.execute(
        insert(LoginAttempt)
        .values(key=key, failures=0, window_start=now())
        .on_conflict_do_nothing()
    )
    attempt = db.scalar(
        select(LoginAttempt).where(LoginAttempt.key == key).with_for_update()
    )
    if attempt.window_start < now() - timedelta(minutes=15):
        attempt.failures = 0
        attempt.window_start = now()
    if attempt.failures >= 10:
        db.commit()
        fail("RATE_LIMITED", 429)
    user = db.scalar(select(User).where(User.username == data.username))
    valid = passwords.verify(data.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid or not user.active:
        attempt.failures += 1
        db.commit()
        fail("INVALID_LOGIN", 401)
    attempt.failures = 0
    old = request.cookies.get("printtrack_session")
    if old:
        previous = db.get(SessionToken, digest(old))
        if previous:
            db.delete(previous)
    token = secrets.token_urlsafe(48)
    db.add(
        SessionToken(
            token_hash=digest(token),
            user_id=user.id,
            expires=now() + timedelta(hours=settings.session_hours),
        )
    )
    db.add(AuditLog(user_id=user.id, action="login", entity="users", entity_id=user.id))
    db.commit()
    response.set_cookie(
        "printtrack_session",
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        max_age=settings.session_hours * 3600,
        path="/api",
    )
    return user_json(user)


@router.post("/auth/logout")
def logout(
    request: Request,
    response: Response,
    db: DBSession = Depends(get_db),
    user=Depends(current_user),
):
    token = db.get(SessionToken, digest(request.cookies["printtrack_session"]))
    db.delete(token)
    db.commit()
    response.delete_cookie(
        "printtrack_session",
        path="/api",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="strict",
    )
    return {"ok": True}


@router.get("/auth/me")
def me(user=Depends(current_user)):
    return user_json(user)


@router.patch("/auth/language")
def language(
    data: Language, db: DBSession = Depends(get_db), user=Depends(current_user)
):
    user.language = data.language
    db.commit()
    return user_json(user)


@router.get("/users")
def users(db: DBSession = Depends(get_db), user=Depends(admin)):
    return [user_json(u) for u in db.scalars(select(User).order_by(User.id))]


@router.post("/users", status_code=201)
def create_user(data: UserCreate, db: DBSession = Depends(get_db), user=Depends(admin)):
    obj = User(
        username=data.username,
        password_hash=passwords.hash(data.password),
        role=data.role,
    )
    db.add(obj)
    db.flush()
    db.add(AuditLog(user_id=user.id, action="create", entity="users", entity_id=obj.id))
    db.commit()
    return user_json(obj)


@router.put("/users/{user_id}")
def update_user(
    user_id: int, data: UserUpdate, db: DBSession = Depends(get_db), user=Depends(admin)
):
    # A user cannot accidentally lock their own administrator account out.
    if user_id == user.id and (not data.active or data.role != "admin"):
        fail("SELF_DEMOTION")
    obj = db.get(User, user_id)
    if not obj:
        fail("NOT_FOUND", 404)
    obj.role, obj.active = data.role, data.active
    db.add(AuditLog(user_id=user.id, action="update", entity="users", entity_id=obj.id))
    db.commit()
    return user_json(obj)
