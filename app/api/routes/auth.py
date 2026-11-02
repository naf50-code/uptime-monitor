from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, SecretStr
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_account, get_db_session
from app.core.security import (
    create_access_token,
    dummy_password_hash,
    hash_password,
    verify_password,
)
from app.db.models import Account

router = APIRouter(prefix="/auth", tags=["authentication"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


class Credentials(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=12, max_length=128)


class AccountResponse(BaseModel):
    id: str
    email: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1800


@router.post("/register", response_model=AccountResponse, status_code=201)
async def register(credentials: Credentials, session: DbSession) -> AccountResponse:
    account = Account(
        email=str(credentials.email).lower(),
        password_hash=hash_password(credentials.password.get_secret_value()),
    )
    session.add(account)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from exc
    await session.refresh(account)
    return AccountResponse(id=str(account.id), email=account.email, role=account.role)


@router.post("/login", response_model=TokenResponse)
async def login(credentials: Credentials, session: DbSession) -> TokenResponse:
    result = await session.execute(
        select(Account).where(Account.email == str(credentials.email).lower())
    )
    account = result.scalar_one_or_none()
    password = credentials.password.get_secret_value()
    stored_hash = account.password_hash if account is not None else dummy_password_hash
    password_matches = verify_password(password, stored_hash)

    if account is None or not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(access_token=create_access_token(account.id))


@router.get("/me", response_model=AccountResponse)
async def get_me(account: Account = Depends(get_current_account)) -> AccountResponse:
    return AccountResponse(id=str(account.id), email=account.email, role=account.role)
