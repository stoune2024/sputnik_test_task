import asyncio
import os
from pathlib import Path
from celery import Celery
from backend.schemas import Alert, StoredFile
from backend.file_service.service import STORAGE_DIR
from enum import Enum
from backend.repository import SessionDep

REDIS_URL = os.environ.get("REDIS_URL", "redis://backend-redis:6379/0")
_worker_loop: asyncio.AbstractEventLoop | None = None


class TaskStatus(Enum):
    processing = "processing"
    uploaded = "uploaded"
    processed = "processed"
    failed = "failed"
    suspicious = "suspicious"
    clean = "clean"


def run_in_worker_loop(coroutine):
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)
    return _worker_loop.run_until_complete(coroutine)


celery_app = Celery("file_tasks", broker=REDIS_URL, backend=REDIS_URL)


async def _scan_file_for_threats(session, file_id: str) -> None:
    file_item = await session.get(StoredFile, file_id)
    if not file_item:
        return

    file_item.processing_status = TaskStatus.processing
    reasons: list[str] = []
    extension = Path(file_item.original_name).suffix.lower()

    if extension in {".exe", ".bat", ".cmd", ".sh", ".js"}:
        reasons.append(f"suspicious extension {extension}")

    if file_item.size > 10 * 1024 * 1024:
        reasons.append("file is larger than 10 MB")

    if extension == ".pdf" and file_item.mime_type not in {
        "application/pdf",
        "application/octet-stream",
    }:
        reasons.append("pdf extension does not match mime type")

    file_item.scan_status = TaskStatus.suspicious if reasons else TaskStatus.clean
    file_item.scan_details = ", ".join(reasons) if reasons else "no threats found"
    file_item.requires_attention = bool(reasons)
    await session.commit()

    extract_file_metadata.delay(session, file_id)


async def _extract_file_metadata(session, file_id: str) -> None:
    file_item = await session.get(StoredFile, file_id)
    if not file_item:
        return

    stored_path = STORAGE_DIR / file_item.stored_name
    if not stored_path.exists():
        file_item.processing_status = TaskStatus.failed
        file_item.scan_status = file_item.scan_status or TaskStatus.failed
        file_item.scan_details = "stored file not found during metadata extraction"
        await session.commit()
        send_file_alert.delay(file_id)
        return

    metadata = {
        "extension": Path(file_item.original_name).suffix.lower(),
        "size_bytes": file_item.size,
        "mime_type": file_item.mime_type,
    }

    if file_item.mime_type.startswith("text/"):
        content = stored_path.read_text(encoding="utf-8", errors="ignore")
        metadata["line_count"] = len(content.splitlines())
        metadata["char_count"] = len(content)
    elif file_item.mime_type == "application/pdf":
        content = stored_path.read_bytes()
        metadata["approx_page_count"] = max(content.count(b"/Type /Page"), 1)

    file_item.metadata_json = metadata
    file_item.processing_status = TaskStatus.processed
    await session.commit()

    send_file_alert.delay(session, file_id)


async def _send_file_alert(session, file_id: str) -> None:
    file_item = await session.get(StoredFile, file_id)
    if not file_item:
        return

    if file_item.processing_status == TaskStatus.failed:
        alert = Alert(
            file_id=file_id, level="critical", message="File processing failed"
        )
    elif file_item.requires_attention:
        alert = Alert(
            file_id=file_id,
            level="warning",
            message=f"File requires attention: {file_item.scan_details}",
        )
    else:
        alert = Alert(
            file_id=file_id, level="info", message="File processed successfully"
        )

    session.add(alert)
    await session.commit()


@celery_app.task
def scan_file_for_threats(session: SessionDep, file_id: str) -> None:
    run_in_worker_loop(_scan_file_for_threats(session, file_id))


@celery_app.task
def extract_file_metadata(session, file_id: str) -> None:
    run_in_worker_loop(_extract_file_metadata(session, file_id))


@celery_app.task
def send_file_alert(session, file_id: str) -> None:
    run_in_worker_loop(_send_file_alert(session, file_id))
