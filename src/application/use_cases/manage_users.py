from dataclasses import dataclass
from uuid import UUID, uuid4

from src.application.ports.repositories import UserRepository
from src.domain.entities.user import User
from src.domain.exceptions import EntityNotFoundError, ValidationError


@dataclass
class CreateUserInput:
    phone: str
    source_channel: str
    first_name: str | None = None
    last_name: str | None = None


@dataclass
class UpdateUserInput:
    phone: str | None = None
    source_channel: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool | None = None


class ManageUsersUseCase:
    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo

    async def create(self, input_dto: CreateUserInput) -> User:
        if not input_dto.phone:
            raise ValidationError("Phone is required")
        existing = await self._user_repo.get_by_phone(input_dto.phone)
        if existing:
            raise ValidationError(f"User with phone {input_dto.phone} already exists")
        user = User(
            id=uuid4(),
            phone=input_dto.phone,
            source_channel=input_dto.source_channel,
            first_name=input_dto.first_name,
            last_name=input_dto.last_name,
        )
        return await self._user_repo.save(user)

    async def get(self, user_id: UUID) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError(f"User {user_id} not found")
        return user

    async def get_by_phone(self, phone: str) -> User | None:
        return await self._user_repo.get_by_phone(phone)

    async def get_or_create_by_phone(
        self,
        phone: str,
        source_channel: str = "user_app",
        first_name: str | None = None,
    ) -> User:
        existing = await self._user_repo.get_by_phone(phone)
        if existing:
            return existing
        return await self.create(
            CreateUserInput(
                phone=phone,
                source_channel=source_channel,
                first_name=first_name,
            )
        )

    async def list(self, skip: int = 0, limit: int = 100) -> list[User]:
        return await self._user_repo.list_all(skip=skip, limit=limit)

    async def update(self, user_id: UUID, input_dto: UpdateUserInput) -> User:
        user = await self.get(user_id)
        if input_dto.phone is not None:
            user.phone = input_dto.phone
        if input_dto.source_channel is not None:
            user.source_channel = input_dto.source_channel
        if input_dto.first_name is not None:
            user.first_name = input_dto.first_name
        if input_dto.last_name is not None:
            user.last_name = input_dto.last_name
        if input_dto.is_active is not None:
            user.is_active = input_dto.is_active
        return await self._user_repo.save(user)

    async def delete(self, user_id: UUID) -> None:
        if not await self._user_repo.delete(user_id):
            raise EntityNotFoundError(f"User {user_id} not found")
