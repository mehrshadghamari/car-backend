from uuid import UUID

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from src.domain.exceptions import ValidationError


class AuthTokenService:
    def __init__(self, secret_key: str, max_age_sec: int = 604800):
        self._serializer = URLSafeTimedSerializer(secret_key, salt="car-user-auth")
        self._max_age_sec = max_age_sec

    def create_access_token(self, user_id: UUID, phone: str) -> str:
        return self._serializer.dumps({"sub": str(user_id), "phone": phone})

    def decode_access_token(self, token: str) -> tuple[UUID, str]:
        try:
            data = self._serializer.loads(token, max_age=self._max_age_sec)
        except SignatureExpired as exc:
            raise ValidationError("نشست شما منقضی شده — دوباره وارد شوید") from exc
        except BadSignature as exc:
            raise ValidationError("نشست نامعتبر است") from exc
        try:
            return UUID(data["sub"]), data["phone"]
        except (KeyError, ValueError, TypeError) as exc:
            raise ValidationError("Invalid session token") from exc
