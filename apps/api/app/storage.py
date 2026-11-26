import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
from fastapi import UploadFile
from sqlalchemy.orm import Session

from . import models as M
from .config import settings
from .core import AppError
from .enums import FilePurpose


def s3():
    import boto3
    from botocore.config import Config
    return boto3.client("s3", region_name=settings.s3_region, endpoint_url=settings.s3_endpoint or None,
                        config=Config(signature_version="s3v4", s3={"addressing_style": "path" if settings.s3_endpoint else "auto"}))

ALLOWED = {
    FilePurpose.PROFILE_PHOTO: ({"image/jpeg", "image/png"}, 5),
    FilePurpose.WORK_LOG_ATTACHMENT: ({"application/pdf", "image/jpeg", "image/png", "application/zip", "application/x-zip-compressed",
                                       "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "text/plain"}, 10),
}


async def save_upload(db: Session, f: UploadFile, purpose: FilePurpose, user_id: int) -> M.File:
    types, mb = ALLOWED[purpose]
    data = await f.read()
    if (f.content_type or "") not in types:
        raise AppError("FILE_TYPE_NOT_ALLOWED", "허용되지 않는 파일 형식입니다.")
    if len(data) > mb * 1024 * 1024:
        raise AppError("FILE_TOO_LARGE", f"{mb}MB 이하 파일만 올릴 수 있습니다.")
    ext = (f.filename or "file").rsplit(".", 1)[-1][:10]
    now = datetime.now(UTC)
    key = f"{purpose.value.lower()}/{now:%Y/%m}/{uuid.uuid4().hex}.{ext}"
    if settings.storage_backend == "s3":
        s3().put_object(Bucket=settings.s3_bucket, Key=key, Body=data, ContentType=f.content_type)
    else:
        path = Path(settings.upload_dir) / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    row = M.File(storage_key=key, original_name=f.filename or "file", mime_type=f.content_type or "", size_bytes=len(data), purpose=purpose, uploaded_by=user_id)
    db.add(row)
    db.flush()
    return row


def download_url(f: M.File) -> str:
    if settings.storage_backend == "s3":
        return s3().generate_presigned_url(
            "get_object", Params={"Bucket": settings.s3_bucket, "Key": f.storage_key,
                                  "ResponseContentDisposition": f"attachment; filename*=UTF-8''{__import__('urllib.parse').parse.quote(f.original_name)}"}, ExpiresIn=600)
    sig = jwt.encode({"fid": f.id, "exp": datetime.now(UTC) + timedelta(minutes=10)}, settings.jwt_secret, algorithm="HS256")
    return f"/api/v1/files/{f.id}/content?sig={sig}"


def verify_sig(fid: int, sig: str) -> bool:
    try:
        return jwt.decode(sig, settings.jwt_secret, algorithms=["HS256"]).get("fid") == fid
    except jwt.PyJWTError:
        return False
