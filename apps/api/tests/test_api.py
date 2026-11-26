from datetime import date

from conftest import login


def test_demo_login_all_roles(client):
    for role in ("WORKER", "COMPANY_MANAGER", "VDREAM_MANAGER", "SYSTEM_ADMIN"):
        h = login(client, role)
        assert client.get("/api/v1/auth/me", headers=h).json()["data"]["role"] == role


def test_message_recipients_restricted(client):
    wk = login(client, "WORKER")
    groups = client.get("/api/v1/messages/recipients", headers=wk).json()["data"]["groups"]
    names = {p["name"] for g in groups for p in g["people"]}
    assert "송유나" in names and "이수진" in names and "오세훈" not in names  # other company's manager hidden
    other_vm = client.get("/api/v1/messages/recipients?q=오세훈", headers=login(client, "VDREAM_MANAGER")).json()["data"]["groups"][0]["people"][0]["id"]
    r = client.post("/api/v1/messages", headers=wk, json={"recipientIds": [other_vm], "title": "t", "body": "b"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "MESSAGE_RECIPIENT_NOT_ALLOWED"


def test_manager_can_message_anyone_and_unread(client):
    vm = login(client, "VDREAM_MANAGER")
    r = client.post("/api/v1/messages", headers=vm, json={"audience": "ALL_WORKERS", "title": "공지", "body": "안녕하세요"})
    assert r.status_code == 200 and r.json()["data"]["recipientCount"] == 9
    assert client.get("/api/v1/me/unread-counts", headers=login(client, "WORKER")).json()["data"]["messages"] >= 1


def test_employment_report(client):
    cm = login(client, "COMPANY_MANAGER")
    today = date.today()
    frm = f"{today.year if today.month > 2 else today.year - 1}-{(today.month - 3) % 12 + 1:02d}"
    rep = client.get(f"/api/v1/reports/employment?from={frm}&to={today:%Y-%m}", headers=cm)
    assert rep.status_code == 200, rep.text
    results = {w["recognition"]["result"] for m in rep.json()["data"]["months"] for w in m["workers"]}
    assert {"DOUBLE", "SINGLE", "EXCLUDED", "NEEDS_REVIEW"} <= results
    assert client.get(f"/api/v1/reports/employment.xlsx?from={frm}&to={today:%Y-%m}", headers=cm).status_code == 200
    assert client.get(f"/api/v1/reports/employment?from={frm}&to={today:%Y-%m}", headers=login(client, "VDREAM_MANAGER")).status_code == 403


def test_counseling_hidden_from_company(client):
    assert client.get("/api/v1/counseling", headers=login(client, "COMPANY_MANAGER")).status_code == 403


def test_worker_daily_flow(client):
    wk, cm = login(client, "WORKER"), login(client, "COMPANY_MANAGER")
    today = client.get("/api/v1/attendance/today", headers=wk).json()["data"]
    if today["isWorkday"]:
        assert client.post("/api/v1/attendance/check-in", headers=wk).status_code == 200
    else:
        return
    task = client.get("/api/v1/tasks", headers=wk).json()["data"][0]
    d = date.today().isoformat()
    r = client.put(f"/api/v1/work-logs/me/{d}", headers=wk, json={"summary": "테스트", "entries": [{"taskId": task["id"], "title": task["title"], "content": "작업", "minutes": 120}]})
    assert r.status_code == 200, r.text
    wl = client.post(f"/api/v1/work-logs/me/{d}/submit", headers=wk).json()["data"]
    assert wl["status"] == "SUBMITTED"
    assert client.post(f"/api/v1/work-logs/{wl['id']}/confirm", headers=cm, json={}).json()["data"]["status"] == "CONFIRMED"
    assert client.post("/api/v1/attendance/check-out", headers=wk).status_code == 200


def test_hiring_flow(client):
    cm, vm = login(client, "COMPANY_MANAGER"), login(client, "VDREAM_MANAGER")
    apps = client.get("/api/v1/job-postings", headers=cm).json()["data"]
    passed = next(a for p in apps for a in client.get(f"/api/v1/job-postings/{p['id']}/applications", headers=cm).json()["data"] if a["status"] == "PASSED")
    r = client.post(f"/api/v1/applications/{passed['id']}/hire", headers=vm, json={"startDate": "2099-01-02"})
    assert r.status_code == 200 and r.json()["data"]["status"] == "HIRED"


def test_dashboards(client):
    for role in ("COMPANY_MANAGER", "VDREAM_MANAGER"):
        assert client.get("/api/v1/dashboard", headers=login(client, role)).status_code == 200
    assert client.get("/api/v1/system/dashboard", headers=login(client, "SYSTEM_ADMIN")).status_code == 200
