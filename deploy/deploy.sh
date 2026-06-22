#!/usr/bin/env bash
# Push to GitHub and deploy to GCP VM.
#
# Usage:
#   ./deploy/deploy.sh              # deploy only (git pull + rebuild on VM)
#   ./deploy/deploy.sh --push       # commit, push, then deploy
#   ./deploy/deploy.sh --push -m "fix pdf error"

set -euo pipefail

GCP_PROJECT_ID="${GCP_PROJECT_ID:-mtcverse}"
GCP_ZONE="${GCP_ZONE:-asia-northeast1-a}"
GCP_VM_INSTANCE="${GCP_VM_INSTANCE:-mt-estimate81-vm}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "${REPO_ROOT}"

if [[ "${1:-}" == "--push" ]]; then
  shift
  MESSAGE="update"
  if [[ "${1:-}" == "-m" ]]; then
    shift
    MESSAGE="${1:?commit message required after -m}"
    shift
  fi
  git add -A
  if git diff --cached --quiet; then
    echo "No changes to commit."
  else
    git commit -m "${MESSAGE}"
  fi
  git push origin main
fi

echo "Deploying to ${GCP_VM_INSTANCE}..."
gcloud compute ssh "${GCP_VM_INSTANCE}" \
  --zone="${GCP_ZONE}" \
  --project="${GCP_PROJECT_ID}" \
  --command="sudo -u github-deploy bash -c 'cd /opt/ai-estimate/app && git pull origin main && docker compose --env-file /opt/ai-estimate/deploy/.env -f docker-compose.vm.yml up -d --build && docker compose --env-file /opt/ai-estimate/deploy/.env -f docker-compose.vm.yml ps'"

echo "Done. App: http://34.153.193.172"
