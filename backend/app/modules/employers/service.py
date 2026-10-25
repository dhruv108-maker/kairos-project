from datetime import UTC, date, datetime, timedelta
import hmac
import secrets
from uuid import uuid4

from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import Account, AccountRole, Role, StudentProfile
from app.models.employers import EmployerInvitation, EmployerMembership, EmployerOrganization
from app.core.security import hash_token
from app.services.email import send_workflow_notification
from app.core.config import settings
from app.models.internship import InternshipOpportunity, InternshipProvider, InternshipApplication, RecruitmentStageEvent, RecruitmentNote
from app.models.recruitment import RecruitmentDrive, RecruitmentDriveOpportunity
from app.modules.audit.service import AuditService


class EmployerError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class EmployerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, account_id: str, payload: dict) -> EmployerOrganization:
        account = await self.db.get(Account, account_id)
        if account is None or not account.is_active or not account.is_verified:
            raise EmployerError(403, "An active, verified Kairos account is required")
        legal = payload["legal_name"].strip()
        normalized = " ".join(legal.casefold().split())
        item = EmployerOrganization(
            id=str(uuid4()), legal_name=legal, display_name=payload["display_name"].strip(),
            normalized_name=normalized, organization_type=payload.get("organization_type", "COMPANY"),
            industry=payload.get("industry"), description=payload.get("description"),
            website_url=str(payload["website_url"]) if payload.get("website_url") else None,
            business_email=payload.get("business_email"), phone=payload.get("phone"),
            country=payload.get("country"), state=payload.get("state"), city=payload.get("city"),
            postal_code=payload.get("postal_code"), headquarters_address=payload.get("headquarters_address"),
            company_size=payload.get("company_size"), founded_year=payload.get("founded_year"),
            registration_identifier=payload.get("registration_identifier"),
            careers_url=str(payload["careers_url"]) if payload.get("careers_url") else None,
            status="PENDING_VERIFICATION", created_by_account_id=account_id,
        )
        self.db.add(item)
        self.db.add(EmployerMembership(id=str(uuid4()), organization_id=item.id, account_id=account_id, role="OWNER", status="ACTIVE"))
        self.db.add(InternshipProvider(
            id=str(uuid4()), company_name=item.display_name, website=item.website_url,
            industry_sector=item.industry, contact_person_name=account.full_name,
            contact_email=item.business_email or account.email, employer_organization_id=item.id,
        ))
        AuditService(self.db).record(account_id, None, "employer.registered", "employer_organization", item.id, {"status": item.status})
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise EmployerError(409, "An employer with this legal name or registration identifier already exists") from None
        await self.db.refresh(item)
        return item

    async def membership(self, organization_id: str, account_id: str, allowed: set[str] | None = None) -> tuple[EmployerOrganization, EmployerMembership]:
        org = await self.db.get(EmployerOrganization, organization_id)
        if org is None:
            raise EmployerError(404, "Employer organization not found")
        result = await self.db.execute(select(EmployerMembership).where(
            EmployerMembership.organization_id == organization_id,
            EmployerMembership.account_id == account_id,
            EmployerMembership.status == "ACTIVE",
        ))
        member = result.scalar_one_or_none()
        if member is None:
            raise EmployerError(403, "Active membership in this employer organization is required")
        if allowed and member.role not in allowed:
            raise EmployerError(403, "Your company role does not permit this action")
        return org, member

    async def my_organizations(self, account_id: str) -> list[EmployerOrganization]:
        result = await self.db.execute(
            select(EmployerOrganization).join(EmployerMembership, EmployerMembership.organization_id == EmployerOrganization.id)
            .where(EmployerMembership.account_id == account_id, EmployerMembership.status == "ACTIVE")
            .order_by(EmployerOrganization.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_profile(self, organization_id: str, actor_id: str, data: dict) -> EmployerOrganization:
        org, _ = await self.membership(organization_id, actor_id, {"OWNER", "ADMIN"})
        for key, value in data.items():
            if key in {"website_url", "careers_url"} and value is not None:
                value = str(value)
            setattr(org, key, value)
        AuditService(self.db).record(actor_id, None, "employer.profile_updated", "employer_organization", org.id, {"fields": sorted(data)})
        await self.db.commit()
        await self.db.refresh(org)
        return org

    async def submit_verification(self, organization_id: str, actor_id: str) -> EmployerOrganization:
        org, _ = await self.membership(organization_id, actor_id, {"OWNER", "ADMIN"})
        if org.status not in {"PENDING_VERIFICATION", "REJECTED"}:
            raise EmployerError(409, "Only a new or rejected organization can be submitted for verification")
        org.status, org.review_notes = "PENDING_APPROVAL", None
        AuditService(self.db).record(actor_id, None, "employer.verification_submitted", "employer_organization", org.id, {})
        await self.db.commit()
        await self.db.refresh(org)
        return org

    async def review_verification(self, organization_id: str, actor_id: str, decision: str, notes: str | None) -> EmployerOrganization:
        result = await self.db.execute(select(Role.name).join(AccountRole, AccountRole.role_id == Role.id).where(AccountRole.account_id == actor_id))
        if "PLATFORM_ADMIN" not in set(result.scalars().all()):
            raise EmployerError(403, "Platform administrator permission required")
        org = await self.db.get(EmployerOrganization, organization_id)
        if org is None:
            raise EmployerError(404, "Employer organization not found")
        if org.status != "PENDING_APPROVAL":
            raise EmployerError(409, "Organization is not awaiting verification review")
        if decision not in {"ACTIVE", "REJECTED"}:
            raise EmployerError(422, "decision must be ACTIVE or REJECTED")
        org.status, org.reviewed_by_account_id, org.reviewed_at, org.review_notes = decision, actor_id, datetime.utcnow(), notes
        AuditService(self.db).record(actor_id, None, "employer.verification_decided", "employer_organization", org.id, {"decision": decision})
        await self.db.commit()
        await self.db.refresh(org)
        return org


    async def list_members(self, organization_id: str, actor_id: str) -> list[EmployerMembership]:
        await self.membership(organization_id, actor_id)
        result = await self.db.execute(select(EmployerMembership).where(
            EmployerMembership.organization_id == organization_id
        ).order_by(EmployerMembership.created_at))
        return list(result.scalars().all())

    async def invite_member(self, organization_id: str, actor_id: str, email: str, role: str) -> tuple[EmployerInvitation, bool]:
        org, actor_member = await self.membership(organization_id, actor_id, {"OWNER", "ADMIN"})
        role = role.strip().upper()
        allowed = {"ADMIN", "RECRUITER", "VIEWER"} if actor_member.role == "OWNER" else {"RECRUITER", "VIEWER"}
        if role not in allowed:
            raise EmployerError(403, "Your company role cannot invite a member with that role")
        normalized_email = email.strip().lower()
        if not normalized_email or "@" not in normalized_email:
            raise EmployerError(422, "A valid invitation email is required")
        account = await self.db.scalar(select(Account).where(func.lower(Account.email) == normalized_email))
        if account is not None:
            current = await self.db.scalar(select(EmployerMembership).where(
                EmployerMembership.organization_id == organization_id,
                EmployerMembership.account_id == account.id,
                EmployerMembership.status == "ACTIVE",
            ))
            if current is not None:
                raise EmployerError(409, "This account is already an active member of the organization")
        now = datetime.now(UTC).replace(tzinfo=None)
        pending = await self.db.execute(select(EmployerInvitation).where(
            EmployerInvitation.organization_id == organization_id,
            EmployerInvitation.email == normalized_email,
            EmployerInvitation.accepted_at.is_(None),
            EmployerInvitation.revoked_at.is_(None),
            EmployerInvitation.expires_at > now,
        ))
        for previous in pending.scalars().all():
            previous.revoked_at = now
        raw_token = secrets.token_urlsafe(32)
        item = EmployerInvitation(
            id=str(uuid4()), organization_id=organization_id, email=normalized_email, role=role,
            token_hash=hash_token(raw_token), expires_at=now + timedelta(days=7),
            invited_by_account_id=actor_id,
        )
        self.db.add(item)
        AuditService(self.db).record(actor_id, None, "employer.member_invited", "employer_invitation", item.id,
                                     {"organization_id": organization_id, "email": normalized_email, "role": role})
        await self.db.commit()
        await self.db.refresh(item)
        try:
            link = f"{settings.FRONTEND_URL.rstrip('/')}/employer-invite?token={raw_token}"
            await send_workflow_notification(normalized_email, f"Invitation to join {org.display_name} on Kairos",
                f"You have been invited to join {org.display_name} as {role}. Sign in to your verified Kairos account and accept within seven days: {link}")
            return item, True
        except Exception:
            item.revoked_at = datetime.now(UTC).replace(tzinfo=None)
            await self.db.commit()
            return item, False

    async def list_invitations(self, organization_id: str, actor_id: str) -> list[EmployerInvitation]:
        await self.membership(organization_id, actor_id, {"OWNER", "ADMIN"})
        result = await self.db.execute(select(EmployerInvitation).where(
            EmployerInvitation.organization_id == organization_id
        ).order_by(EmployerInvitation.created_at.desc()))
        return list(result.scalars().all())

    async def revoke_invitation(self, organization_id: str, actor_id: str, invitation_id: str) -> None:
        await self.membership(organization_id, actor_id, {"OWNER", "ADMIN"})
        item = await self.db.get(EmployerInvitation, invitation_id)
        if item is None or item.organization_id != organization_id:
            raise EmployerError(404, "Invitation not found in this organization")
        if item.accepted_at is not None:
            raise EmployerError(409, "An accepted invitation cannot be revoked")
        item.revoked_at = datetime.now(UTC).replace(tzinfo=None)
        AuditService(self.db).record(actor_id, None, "employer.invitation_revoked", "employer_invitation", item.id,
                                     {"organization_id": organization_id})
        await self.db.commit()

    async def accept_invitation(self, account_id: str, raw_token: str) -> EmployerMembership:
        account = await self.db.get(Account, account_id)
        if account is None or not account.is_active or not account.is_verified:
            raise EmployerError(403, "An active, verified Kairos account is required")
        digest = hash_token(raw_token)
        item = await self.db.scalar(select(EmployerInvitation).where(EmployerInvitation.token_hash == digest))
        now = datetime.now(UTC).replace(tzinfo=None)
        if item is None or item.accepted_at is not None or item.revoked_at is not None or item.expires_at <= now:
            raise EmployerError(400, "Invitation token is invalid, expired, revoked, or already used")
        if not hmac.compare_digest(item.token_hash, digest) or account.email.strip().lower() != item.email:
            raise EmployerError(403, "Invitation email does not match the authenticated account")
        org = await self.db.get(EmployerOrganization, item.organization_id)
        if org is None or org.status == "SUSPENDED":
            raise EmployerError(403, "This employer organization is not accepting invitations")
        membership = await self.db.scalar(select(EmployerMembership).where(
            EmployerMembership.organization_id == item.organization_id,
            EmployerMembership.account_id == account_id,
        ))
        if membership is None:
            membership = EmployerMembership(id=str(uuid4()), organization_id=item.organization_id,
                account_id=account_id, role=item.role, status="ACTIVE", invited_by_account_id=item.invited_by_account_id)
            self.db.add(membership)
        elif membership.status == "ACTIVE":
            raise EmployerError(409, "This account is already an active member")
        else:
            membership.role, membership.status, membership.invited_by_account_id = item.role, "ACTIVE", item.invited_by_account_id
        item.accepted_at = now
        AuditService(self.db).record(account_id, None, "employer.invitation_accepted", "employer_invitation", item.id,
                                     {"organization_id": item.organization_id, "role": item.role})
        await self.db.commit()
        await self.db.refresh(membership)
        return membership

    async def change_member_role(self, organization_id: str, actor_id: str, target_account_id: str, role: str) -> EmployerMembership:
        _, actor_member = await self.membership(organization_id, actor_id, {"OWNER", "ADMIN"})
        target = await self.db.scalar(select(EmployerMembership).where(
            EmployerMembership.organization_id == organization_id,
            EmployerMembership.account_id == target_account_id,
            EmployerMembership.status == "ACTIVE",
        ))
        if target is None:
            raise EmployerError(404, "Active membership not found")
        role = role.strip().upper()
        if role not in {"ADMIN", "RECRUITER", "VIEWER"}:
            raise EmployerError(422, "Supported roles are ADMIN, RECRUITER, and VIEWER")
        if actor_member.role != "OWNER" and (target.role in {"OWNER", "ADMIN"} or role == "ADMIN"):
            raise EmployerError(403, "Only the owner can change administrator roles")
        if target.role == "OWNER":
            raise EmployerError(409, "Owner role cannot be changed through member role editing")
        old_role = target.role
        target.role = role
        AuditService(self.db).record(actor_id, None, "employer.member_role_changed", "employer_membership", target.id,
                                     {"organization_id": organization_id, "from": old_role, "to": role})
        await self.db.commit()
        await self.db.refresh(target)
        return target

    async def remove_member(self, organization_id: str, actor_id: str, target_account_id: str) -> None:
        _, actor_member = await self.membership(organization_id, actor_id, {"OWNER", "ADMIN"})
        target = await self.db.scalar(select(EmployerMembership).where(
            EmployerMembership.organization_id == organization_id,
            EmployerMembership.account_id == target_account_id,
            EmployerMembership.status == "ACTIVE",
        ))
        if target is None:
            raise EmployerError(404, "Active membership not found")
        if target.role == "OWNER":
            raise EmployerError(409, "Ownership must be transferred before removing the owner")
        if actor_member.role != "OWNER" and target.role == "ADMIN":
            raise EmployerError(403, "Only the owner can remove an administrator")
        target.status = "REVOKED"
        AuditService(self.db).record(actor_id, None, "employer.member_removed", "employer_membership", target.id,
                                     {"organization_id": organization_id, "role": target.role})
        await self.db.commit()


    async def set_organization_status(self, organization_id: str, actor_id: str, new_status: str, notes: str | None = None) -> EmployerOrganization:
        roles = await self.db.execute(select(Role.name).join(AccountRole, AccountRole.role_id == Role.id).where(AccountRole.account_id == actor_id))
        if "PLATFORM_ADMIN" not in set(roles.scalars().all()):
            raise EmployerError(403, "Platform administrator permission required")
        org = await self.db.get(EmployerOrganization, organization_id)
        if org is None:
            raise EmployerError(404, "Employer organization not found")
        new_status = new_status.strip().upper()
        allowed = {
            "PENDING_VERIFICATION": {"PENDING_APPROVAL", "REJECTED"},
            "PENDING_APPROVAL": {"ACTIVE", "REJECTED", "SUSPENDED"},
            "ACTIVE": {"SUSPENDED"},
            "SUSPENDED": {"ACTIVE"},
            "REJECTED": {"PENDING_APPROVAL"},
        }
        if new_status not in allowed.get(org.status, set()):
            raise EmployerError(409, f"Invalid employer status transition: {org.status} -> {new_status}")
        old_status = org.status
        org.status = new_status
        org.reviewed_by_account_id = actor_id
        org.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
        org.review_notes = notes
        AuditService(self.db).record(actor_id, None, "employer.status_changed", "employer_organization", org.id,
            {"from": old_status, "to": new_status})
        await self.db.commit()
        await self.db.refresh(org)
        return org

    async def public_company(self, organization_id: str) -> EmployerOrganization:
        org = await self.db.get(EmployerOrganization, organization_id)
        if org is None or org.status != "ACTIVE":
            raise EmployerError(404, "Company profile not found")
        return org

    async def public_company_jobs(self, organization_id: str, limit: int, offset: int):
        org = await self.public_company(organization_id)
        provider = await self._provider_for_org(org.id)
        campus_link = select(RecruitmentDriveOpportunity.opportunity_id).join(RecruitmentDrive, RecruitmentDrive.id == RecruitmentDriveOpportunity.drive_id).where(
            RecruitmentDriveOpportunity.opportunity_id == InternshipOpportunity.id, RecruitmentDrive.status.in_({"PUBLISHED", "ACTIVE"})).exists()
        result = await self.db.execute(select(InternshipOpportunity, InternshipProvider).join(
            InternshipProvider, InternshipOpportunity.provider_id == InternshipProvider.id
        ).where(
            ~campus_link,
            InternshipProvider.id == provider.id,
            InternshipOpportunity.lifecycle_status == "PUBLISHED",
            InternshipOpportunity.is_active.is_(True),
            InternshipOpportunity.application_deadline >= date.today(),
        ).order_by(InternshipOpportunity.created_at.desc(), InternshipOpportunity.id).limit(limit).offset(offset))
        return list(result.all())

    async def _provider_for_org(self, org_id: str) -> InternshipProvider:
        result = await self.db.execute(select(InternshipProvider).where(InternshipProvider.employer_organization_id == org_id))
        provider = result.scalar_one_or_none()
        if provider is None:
            raise EmployerError(409, "Recruitment provider mapping is missing")
        return provider

    async def create_job(self, organization_id: str, actor_id: str, data: dict) -> InternshipOpportunity:
        org, _ = await self.membership(organization_id, actor_id, {"OWNER", "ADMIN", "RECRUITER"})
        provider = await self._provider_for_org(org.id)
        if data.get("application_deadline") < date.today():
            raise EmployerError(422, "application_deadline must be today or later")
        item = InternshipOpportunity(
            id=str(uuid4()), provider_id=provider.id, title=data["title"].strip(),
            description=data["description"].strip(), summary=data.get("summary"), location=data["location"].strip(),
            stipend_amount=data.get("compensation_min") or 0, application_deadline=data["application_deadline"],
            is_active=False, lifecycle_status="DRAFT", opportunity_type=data.get("opportunity_type", "INTERNSHIP"),
            employment_type=data.get("employment_type", "INTERNSHIP"), work_mode=data.get("work_mode", "ONSITE"),
            department=data.get("department"), experience_min_years=data.get("experience_min_years"),
            experience_max_years=data.get("experience_max_years"), compensation_min=data.get("compensation_min"),
            compensation_max=data.get("compensation_max"), compensation_currency=data.get("compensation_currency", "INR"),
            compensation_period=data.get("compensation_period", "YEAR"), compensation_visible=data.get("compensation_visible", True),
            starts_on=data.get("starts_on"), ends_on=data.get("ends_on"), openings=data.get("openings", 1),
            required_skills=data.get("required_skills", []), preferred_skills=data.get("preferred_skills", []),
            education_requirements=data.get("education_requirements"), public_application_url=str(data["public_application_url"]) if data.get("public_application_url") else None,
            created_by_account_id=actor_id,
        )
        self.db.add(item)
        AuditService(self.db).record(actor_id, None, "recruitment.job_created", "internship_opportunity", item.id, {"organization_id": org.id})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list_jobs(self, organization_id: str, actor_id: str, limit: int, offset: int) -> list[InternshipOpportunity]:
        await self.membership(organization_id, actor_id)
        provider = await self._provider_for_org(organization_id)
        result = await self.db.execute(select(InternshipOpportunity).where(InternshipOpportunity.provider_id == provider.id).order_by(InternshipOpportunity.created_at.desc()).limit(limit).offset(offset))
        return list(result.scalars().all())

    async def get_owned_job(self, organization_id: str, actor_id: str, job_id: str, write: bool = False) -> InternshipOpportunity:
        await self.membership(organization_id, actor_id, {"OWNER", "ADMIN", "RECRUITER"} if write else None)
        provider = await self._provider_for_org(organization_id)
        result = await self.db.execute(select(InternshipOpportunity).where(InternshipOpportunity.id == job_id, InternshipOpportunity.provider_id == provider.id))
        item = result.scalar_one_or_none()
        if item is None:
            raise EmployerError(404, "Job not found in this organization")
        return item

    async def update_job(self, organization_id: str, actor_id: str, job_id: str, data: dict) -> InternshipOpportunity:
        item = await self.get_owned_job(organization_id, actor_id, job_id, write=True)
        if item.lifecycle_status in {"CLOSED", "ARCHIVED"}:
            raise EmployerError(409, "Closed or archived jobs cannot be edited")
        if "application_deadline" in data and data["application_deadline"] < date.today():
            raise EmployerError(422, "application_deadline must be today or later")
        for key, value in data.items():
            if key == "public_application_url" and value is not None:
                value = str(value)
            setattr(item, key, value)
        AuditService(self.db).record(actor_id, None, "recruitment.job_updated", "internship_opportunity", item.id, {"fields": sorted(data)})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def transition_job(self, organization_id: str, actor_id: str, job_id: str, action: str) -> InternshipOpportunity:
        org, _ = await self.membership(organization_id, actor_id, {"OWNER", "ADMIN", "RECRUITER"})
        item = await self.get_owned_job(organization_id, actor_id, job_id, write=True)
        transitions = {
            "publish": {"DRAFT": "PUBLISHED"}, "pause": {"PUBLISHED": "PAUSED"},
            "resume": {"PAUSED": "PUBLISHED"}, "close": {"PUBLISHED": "CLOSED", "PAUSED": "CLOSED"},
            "reopen": {"CLOSED": "PUBLISHED"}, "archive": {"DRAFT": "ARCHIVED", "PAUSED": "ARCHIVED", "CLOSED": "ARCHIVED"},
        }
        old_status = item.lifecycle_status
        next_status = transitions.get(action, {}).get(old_status)
        if not next_status:
            raise EmployerError(409, f"Cannot {action} a job in {old_status} state")
        if action in {"publish", "resume", "reopen"}:
            if org.status != "ACTIVE":
                raise EmployerError(403, "Employer organization must be active and verified before publishing")
            if item.application_deadline < date.today():
                raise EmployerError(409, "Expired jobs cannot accept applications")
            if len(item.title.strip()) < 2 or len(item.description.strip()) < 20 or not item.location.strip():
                raise EmployerError(422, "Title, description (20+ characters), and location are required")
        item.lifecycle_status, item.is_active = next_status, next_status == "PUBLISHED"
        AuditService(self.db).record(actor_id, None, f"recruitment.job_{action}", "internship_opportunity", item.id, {"from": old_status, "to": next_status, "organization_id": org.id})
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def public_jobs(
        self, q: str | None, location: str | None, opportunity_type: str | None,
        work_mode: str | None, limit: int, offset: int, *,
        employment_type: str | None = None, sort_by: str = "newest",
        posted_within_days: int | None = None,
    ) -> list[tuple[InternshipOpportunity, InternshipProvider]]:
        campus_link = select(RecruitmentDriveOpportunity.opportunity_id).join(RecruitmentDrive, RecruitmentDrive.id == RecruitmentDriveOpportunity.drive_id).where(
            RecruitmentDriveOpportunity.opportunity_id == InternshipOpportunity.id, RecruitmentDrive.status.in_({"PUBLISHED", "ACTIVE"})).exists()
        query = select(InternshipOpportunity, InternshipProvider).join(InternshipProvider, InternshipOpportunity.provider_id == InternshipProvider.id).join(EmployerOrganization, InternshipProvider.employer_organization_id == EmployerOrganization.id).where(
            ~campus_link,
            InternshipOpportunity.lifecycle_status == "PUBLISHED", InternshipOpportunity.is_active.is_(True),
            EmployerOrganization.status == "ACTIVE", InternshipOpportunity.application_deadline >= date.today(),
        )
        if q:
            term = f"%{q.strip()}%"
            query = query.where(or_(InternshipOpportunity.title.ilike(term), InternshipOpportunity.description.ilike(term), InternshipOpportunity.summary.ilike(term), EmployerOrganization.display_name.ilike(term)))
        if location:
            query = query.where(InternshipOpportunity.location.ilike(f"%{location.strip()}%"))
        if opportunity_type:
            query = query.where(InternshipOpportunity.opportunity_type == opportunity_type.upper())
        if work_mode:
            query = query.where(InternshipOpportunity.work_mode == work_mode.upper())
        if employment_type:
            query = query.where(InternshipOpportunity.employment_type == employment_type.upper())
        if posted_within_days is not None:
            cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=posted_within_days)
            query = query.where(InternshipOpportunity.created_at >= cutoff)
        if sort_by == "relevance" and q and q.strip():
            relevance_term = f"%{q.strip()}%"
            query = query.order_by(
                case(
                    (InternshipOpportunity.title.ilike(f"{q.strip()}%"), 0),
                    (EmployerOrganization.display_name.ilike(f"{q.strip()}%"), 1),
                    (InternshipOpportunity.title.ilike(relevance_term), 2),
                    (EmployerOrganization.display_name.ilike(relevance_term), 3),
                    else_=4,
                ),
                InternshipOpportunity.created_at.desc(),
                InternshipOpportunity.id,
            )
        else:
            query = query.order_by(InternshipOpportunity.created_at.desc(), InternshipOpportunity.id)
        result = await self.db.execute(query.limit(limit).offset(offset))
        return list(result.all())


    async def public_job(self, job_id: str) -> tuple[InternshipOpportunity, InternshipProvider]:
        campus_link = select(RecruitmentDriveOpportunity.opportunity_id).join(
            RecruitmentDrive, RecruitmentDrive.id == RecruitmentDriveOpportunity.drive_id
        ).where(
            RecruitmentDriveOpportunity.opportunity_id == InternshipOpportunity.id,
            RecruitmentDrive.status.in_({"PUBLISHED", "ACTIVE"}),
        ).exists()
        result = await self.db.execute(
            select(InternshipOpportunity, InternshipProvider)
            .join(InternshipProvider, InternshipOpportunity.provider_id == InternshipProvider.id)
            .join(EmployerOrganization, InternshipProvider.employer_organization_id == EmployerOrganization.id)
            .where(
                InternshipOpportunity.id == job_id,
                ~campus_link,
                InternshipOpportunity.lifecycle_status == "PUBLISHED",
                InternshipOpportunity.is_active.is_(True),
                EmployerOrganization.status == "ACTIVE",
                InternshipOpportunity.application_deadline >= date.today(),
            )
            .limit(1)
        )
        row = result.one_or_none()
        if row is None:
            raise EmployerError(404, "Published job not found")
        return row[0], row[1]

    async def _application_in_org(self, organization_id: str, actor_id: str, application_id: str, write: bool = False):
        await self.membership(organization_id, actor_id, {"OWNER", "ADMIN", "RECRUITER"} if write else None)
        provider = await self._provider_for_org(organization_id)
        result = await self.db.execute(
            select(InternshipApplication, InternshipOpportunity).join(
                InternshipOpportunity, InternshipApplication.opportunity_id == InternshipOpportunity.id
            ).where(InternshipApplication.id == application_id, InternshipOpportunity.provider_id == provider.id)
        )
        row = result.one_or_none()
        if row is None:
            raise EmployerError(404, "Application not found in this organization")
        return row[0], row[1]

    async def list_applications(self, organization_id: str, actor_id: str, job_id: str | None, stage: str | None, limit: int, offset: int):
        await self.membership(organization_id, actor_id)
        provider = await self._provider_for_org(organization_id)
        query = select(InternshipApplication, InternshipOpportunity, Account).join(
            InternshipOpportunity, InternshipApplication.opportunity_id == InternshipOpportunity.id
        ).join(StudentProfile, StudentProfile.id == InternshipApplication.student_id).join(
            Account, Account.id == StudentProfile.account_id
        ).where(InternshipOpportunity.provider_id == provider.id)
        if job_id:
            query = query.where(InternshipOpportunity.id == job_id)
        if stage:
            query = query.where(InternshipApplication.recruitment_stage == stage.upper())
        result = await self.db.execute(query.order_by(InternshipApplication.applied_at.desc(), InternshipApplication.id).limit(limit).offset(offset))
        return list(result.all())

    async def get_application_detail(self, organization_id: str, actor_id: str, application_id: str):
        application, opportunity = await self._application_in_org(organization_id, actor_id, application_id)
        from app.models.academic import StudentProfile
        student = await self.db.get(StudentProfile, application.student_id)
        account = await self.db.get(Account, student.account_id) if student else None
        history_result = await self.db.execute(select(RecruitmentStageEvent).where(
            RecruitmentStageEvent.application_id == application.id
        ).order_by(RecruitmentStageEvent.created_at))
        return application, opportunity, student, account, list(history_result.scalars().all())

    async def transition_application_stage(self, organization_id: str, actor_id: str, application_id: str, new_stage: str, note: str | None = None):
        application, opportunity = await self._application_in_org(organization_id, actor_id, application_id, write=True)
        new_stage = new_stage.strip().upper()
        transitions = {
            "SUBMITTED": {"UNDER_REVIEW", "REJECTED", "WITHDRAWN"},
            "UNDER_REVIEW": {"SHORTLISTED", "INTERVIEW", "REJECTED", "WITHDRAWN"},
            "SHORTLISTED": {"INTERVIEW", "OFFER", "REJECTED", "WITHDRAWN"},
            "INTERVIEW": {"SHORTLISTED", "OFFER", "REJECTED", "WITHDRAWN"},
            "OFFER": {"HIRED", "REJECTED", "WITHDRAWN"},
            "HIRED": set(), "REJECTED": set(), "WITHDRAWN": set(),
        }
        old_stage = application.recruitment_stage or "SUBMITTED"
        if new_stage not in transitions.get(old_stage, set()):
            raise EmployerError(409, f"Invalid application stage transition: {old_stage} -> {new_stage}")
        legacy_status = {
            "SUBMITTED": "APPLIED", "UNDER_REVIEW": "APPLIED", "SHORTLISTED": "SHORTLISTED",
            "INTERVIEW": "SHORTLISTED", "OFFER": "OFFERED", "HIRED": "OFFERED",
            "REJECTED": "REJECTED", "WITHDRAWN": "WITHDRAWN",
        }[new_stage]
        application.recruitment_stage = new_stage
        application.status = legacy_status
        self.db.add(RecruitmentStageEvent(id=str(uuid4()), application_id=application.id, actor_account_id=actor_id,
            from_stage=old_stage, to_stage=new_stage, note=note))
        AuditService(self.db).record(actor_id, None, "recruitment.application_stage_changed", "internship_application", application.id,
            {"organization_id": organization_id, "opportunity_id": opportunity.id, "from": old_stage, "to": new_stage})
        await self.db.commit()
        await self.db.refresh(application)
        return application

    async def add_application_note(self, organization_id: str, actor_id: str, application_id: str, body: str) -> RecruitmentNote:
        application, _ = await self._application_in_org(organization_id, actor_id, application_id, write=True)
        note = RecruitmentNote(id=str(uuid4()), application_id=application.id, author_account_id=actor_id, body=body.strip())
        self.db.add(note)
        AuditService(self.db).record(actor_id, None, "recruitment.internal_note_added", "internship_application", application.id,
            {"organization_id": organization_id})
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def list_application_notes(self, organization_id: str, actor_id: str, application_id: str) -> list[RecruitmentNote]:
        await self._application_in_org(organization_id, actor_id, application_id)
        result = await self.db.execute(select(RecruitmentNote).where(
            RecruitmentNote.application_id == application_id
        ).order_by(RecruitmentNote.created_at))
        return list(result.scalars().all())

    async def dashboard(self, organization_id: str, actor_id: str) -> dict:
        await self.membership(organization_id, actor_id)
        provider = await self._provider_for_org(organization_id)
        counts = {}
        for state in ["DRAFT", "PUBLISHED", "PAUSED", "CLOSED", "ARCHIVED"]:
            result = await self.db.execute(select(func.count(InternshipOpportunity.id)).where(InternshipOpportunity.provider_id == provider.id, InternshipOpportunity.lifecycle_status == state))
            counts[state.lower()] = result.scalar_one()
        result = await self.db.execute(select(func.count(InternshipApplication.id)).join(InternshipOpportunity, InternshipApplication.opportunity_id == InternshipOpportunity.id).where(InternshipOpportunity.provider_id == provider.id))
        counts["applications"] = result.scalar_one()
        result = await self.db.execute(select(func.count(InternshipApplication.id)).join(InternshipOpportunity, InternshipApplication.opportunity_id == InternshipOpportunity.id).where(InternshipOpportunity.provider_id == provider.id, InternshipApplication.status == "APPLIED"))
        counts["new_applications"] = result.scalar_one()
        return counts
