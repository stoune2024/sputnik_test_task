import mimetypes
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select

from backend.file_service.models import StoredFile


BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage" / "files"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


async def list_files(session) -> list[StoredFile]:
    result = await session.execute(
        select(StoredFile).order_by(StoredFile.created_at.desc())
    )
    return list(result.scalars().all())


async def get_file(session, file_id: str) -> StoredFile:
    file_item = await session.get(StoredFile, file_id)
    if not file_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )
    return file_item


async def create_file(session, title: str, upload_file: UploadFile) -> StoredFile:
    content = await upload_file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty"
        )

    file_id = str(uuid4())
    suffix = Path(upload_file.filename or "").suffix
    stored_name = f"{file_id}{suffix}"
    stored_path = STORAGE_DIR / stored_name
    stored_path.write_bytes(content)

    file_item = StoredFile(
        id=file_id,
        title=title,
        original_name=upload_file.filename or stored_name,
        stored_name=stored_name,
        mime_type=upload_file.content_type
        or mimetypes.guess_type(stored_name)[0]
        or "application/octet-stream",
        size=len(content),
        processing_status="uploaded",
    )
    session.add(file_item)
    await session.commit()
    await session.refresh(file_item)
    return file_item


async def update_file(session, file_id: str, title: str) -> StoredFile:
    file_item = await session.get(StoredFile, file_id)
    if not file_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )
    file_item.title = title
    await session.commit()
    await session.refresh(file_item)
    return file_item


async def delete_file(session, file_id: str) -> None:
    file_item = await session.get(StoredFile, file_id)
    if not file_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )
    stored_path = STORAGE_DIR / file_item.stored_name
    if stored_path.exists():
        stored_path.unlink()
    await session.delete(file_item)
    await session.commit()


async def get_file_path(file_id: str) -> tuple[StoredFile, Path]:
    file_item = await get_file(file_id)
    stored_path = STORAGE_DIR / file_item.stored_name
    if not stored_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stored file not found"
        )
    return file_item, stored_path
