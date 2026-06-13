class DomainError(Exception):
    """Base domain exception."""


class EntityNotFoundError(DomainError):
    pass


class ValidationError(DomainError):
    pass


class ExternalServiceError(DomainError):
    pass
