from fastapi import HTTPException
from fastapi import File, Form, UploadFile
from fastapi.responses import FileResponse
from starlette import status
from backend.file_service.models import FileItem, FileUpdate
from backend.file_service.service import (
    create_file,
    delete_file,
    get_file,
    list_files,
    update_file,
    STORAGE_DIR,
)
from backend.tasks import scan_file_for_threats
from backend.file_service.routers import file_router
from backend.repository import SessionDep


@file_router.get("/files", response_model=list[FileItem])
async def list_files_view(session: SessionDep):
    return await list_files(session)


@file_router.post("/files", response_model=FileItem, status_code=201)
async def create_file_view(
    session: SessionDep, title: str = Form(...), file: UploadFile = File(...)
):
    file_item = await create_file(session, title=title, upload_file=file)
    scan_file_for_threats.delay(file_item.id)
    return file_item


@file_router.get("/files/{file_id}", response_model=FileItem)
async def get_file_view(session: SessionDep, file_id: str):
    return await get_file(session, file_id)


@file_router.patch("/files/{file_id}", response_model=FileItem)
async def update_file_view(
    session: SessionDep,
    file_id: str,
    payload: FileUpdate,
):
    return await update_file(session, file_id=file_id, title=payload.title)


@file_router.get("/files/{file_id}/download")
async def download_file(session, file_id: str):
    file_item = await get_file(session, file_id)
    stored_path = STORAGE_DIR / file_item.stored_name
    if not stored_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stored file not found"
        )
    return FileResponse(
        path=stored_path,
        media_type=file_item.mime_type,
        filename=file_item.original_name,
    )


@file_router.delete("/files/{file_id}", status_code=204)
async def delete_file_view(session: SessionDep, file_id: str):
    await delete_file(session, file_id)
