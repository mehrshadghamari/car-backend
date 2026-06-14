from dataclasses import dataclass

from src.application.ports.external import NotificationPort
from src.application.use_cases.manage_users import ManageUsersUseCase
from src.domain.entities.user import User
from src.domain.exceptions import ValidationError
from src.infrastructure.auth.otp_store import OtpStore, generate_otp_code
from src.infrastructure.auth.phone import normalize_phone
from src.infrastructure.auth.tokens import AuthTokenService
from src.infrastructure.config import Settings


@dataclass
class OtpCreateResult:
    phone: str
    expires_in_sec: int
    sandbox: bool
    message: str


@dataclass
class OtpVerifyResult:
    access_token: str
    user: User


class OtpAuthUseCase:
    def __init__(
        self,
        settings: Settings,
        otp_store: OtpStore,
        token_service: AuthTokenService,
        users: ManageUsersUseCase,
        notification: NotificationPort,
    ):
        self._settings = settings
        self._otp_store = otp_store
        self._token_service = token_service
        self._users = users
        self._notification = notification

    async def create_otp(self, phone: str) -> OtpCreateResult:
        try:
            normalized = normalize_phone(phone)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        if self._settings.otp_sandbox:
            code = self._settings.otp_sandbox_code
        else:
            code = generate_otp_code(self._settings.otp_code_length)

        try:
            await self._otp_store.save(normalized, code, self._settings.otp_ttl_sec)
        except Exception:
            if not self._settings.otp_sandbox:
                raise

        if self._settings.otp_sandbox:
            message = "حالت آزمایشی — پیامک ارسال نمی‌شود. کد ورود: 11111"
        else:
            sms_text = f"کد ورود شما: {code}"
            await self._notification.send_opportunity_sms(normalized, sms_text)
            message = "کد تأیید با پیامک ارسال شد"

        return OtpCreateResult(
            phone=normalized,
            expires_in_sec=self._settings.otp_ttl_sec,
            sandbox=self._settings.otp_sandbox,
            message=message,
        )

    async def verify_otp(self, phone: str, code: str, first_name: str | None = None) -> OtpVerifyResult:
        try:
            normalized = normalize_phone(phone)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        submitted = (code or "").strip()
        if not submitted:
            raise ValidationError("کد تأیید را وارد کنید")

        sandbox_ok = (
            self._settings.otp_sandbox
            and submitted == self._settings.otp_sandbox_code
        )
        if not sandbox_ok:
            try:
                stored = await self._otp_store.get(normalized)
            except Exception as exc:
                raise ValidationError(
                    "سرویس تأیید موقتاً در دسترس نیست — لطفاً چند لحظه بعد دوباره تلاش کنید"
                ) from exc
            if not stored or stored != submitted:
                raise ValidationError("کد تأیید نامعتبر یا منقضی شده است")
            try:
                await self._otp_store.delete(normalized)
            except Exception:
                pass

        user = await self._users.get_or_create_by_phone(
            phone=normalized,
            source_channel="user_app",
            first_name=first_name,
        )
        token = self._token_service.create_access_token(user.id, user.phone)
        return OtpVerifyResult(access_token=token, user=user)
