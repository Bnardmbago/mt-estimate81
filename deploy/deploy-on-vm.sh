#!/usr/bin/env bash
# Run ON the VM to deploy latest code from GitHub (no GitHub Actions).
#
# One-time setup:
#   sudo mkdir -p /opt/ai-estimate/app
#   sudo git clone https://github.com/Bnardmbago/mt-estimate81.git /opt/ai-estimate/app
#   sudo chown -R $USER:$USER /opt/ai-estimate
#
# Deploy / update:
#   ./deploy/deploy-on-vm.sh

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/ai-estimate/app}"
ENV_FILE="${ENV_FILE:-/opt/ai-estimate/deploy/.env}"
BRANCH="${BRANCH:-main}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE} — create it from .env.example first."
  exit 1
fi

cd "${APP_DIR}"
git fetch origin "${BRANCH}"
git checkout "${BRANCH}"
git pull origin "${BRANCH}"

docker compose --env-file "${ENV_FILE}" -f docker-compose.vm.yml up -d --build

echo "Deploy complete. Open http://$(curl -sf -H Metadata-Flavor:Google http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip 2>/dev/null || echo '<vm-external-ip>')"
