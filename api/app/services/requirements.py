from __future__ import annotations

import uuid
from pathlib import Path

from app.schemas import UploadOut


def store_upload(upload_dir: str, file_name: str, content: bytes, owner: str) -> UploadOut:
    target = Path(upload_dir) / f"{uuid.uuid4().hex}-{file_name}"
    target.write_bytes(content)
    return UploadOut(owner=owner, fileName=file_name, storedAt=str(target), size=len(content))
