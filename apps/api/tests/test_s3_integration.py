"""S3 저장 경로 통합 테스트. S3 호환 서버가 있을 때만 실행한다.
예: moto_server -p 19000 후  S3_TEST_ENDPOINT=http://127.0.0.1:19000 pytest tests/test_s3_integration.py
"""
import io
import os
from datetime import date

import httpx
import pytest

ENDPOINT = os.environ.get("S3_TEST_ENDPOINT")
pytestmark = pytest.mark.skipif(not ENDPOINT, reason="S3_TEST_ENDPOINT 미설정")


def test_upload_and_presigned_download(client, monkeypatch):
    import boto3
    from conftest import login

    from app.config import settings

    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    for k, v in {"storage_backend": "s3", "s3_bucket": "mv-test", "s3_region": "us-east-1", "s3_endpoint": ENDPOINT}.items():
        monkeypatch.setattr(settings, k, v)
    boto3.client("s3", endpoint_url=ENDPOINT, region_name="us-east-1").create_bucket(Bucket="mv-test")

    h = login(client, "WORKER")
    me = client.get("/api/v1/auth/me", headers=h).json()["data"]
    client.post("/api/v1/attendance/check-in", headers=h)
    d = date.today().isoformat()
    r = client.post(f"/api/v1/work-logs/me/{d}/files", headers=h, files={"file": ("결과물.pdf", io.BytesIO(b"%PDF-1.4 demo"), "application/pdf")})
    assert r.status_code == 200, r.text
    fid = r.json()["data"]["files"][-1]["id"]
    url = client.get(f"/api/v1/files/{fid}/url", headers=h).json()["data"]["url"]
    assert url.startswith(ENDPOINT)
    got = httpx.get(url)
    assert got.status_code == 200 and got.content == b"%PDF-1.4 demo"

    p = client.post(f"/api/v1/resumes/{me['id']}/photo", headers=h, files={"file": ("me.png", io.BytesIO(b"\x89PNG\r\n\x1a\n0000"), "image/png")})
    purl = client.get(f"/api/v1/files/{p.json()['data']['photoFileId']}/url", headers=h).json()["data"]["url"]
    assert httpx.get(purl).status_code == 200
