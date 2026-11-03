from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.files import MAX_UPLOAD_BYTES, is_acceptable_name, safe_file_name
from app.schemas import UploadOut
from app.security import Identity, get_identity
from app.services.requirements import store_upload

router = APIRouter(prefix="/api")


@router.post("/requirements", status_code=201, response_model=UploadOut)
async def upload_requirement(
    request: Request,
    file: UploadFile = File(...),
    identity: Identity = Depends(get_identity),
) -> UploadOut:
    file_name = safe_file_name(file.filename or "")
    if not is_acceptable_name(file_name):
        raise HTTPException(status_code=400, detail="Invalid file name or extension")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large")
    return store_upload(request.app.state.settings.upload_dir, file_name, content, identity.username)
