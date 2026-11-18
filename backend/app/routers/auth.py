from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select

from ..deps import DB, CurrentUser, client_ip, login_limit
from ..models import User
from ..schemas import LoginIn, PasswordIn, TokenOut, UserOut
from ..security import DUMMY_HASH, create_token, hash_password, verify_password

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
    return TokenOut(access_token=create_token(user.id, user.token_version))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.post("/logout", status_code=204)
def logout(user: CurrentUser, db: DB):
    """Выход на сервере: все выданные пользователю токены, в том числе украденные, перестают действовать."""
    user.token_version += 1
    db.commit()
    return Response(status_code=204)


@router.post("/password", response_model=TokenOut)
def change_password(body: PasswordIn, user: CurrentUser, db: DB, request: Request):
    """Смена своего пароля. Старые токены гаснут, в ответе — новый токен для этой сессии."""
    key = f"{client_ip(request)}|{user.email}"
    if login_limit.full(key):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Слишком много попыток, подождите 15 минут")
    if not verify_password(body.current_password, user.password_hash):
        login_limit.add(key)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Текущий пароль указан неверно")
    user.password_hash = hash_password(body.new_password)
    user.token_version += 1
    db.commit()
    return TokenOut(access_token=create_token(user.id, user.token_version))
