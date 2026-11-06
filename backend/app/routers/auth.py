from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from ..deps import DB, CurrentUser, client_ip, login_limit
from ..models import User
from ..schemas import LoginIn, TokenOut, UserOut
from ..security import DUMMY_HASH, create_token, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: DB, request: Request):
    email = body.email.lower().strip()
    key = f"{client_ip(request)}|{email}"
    if login_limit.full(key):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Слишком много попыток входа, подождите 15 минут")
    user = db.scalar(select(User).where(User.email == email))
    # Хеш считаем и для несуществующего e-mail: по времени ответа нельзя узнать, есть ли такой пользователь
    ok = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not ok:
        login_limit.add(key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный e-mail или пароль")
    login_limit.reset(key)
    return TokenOut(access_token=create_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user
