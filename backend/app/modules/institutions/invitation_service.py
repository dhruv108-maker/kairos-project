"""Institution invitation lifecycle with hashed, expiring, single-use tokens."""
from datetime import UTC, datetime, timedelta
from uuid import uuid4
import hmac
import secrets
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_token
from app.models.academic import Account, FacultyProfile, Department, School
from app.models.institutions import Institution, InstitutionInvitation, InstitutionMembership
from app.modules.audit.service import AuditService
from app.modules.institutions.service import InstitutionAccessError, InstitutionService
from app.services.email import send_institution_invitation_email


class InvitationWorkflowError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class InstitutionInvitationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.institutions = InstitutionService(db)

    async def invite(self, institution_id: str, actor_id: str, email: str, role: str):
        await self.institutions.require_admin(institution_id, actor_id)
        if role not in {"FACULTY", "MEMBER"}:
            raise InvitationWorkflowError(422, "Institution administrators may invite FACULTY or MEMBER roles only")
        normalized_email = email.strip().lower()
        institution = await self.db.get(Institution, institution_id)
        now = datetime.now(UTC).replace(tzinfo=None)
        result = await self.db.execute(select(InstitutionInvitation).where(
            InstitutionInvitation.institution_id == institution_id,
            InstitutionInvitation.email == normalized_email,
            InstitutionInvitation.accepted_at.is_(None),
            InstitutionInvitation.revoked_at.is_(None),
        ))
        for old in result.scalars().all():
            old.revoked_at = now
        raw_token = secrets.token_urlsafe(32)
        item = InstitutionInvitation(id=str(uuid4()), institution_id=institution_id, email=normalized_email,
            role=role, token_hash=hash_token(raw_token), expires_at=now + timedelta(days=7),
            invited_by_account_id=actor_id)
        self.db.add(item)
        AuditService(self.db).record(actor_id, institution_id, "institution.invitation_created",
            "institution_invitation", item.id, {"email": normalized_email, "role": role})
        await self.db.commit()
        await self.db.refresh(item)
        try:
            await send_institution_invitation_email(normalized_email, institution.name, role, raw_token)
        except Exception:
            item.revoked_at = datetime.now(UTC).replace(tzinfo=None)
            await self.db.commit()
            return item, False
        return item, True

    async def list_invitations(self, institution_id: str, actor_id: str):
        await self.institutions.require_admin(institution_id, actor_id)
        result = await self.db.execute(select(InstitutionInvitation).where(
            InstitutionInvitation.institution_id == institution_id
        ).order_by(InstitutionInvitation.created_at.desc()))
        return list(result.scalars().all())

    async def revoke(self, institution_id: str, actor_id: str, invitation_id: str):
        await self.institutions.require_admin(institution_id, actor_id)
        item = await self.db.get(InstitutionInvitation, invitation_id)
        if item is None or item.institution_id != institution_id:
            raise InvitationWorkflowError(404, "Invitation not found in this institution")
        if item.accepted_at is not None:
            raise InvitationWorkflowError(409, "An accepted invitation cannot be revoked")
        item.revoked_at = datetime.now(UTC).replace(tzinfo=None)
        AuditService(self.db).record(actor_id, institution_id, "institution.invitation_revoked",
            "institution_invitation", item.id, {"email": item.email})
        await self.db.commit()

    async def accept(self, account_id: str, raw_token: str):
        account = await self.db.get(Account, account_id)
        if account is None or not account.is_active or not account.is_verified:
            raise InvitationWorkflowError(403, "An active, verified account is required to accept an invitation")
        digest = hash_token(raw_token)
        result = await self.db.execute(select(InstitutionInvitation).where(InstitutionInvitation.token_hash == digest))
        item = result.scalar_one_or_none()
        now = datetime.now(UTC).replace(tzinfo=None)
        if item is None or item.accepted_at is not None or item.revoked_at is not None or item.expires_at <= now:
            raise InvitationWorkflowError(400, "Invitation token is invalid, expired, or already used")
        if account.email.strip().lower() != item.email or not hmac.compare_digest(item.token_hash, digest):
            raise InvitationWorkflowError(403, "Invitation email does not match the authenticated account")
        if item.role == "FACULTY":
            faculty = await self.db.scalar(select(FacultyProfile).where(FacultyProfile.account_id == account_id))
            if faculty is None:
                raise InvitationWorkflowError(422, "A faculty profile is required to accept a faculty invitation")
            belongs = await self.db.scalar(select(School.id).join(Department, Department.school_id == School.id)
                .where(Department.id == faculty.department_id, School.institution_id == item.institution_id))
            if belongs is None:
                raise InvitationWorkflowError(422, "Faculty profile must belong to the invited institution")
        membership = await self.db.get(InstitutionMembership, (item.institution_id, account_id))
        if membership is None:
            membership = InstitutionMembership(institution_id=item.institution_id, account_id=account_id,
                role=item.role, status="ACTIVE", invited_by_account_id=item.invited_by_account_id)
            self.db.add(membership)
        else:
            if membership.status == "ACTIVE" and membership.role == "INSTITUTION_ADMIN":
                raise InvitationWorkflowError(409, "Existing institution administrator role cannot be overwritten by an invitation")
            membership.role, membership.status, membership.invited_by_account_id = item.role, "ACTIVE", item.invited_by_account_id
        item.accepted_at = now
        AuditService(self.db).record(account_id, item.institution_id, "institution.invitation_accepted",
            "institution_invitation", item.id, {"role": item.role})
        await self.db.commit()
        await self.db.refresh(membership)
        return membership
