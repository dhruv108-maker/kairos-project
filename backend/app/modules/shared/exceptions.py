"""Shared domain exception hierarchy."""

class KairosDomainError(Exception):
    """Base class for expected domain errors."""
    status_code = 400
    code = "domain_error"

class ResourceNotFoundError(KairosDomainError):
    status_code = 404
    code = "resource_not_found"

class DomainConflictError(KairosDomainError):
    status_code = 409
    code = "domain_conflict"

class InvalidStateTransitionError(DomainConflictError):
    code = "invalid_state_transition"

class DomainValidationError(KairosDomainError):
    status_code = 422
    code = "domain_validation_error"

class PermissionDeniedError(KairosDomainError):
    status_code = 403
    code = "permission_denied"
