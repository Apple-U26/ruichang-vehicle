#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/home/ubuntu/ruichang-vehicle}"
BRANCH="${BRANCH:-main}"

cd "$APP_DIR"
git pull --ff-only origin "$BRANCH"

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd ../frontend
npm install
npm run build

cd ../backend
python -m app.seed

sudo systemctl restart ruichang-vehicle

echo "部署完成：$(date '+%Y-%m-%d %H:%M:%S')"
