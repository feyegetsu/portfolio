"""Текущий пользователь по токену, проверка роли и доступа к сайту."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .deps import DB
from .models import User
from .security import decode_token
from .sites import SITES

_bearer = HTTPBearer(auto_error=False)
ROLE_LEVEL = {"staff": 1, "admin": 2, "owner": 3}


def current_user(db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> User:
    claims = decode_token(creds.credentials) if creds else None
    user = db.get(User, claims[0]) if claims else None
    if not user or user.token_version != claims[1]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Нужно войти", headers={"WWW-Authenticate": "Bearer"})
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require(role: str):
    """Зависимость «минимальная роль»: staff < admin < owner."""

    def check(user: CurrentUser) -> User:
        if ROLE_LEVEL[user.role] < ROLE_LEVEL[role]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
        return user

    return check


def allowed_sites(user: User) -> list[str]:
    return list(SITES) if user.sites is None else [s for s in user.sites if s in SITES]


def check_site_access(user: User, site: str) -> None:
    if site not in allowed_sites(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Нет доступа к этому сайту")
