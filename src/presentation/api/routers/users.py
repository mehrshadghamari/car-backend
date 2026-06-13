from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.application.use_cases.manage_users import CreateUserInput, ManageUsersUseCase, UpdateUserInput
from src.domain.exceptions import DomainError, EntityNotFoundError, ValidationError
from src.presentation.api.schemas import UserCreate, UserResponse, UserUpdate
from src.presentation.dependencies import get_users_use_case

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    body: UserCreate,
    use_case: ManageUsersUseCase = Depends(get_users_use_case),
):
    try:
        user = await use_case.create(
            CreateUserInput(
                phone=body.phone,
                source_channel=body.source_channel,
                first_name=body.first_name,
                last_name=body.last_name,
            )
        )
        return UserResponse(
            id=user.id,
            phone=user.phone,
            source_channel=user.source_channel,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            created_at=user.created_at,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    use_case: ManageUsersUseCase = Depends(get_users_use_case),
):
    users = await use_case.list(skip=skip, limit=limit)
    return [
        UserResponse(
            id=u.id,
            phone=u.phone,
            source_channel=u.source_channel,
            first_name=u.first_name,
            last_name=u.last_name,
            is_active=u.is_active,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    use_case: ManageUsersUseCase = Depends(get_users_use_case),
):
    try:
        user = await use_case.get(user_id)
        return UserResponse(
            id=user.id,
            phone=user.phone,
            source_channel=user.source_channel,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            created_at=user.created_at,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    use_case: ManageUsersUseCase = Depends(get_users_use_case),
):
    try:
        user = await use_case.update(
            user_id,
            UpdateUserInput(
                phone=body.phone,
                source_channel=body.source_channel,
                first_name=body.first_name,
                last_name=body.last_name,
                is_active=body.is_active,
            ),
        )
        return UserResponse(
            id=user.id,
            phone=user.phone,
            source_channel=user.source_channel,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            created_at=user.created_at,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    use_case: ManageUsersUseCase = Depends(get_users_use_case),
):
    try:
        await use_case.delete(user_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
