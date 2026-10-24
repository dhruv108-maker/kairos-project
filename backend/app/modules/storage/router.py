from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentAccount, DbSession
from app.modules.storage.service import MAX_UPLOAD_BYTES, StorageService, StorageWorkflowError

router = APIRouter(prefix="/storage", tags=["file storage"])


async def _call(operation, db):
    try:
        return await operation
    except StorageWorkflowError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Storage metadata conflicts with existing data") from None


def _file(item):
    return {"id": item.id, "original_name": item.original_name, "file_size_bytes": item.file_size_bytes,
            "mime_type": item.mime_type, "sha256_hash": item.sha256_hash, "created_at": item.created_at}


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(account: CurrentAccount, db: DbSession, file: UploadFile = File(...)):
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    item = await _call(StorageService(db).save_upload(account.id, file.filename or "", file.content_type or "", content), db)
    return _file(item)


@router.get("/{file_id}")
async def download_file(file_id: str, account: CurrentAccount, db: DbSession):
    item, path = await _call(StorageService(db).get_download(file_id, account.id), db)
    return FileResponse(path=path, media_type=item.mime_type, filename=item.original_name, content_disposition_type="attachment")


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(file_id: str, account: CurrentAccount, db: DbSession):
    await _call(StorageService(db).delete(file_id, account.id), db)
    return None
