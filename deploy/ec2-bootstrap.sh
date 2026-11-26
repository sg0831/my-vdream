#!/usr/bin/env bash
# Ubuntu 24.04 EC2 최초 1회. 사용법: bash ec2-bootstrap.sh <github-repo-url>
set -euo pipefail
sudo apt-get update && sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
git clone "$1" ~/my-vdream
cp ~/my-vdream/.env.example ~/my-vdream/.env
echo "~/my-vdream/.env 를 채운 뒤 다시 로그인하고 bash ~/my-vdream/deploy/deploy.sh 를 실행하세요."
