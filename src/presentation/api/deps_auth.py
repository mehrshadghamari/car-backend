from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.application.use_cases.manage_users import ManageUsersUseCase
from src.domain.entities.user import User
from src.domain.exceptions import EntityNotFoundError, ValidationError
from src.infrastructure.auth.tokens import AuthTokenService
from src.infrastructure.config import Settings, get_settings
from src.presentation.dependencies import get_users_use_case

_bearer = HTTPBearer(auto_error=False)


def get_token_service(settings: Settings = Depends(get_settings)) -> AuthTokenService:
    return AuthTokenService(settings.auth_secret_key, settings.auth_token_max_age_sec)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    token_service: AuthTokenService = Depends(get_token_service),
    users_uc: ManageUsersUseCase = Depends(get_users_use_case),
) -> User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="لطفاً وارد حساب کاربری شوید")
    try:
        user_id, _phone = token_service.decode_access_token(credentials.credentials)
    except ValidationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    try:
        return await users_uc.get(user_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
