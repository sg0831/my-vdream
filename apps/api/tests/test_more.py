import io

from conftest import login

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def test_photo_upload_and_access(client):
    wk = login(client, "WORKER")
    me = client.get("/api/v1/auth/me", headers=wk).json()["data"]
    r = client.post(f"/api/v1/resumes/{me['id']}/photo", headers=wk, files={"file": ("me.png", io.BytesIO(PNG), "image/png")})
    assert r.status_code == 200, r.text
    fid = r.json()["data"]["photoFileId"]
    url = client.get(f"/api/v1/files/{fid}/url", headers=wk).json()["data"]["url"]
    assert client.get(url).status_code == 200
    assert client.get(f"/api/v1/files/{fid}/url", headers=login(client, "COMPANY_MANAGER")).status_code == 200  # 자기 기업 재직자
    bad = client.post(f"/api/v1/resumes/{me['id']}/photo", headers=wk, files={"file": ("x.exe", io.BytesIO(b"MZ"), "application/x-msdownload")})
    assert bad.status_code == 400


def test_inactive_company_blocks_login(client):
    sa = login(client, "SYSTEM_ADMIN")
    cos = client.get("/api/v1/companies", headers=sa).json()["data"]
    c = next(x for x in cos if x["name"] == "(주)바른리서치")
    body = {k: c[k] for k in ("name", "businessRegistrationNo", "representativeName", "employmentInsuranceNo", "industry", "address", "phone", "managerId")}
    assert client.put(f"/api/v1/companies/{c['id']}", headers=sa, json=body | {"status": "INACTIVE"}).status_code == 200
    r = client.post("/api/v1/auth/login", json={"loginId": "cm.moon", "password": "demo1234!"})
    assert r.status_code == 403
    client.put(f"/api/v1/companies/{c['id']}", headers=sa, json=body | {"status": "ACTIVE"})
    assert client.post("/api/v1/auth/login", json={"loginId": "cm.moon", "password": "demo1234!"}).status_code == 200


def test_counseling_filters_and_dashboard(client):
    vm = login(client, "VDREAM_MANAGER")
    all_ = client.get("/api/v1/counseling", headers=vm).json()["data"]
    cid = next(r["companyId"] for r in all_ if r["companyId"])
    filtered = client.get(f"/api/v1/counseling?company_id={cid}", headers=vm).json()["data"]
    assert filtered and all(r["companyId"] == cid for r in filtered) and len(filtered) <= len(all_)
    d = client.get("/api/v1/dashboard", headers=vm).json()["data"]
    assert d["byCompany"]
    cm = client.get("/api/v1/dashboard", headers=login(client, "COMPANY_MANAGER")).json()["data"]
    assert "recognizedCount" in cm["lastMonthReport"]


def test_posting_author_filter(client):
    vm = login(client, "VDREAM_MANAGER")
    rows = client.get("/api/v1/job-postings?author_type=VDREAM", headers=vm).json()["data"]
    assert rows and all(r["authorType"] == "VDREAM" for r in rows)


def test_seed_has_ten_applications(client):
    vm = login(client, "VDREAM_MANAGER")
    total = sum(len(client.get(f"/api/v1/job-postings/{p['id']}/applications", headers=vm).json()["data"])
                for p in client.get("/api/v1/job-postings", headers=vm).json()["data"])
    assert total >= 10
