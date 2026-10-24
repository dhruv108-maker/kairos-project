import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Account, Base
from app.modules.storage.service import StorageService, StorageWorkflowError


@pytest_asyncio.fixture
async def storage_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        db.add(Account(id="owner", email="owner@example.test", password_hash="x", full_name="Owner", is_active=True, is_verified=True))
        await db.commit()
        yield db
    await engine.dispose()


@pytest.mark.asyncio
async def test_upload_uses_generated_private_path_and_owner_can_download(storage_session, tmp_path):
    service = StorageService(storage_session, root=tmp_path)
    content = b"%PDF-1.7\nprivate report contents"
    item = await service.save_upload("owner", "../../private.pdf", "application/pdf", content)
    assert item.original_name == "private.pdf"
    assert not item.file_path.startswith("/")
    assert ".." not in item.file_path
    stored = tmp_path / item.file_path
    assert stored.read_bytes() == content
    metadata, path = await service.get_download(item.id, "owner")
    assert metadata.id == item.id
    assert path == stored


@pytest.mark.asyncio
async def test_storage_rejects_mime_mismatch_and_invalid_pdf(storage_session, tmp_path):
    service = StorageService(storage_session, root=tmp_path)
    with pytest.raises(StorageWorkflowError) as mismatch:
        await service.save_upload("owner", "report.pdf", "text/plain", b"%PDF-1.7")
    assert mismatch.value.status_code == 415
    with pytest.raises(StorageWorkflowError) as invalid:
        await service.save_upload("owner", "report.pdf", "application/pdf", b"not a pdf")
    assert invalid.value.status_code == 422


@pytest.mark.asyncio
async def test_file_download_is_not_disclosed_to_another_account(storage_session, tmp_path):
    service = StorageService(storage_session, root=tmp_path)
    item = await service.save_upload("owner", "report.pdf", "application/pdf", b"%PDF-1.7\ncontents")
    with pytest.raises(StorageWorkflowError) as error:
        await service.get_download(item.id, "different-account")
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_owner_can_delete_unreferenced_file(storage_session, tmp_path):
    service = StorageService(storage_session, root=tmp_path)
    item = await service.save_upload("owner", "report.pdf", "application/pdf", b"%PDF-1.7\ncontents")
    path = tmp_path / item.file_path
    await service.delete(item.id, "owner")
    assert not path.exists()
