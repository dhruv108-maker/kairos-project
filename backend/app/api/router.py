from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.faculty import router as faculty_router
from app.api.internships import router as internships_router
from app.api.students import router as students_router
from app.modules.internships.router import router as modular_internships_router
from app.modules.institutions.router import router as institutions_router
from app.modules.institutions.invitation_router import admin_router as institution_invitation_router, accept_router as institution_invitation_accept_router
from app.modules.reports.router import router as reports_router, requirement_router as report_requirement_router
from app.modules.evaluations.router import router as evaluations_router
from app.modules.organizations.router import router as organizations_router
from app.modules.storage.router import router as storage_router
from app.modules.academics.admin_router import router as academic_admin_router
from app.modules.audit.router import router as audit_router
from app.modules.analytics.router import router as analytics_router
from app.modules.employers.router import router as employers_router, public_router as public_jobs_router
from app.modules.employers.recruitment_router import router as recruitment_workflow_router
from app.modules.employers.student_offer_router import router as student_offer_router
from app.modules.identity_verification.router import router as identity_verification_router
from app.modules.employers.campus_recruitment_router import router as campus_recruitment_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(analytics_router)
api_router.include_router(students_router)
api_router.include_router(faculty_router)
api_router.include_router(institutions_router)
api_router.include_router(institution_invitation_router)
api_router.include_router(institution_invitation_accept_router)
api_router.include_router(reports_router)
api_router.include_router(report_requirement_router)
api_router.include_router(evaluations_router)
api_router.include_router(organizations_router)
api_router.include_router(storage_router)
api_router.include_router(academic_admin_router)
api_router.include_router(audit_router)
api_router.include_router(internships_router)
api_router.include_router(employers_router)
api_router.include_router(recruitment_workflow_router)
api_router.include_router(student_offer_router)
api_router.include_router(identity_verification_router)
api_router.include_router(campus_recruitment_router)
api_router.include_router(public_jobs_router)

# Opt-in modular endpoints live under /api/v1/modules/* while legacy routes remain unchanged.
api_router.include_router(modular_internships_router, prefix="/modules")
