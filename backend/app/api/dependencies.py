from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import TokenError, decode_token
from app.models.academic import Account
from app.modules.identity.service import IdentityService

bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_account(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> Account:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        claims = decode_token(credentials.credentials, "access")
    except TokenError:
        raise unauthorized from None

    account = await IdentityService(db).get_account(claims["sub"])
    if account is None or not account.is_active or not account.is_verified:
        raise unauthorized
    if claims.get("ver", 0) != account.token_version:
        raise unauthorized
    return account


CurrentAccount = Annotated[Account, Depends(get_current_account)]


async def account_roles(db: AsyncSession, account_id: str) -> list[str]:
    return await IdentityService(db).roles_for(account_id)


async def require_role(db: AsyncSession, account: Account, role_name: str) -> None:
    roles = await account_roles(db, account.id)
    if role_name not in roles:
        raise HTTPException(status_code=403, detail="Insufficient role")
