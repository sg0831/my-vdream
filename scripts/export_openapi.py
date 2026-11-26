"""서버를 띄우지 않고 OpenAPI JSON을 내보낸다. 사용: python scripts/export_openapi.py > apps/web/openapi.json"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))
os.environ.setdefault("SEED_ON_EMPTY", "false")

from app.main import app  # noqa: E402

print(json.dumps(app.openapi(), ensure_ascii=False, indent=1, sort_keys=True))
