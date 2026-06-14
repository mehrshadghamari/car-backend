import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from src.application.use_cases.otp_auth import OtpAuthUseCase
from src.domain.entities.user import User
from src.domain.exceptions import ValidationError
from src.presentation.api.schemas import (
    OtpCreateRequest,
    OtpCreateResponse,
    OtpVerifyRequest,
    OtpVerifyResponse,
    UserResponse,
)
from src.presentation.dependencies import get_otp_auth_use_case

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        phone=user.phone,
        source_channel=user.source_channel or "user_app",
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=True if user.is_active is None else user.is_active,
        created_at=user.created_at,
    )


@router.post("/otp/create", response_model=OtpCreateResponse)
async def create_otp(
    body: OtpCreateRequest,
    use_case: OtpAuthUseCase = Depends(get_otp_auth_use_case),
):
    try:
        result = await use_case.create_otp(body.phone)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (SQLAlchemyError, aioredis.RedisError, OSError) as exc:
        logger.exception("OTP create failed")
        raise HTTPException(
            status_code=503,
            detail="سرویس ورود موقتاً در دسترس نیست — لطفاً چند لحظه بعد دوباره تلاش کنید",
        ) from exc
    return OtpCreateResponse(
        phone=result.phone,
        expires_in_sec=result.expires_in_sec,
        sandbox=result.sandbox,
        sandbox_code="11111" if result.sandbox else None,
        message=result.message,
    )


@router.post("/otp/verify", response_model=OtpVerifyResponse)
async def verify_otp(
    body: OtpVerifyRequest,
    use_case: OtpAuthUseCase = Depends(get_otp_auth_use_case),
):
    try:
        result = await use_case.verify_otp(body.phone, body.code, body.first_name)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (SQLAlchemyError, aioredis.RedisError, OSError) as exc:
        logger.exception("OTP verify failed for phone=%s", body.phone)
        raise HTTPException(
            status_code=503,
            detail="سرویس ورود موقتاً در دسترس نیست — لطفاً چند لحظه بعد دوباره تلاش کنید",
        ) from exc
    user = result.user
    return OtpVerifyResponse(
        access_token=result.access_token,
        token_type="bearer",
        user=_user_response(user),
    )
