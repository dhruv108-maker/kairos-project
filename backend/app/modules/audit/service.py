"""Append-only audit events; callers add events within their business transaction."""
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent
from app.models.institutions import Institution, InstitutionMembership


class AuditAccessError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def record(self, actor_id: str | None, institution_id: str | None, action: str,
               entity_type: str, entity_id: str | None, details: dict | None = None) -> AuditEvent:
        event = AuditEvent(id=str(uuid4()), actor_account_id=actor_id, institution_id=institution_id,
                           action=action, entity_type=entity_type, entity_id=entity_id, details=details)
        self.db.add(event)
        return event

    async def list_for_institution(self, institution_id: str, actor_id: str, limit: int, offset: int,
                                   action: str | None = None, entity_type: str | None = None) -> list[AuditEvent]:
        institution = await self.db.get(Institution, institution_id)
        membership = await self.db.get(InstitutionMembership, (institution_id, actor_id))
        if institution is None or institution.status != "ACTIVE" or membership is None or membership.status != "ACTIVE" or membership.role != "INSTITUTION_ADMIN":
            raise AuditAccessError(403, "Institution administrator permission required")
        query = select(AuditEvent).where(AuditEvent.institution_id == institution_id)
        if action:
            query = query.where(AuditEvent.action == action)
        if entity_type:
            query = query.where(AuditEvent.entity_type == entity_type)
        result = await self.db.execute(query.order_by(AuditEvent.created_at.desc()).limit(limit).offset(offset))
        return list(result.scalars().all())
