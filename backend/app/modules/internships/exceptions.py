"""Internship-specific domain exceptions."""
from app.modules.shared.exceptions import DomainConflictError, DomainValidationError, InvalidStateTransitionError, ResourceNotFoundError

class InternshipNotFoundError(ResourceNotFoundError):
    code = "internship_not_found"
class ProviderNotFoundError(ResourceNotFoundError):
    code = "provider_not_found"
class ApplicationNotFoundError(ResourceNotFoundError):
    code = "application_not_found"
class PlacementNotFoundError(ResourceNotFoundError):
    code = "placement_not_found"
class DuplicateApplicationError(DomainConflictError):
    code = "duplicate_application"
class InternshipConflictError(DomainConflictError):
    code = "internship_conflict"
class InternshipValidationError(DomainValidationError):
    code = "internship_validation_error"
class InvalidInternshipStateTransitionError(InvalidStateTransitionError):
    code = "invalid_internship_state_transition"
