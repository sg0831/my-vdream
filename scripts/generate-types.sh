#!/usr/bin/env bash
# API의 OpenAPI 스키마로 프론트 TypeScript 타입을 다시 만든다. CI는 결과가 커밋된 파일과 같은지 검사한다.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-apps/api/.venv/bin/python}
"$PY" scripts/export_openapi.py > apps/web/openapi.json
(cd apps/web && npx openapi-typescript openapi.json -o src/api-schema.d.ts)
