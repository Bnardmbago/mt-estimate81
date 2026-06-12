#!/usr/bin/env bash
# Run once on a fresh Ubuntu 22.04 VM (via SSH) after creating it in GCP Console.
# Installs Docker, creates deploy directories, and prepares for GitHub Actions deploy.

set -euo pipefail

sudo apt-get update
sudo apt-get install -y ca-certificates curl python3-minimal
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

sudo mkdir -p /opt/ai-estimate/deploy /opt/ai-estimate/nginx

if id github-deploy >/dev/null 2>&1; then
  sudo usermod -aG docker github-deploy
  sudo chown -R github-deploy:github-deploy /opt/ai-estimate
fi

echo "Done. Next: create /opt/ai-estimate/deploy/.env and add the github-deploy SSH key."
