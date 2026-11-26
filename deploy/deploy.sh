#!/usr/bin/env bash
# EC2에서 실행. CD 워크플로가 SSH로 호출한다. 롤백: IMAGE_TAG=sha-<커밋> bash deploy/deploy.sh
set -euo pipefail
cd "$(dirname "$0")"
set -a; source ../.env; set +a
docker compose -f docker-compose.yml pull
docker compose -f docker-compose.yml up -d --remove-orphans
docker image prune -f
