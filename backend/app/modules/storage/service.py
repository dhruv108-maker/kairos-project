"""Private local file storage with generated paths and ownership checks."""
from __future__ import annotations

import hashlib
import mimetypes
import uuid
import zipfile
from io import BytesIO
from pathlib import Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.academic import Cohort, Department, FacultyProfile, Programme, School, StudentProfile
from app.models.evaluation import ReportSubmission, ReportVersion
from app.models.internship import InternshipPlacement
from app.models.portfolio import StudentResume
from app.models.storage import StorageFile
from app.modules.audit.service import AuditService

ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".txt": "text/plain",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class StorageWorkflowError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class StorageService:
    def __init__(self, db: AsyncSession, root: Path | None = None):
        self.db = db
        self.root = (root or settings.VPS_STORAGE_PATH).expanduser().resolve()

    async def _institution_for_account(self, account_id: str) -> str | None:
        """Resolve an institution without requiring every optional profile table to exist.

        Student accounts can be linked to their department/programme before cohort
        assignment. Resolve those canonical relationships first; the storage upload
        itself must remain usable when an optional faculty profile table has not yet
        been deployed to an older database.
        """
        # Signup establishes department/programme affiliation before a cohort may
        # exist, so don't make cohort membership a prerequisite for file uploads.
        institution_id = await self.db.scalar(
            select(School.institution_id)
            .join(Department, Department.school_id == School.id)
            .join(StudentProfile, StudentProfile.department_id == Department.id)
            .where(StudentProfile.account_id == account_id)
        )
        if institution_id is not None:
            return institution_id

        institution_id = await self.db.scalar(
            select(School.institution_id)
            .join(Department, Department.school_id == School.id)
            .join(Programme, Programme.department_id == Department.id)
            .join(StudentProfile, StudentProfile.programme_id == Programme.id)
            .where(StudentProfile.account_id == account_id)
        )
        if institution_id is not None:
            return institution_id

        institution_id = await self.db.scalar(
            select(School.institution_id)
            .join(Department, Department.school_id == School.id)
            .join(Programme, Programme.department_id == Department.id)
            .join(Cohort, Cohort.programme_id == Programme.id)
            .join(StudentProfile, StudentProfile.cohort_id == Cohort.id)
            .where(StudentProfile.account_id == account_id)
        )
        if institution_id is not None:
            return institution_id

        # Institution attribution is audit metadata, not an upload prerequisite.
        # Do not query FacultyProfile here: older deployed schemas may not yet have
        # faculty_profiles, and that must not turn an otherwise valid upload into 500.
        return None

    def _safe_path(self, file_path: str) -> Path:
        path = (self.root / file_path).resolve()
        if self.root not in path.parents:
            raise StorageWorkflowError(404, "File not found")
        return path

    def _validate_content(self, extension: str, content: bytes) -> None:
        if not content:
            raise StorageWorkflowError(422, "Empty files are not allowed")
        if extension == ".pdf" and not content.startswith(b"%PDF-"):
            raise StorageWorkflowError(422, "File content does not match PDF format")
        if extension == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise StorageWorkflowError(422, "File content does not match PNG format")
        if extension in {".jpg", ".jpeg"} and not content.startswith(b"\xff\xd8\xff"):
            raise StorageWorkflowError(422, "File content does not match JPEG format")
        if extension == ".txt" and b"\x00" in content:
            raise StorageWorkflowError(422, "Text files cannot contain binary null bytes")

    async def save_upload(self, account_id: str, original_name: str, mime_type: str, content: bytes) -> StorageFile:
        if len(content) > MAX_UPLOAD_BYTES:
            raise StorageWorkflowError(413, "File exceeds the 10 MiB upload limit")
        safe_name = Path(original_name.replace("\\", "/")).name.strip()
        if not safe_name or safe_name in {".", ".."}:
            raise StorageWorkflowError(422, "A valid filename is required")
        extension = Path(safe_name).suffix.lower()
        expected_mime = ALLOWED_TYPES.get(extension)
        if expected_mime is None or mime_type.split(";", 1)[0].strip().lower() != expected_mime:
            raise StorageWorkflowError(415, "File type is not allowed or MIME type does not match the extension")
        self._validate_content(extension, content)

        file_id = str(uuid.uuid4())
        relative_path = Path("files") / str(uuid.uuid4()) / (file_id + extension)
        absolute_path = self._safe_path(relative_path.as_posix())
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_path.write_bytes(content)
        item = StorageFile(
            id=file_id, original_name=safe_name, file_path=relative_path.as_posix(),
            file_size_bytes=len(content), mime_type=expected_mime,
            sha256_hash=hashlib.sha256(content).hexdigest(), uploaded_by_account_id=account_id,
        )
        self.db.add(item)
        institution_id = await self._institution_for_account(account_id)
        AuditService(self.db).record(account_id, institution_id, "storage.file_uploaded", "storage_file", item.id, {"mime_type": item.mime_type, "file_size_bytes": item.file_size_bytes})
        try:
            await self.db.commit()
            await self.db.refresh(item)
        except Exception:
            await self.db.rollback()
            absolute_path.unlink(missing_ok=True)
            raise
        return item

    async def get_download(self, file_id: str, account_id: str) -> tuple[StorageFile, Path]:
        item = await self.db.get(StorageFile, file_id)
        if item is None:
            raise StorageWorkflowError(404, "File not found")
        allowed = item.uploaded_by_account_id == account_id
        if not allowed:
            faculty_id = await self.db.scalar(select(FacultyProfile.id).where(FacultyProfile.account_id == account_id))
            if faculty_id is not None:
                allowed = await self.db.scalar(
                    select(ReportVersion.id).join(ReportSubmission, ReportSubmission.id == ReportVersion.submission_id)
                    .join(InternshipPlacement, InternshipPlacement.id == ReportSubmission.placement_id)
                    .where(or_(ReportVersion.file_id == file_id, ReportVersion.presentation_file_id == file_id),
                           InternshipPlacement.faculty_supervisor_id == faculty_id)
                ) is not None
        if not allowed:
            raise StorageWorkflowError(404, "File not found")
        path = self._safe_path(item.file_path)
        if not path.is_file():
            raise StorageWorkflowError(404, "Stored file is unavailable")
        institution_id = await self._institution_for_account(account_id)
        AuditService(self.db).record(account_id, institution_id, "storage.file_downloaded", "storage_file", item.id, {"mime_type": item.mime_type})
        await self.db.commit()
        return item, path

    async def delete(self, file_id: str, account_id: str) -> None:
        item = await self.db.get(StorageFile, file_id)
        if item is None or item.uploaded_by_account_id != account_id:
            raise StorageWorkflowError(404, "File not found")
        referenced_report = await self.db.scalar(select(ReportVersion.id).where(
            or_(ReportVersion.file_id == file_id, ReportVersion.presentation_file_id == file_id)
        ))
        referenced_resume = await self.db.scalar(select(StudentResume.id).where(StudentResume.storage_file_id == file_id))
        if referenced_report is not None or referenced_resume is not None:
            raise StorageWorkflowError(409, "File is attached to a report or resume and cannot be deleted")
        path = self._safe_path(item.file_path)
        backup = path.read_bytes() if path.is_file() else None
        institution_id = await self._institution_for_account(account_id)
        AuditService(self.db).record(account_id, institution_id, "storage.file_deleted", "storage_file", item.id, {"mime_type": item.mime_type})
        if path.is_file():
            path.unlink()
        await self.db.delete(item)
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            if backup is not None:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(backup)
            raise

