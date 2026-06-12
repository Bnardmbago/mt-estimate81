#!/usr/bin/env bash
# One-time GCP + GitHub Actions bootstrap for mt-estimate81.
# Run locally with gcloud authenticated as a project owner.
#
# Usage:
#   export GCP_PROJECT_ID=your-project
#   export GCP_REGION=asia-northeast1          # optional, default Tokyo
#   export GITHUB_REPO=Bnardmbago/mt-estimate81
#   ./deploy/gcp-setup.sh

set -euo pipefail

GCP_PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
GCP_REGION="${GCP_REGION:-asia-northeast1}"
GCP_ZONE="${GCP_ZONE:-${GCP_REGION}-a}"
GITHUB_REPO="${GITHUB_REPO:-Bnardmbago/mt-estimate81}"
AR_REPO="${AR_REPO:-ai-estimate}"
SA_NAME="${SA_NAME:-github-deploy}"
WIF_POOL="${WIF_POOL:-github-pool}"
WIF_PROVIDER="${WIF_PROVIDER:-github-provider}"
VM_NAME="${VM_NAME:-ai-estimate-vm}"
VM_MACHINE_TYPE="${VM_MACHINE_TYPE:-e2-standard-4}"

echo "==> Project: ${GCP_PROJECT_ID}  Region: ${GCP_REGION}"

gcloud config set project "${GCP_PROJECT_ID}"

echo "==> Enabling APIs..."
gcloud services enable \
  artifactregistry.googleapis.com \
  compute.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  cloudresourcemanager.googleapis.com \
  sts.googleapis.com

echo "==> Creating Artifact Registry repository..."
gcloud artifacts repositories describe "${AR_REPO}" \
  --location="${GCP_REGION}" >/dev/null 2>&1 || \
gcloud artifacts repositories create "${AR_REPO}" \
  --repository-format=docker \
  --location="${GCP_REGION}" \
  --description="AI Estimate MVP container images"

echo "==> Creating deploy service account..."
SA_EMAIL="${SA_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe "${SA_EMAIL}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="GitHub Actions deploy"
  echo "    Waiting for service account to propagate..."
  for i in 1 2 3 4 5 6 7 8 9 10; do
    gcloud iam service-accounts describe "${SA_EMAIL}" >/dev/null 2>&1 && break
    sleep 3
  done
fi

for role in \
  roles/artifactregistry.writer \
  roles/compute.instanceAdmin.v1 \
  roles/iam.serviceAccountUser \
  roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "${GCP_PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${role}" \
    --quiet >/dev/null
done

echo "==> Configuring Workload Identity Federation for GitHub..."
gcloud iam workload-identity-pools describe "${WIF_POOL}" \
  --location=global >/dev/null 2>&1 || \
gcloud iam workload-identity-pools create "${WIF_POOL}" \
  --location=global \
  --display-name="GitHub Actions"

WIF_POOL_ID="$(gcloud iam workload-identity-pools describe "${WIF_POOL}" \
  --location=global --format='value(name)')"

gcloud iam workload-identity-pools providers describe "${WIF_PROVIDER}" \
  --workload-identity-pool="${WIF_POOL}" \
  --location=global >/dev/null 2>&1 || \
gcloud iam workload-identity-pools providers create-oidc "${WIF_PROVIDER}" \
  --workload-identity-pool="${WIF_POOL}" \
  --location=global \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='${GITHUB_REPO}'"

gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${WIF_POOL_ID}/attribute.repository/${GITHUB_REPO}" \
  --quiet >/dev/null

WIF_PROVIDER_FULL="projects/$(gcloud projects describe "${GCP_PROJECT_ID}" --format='value(projectNumber)')/locations/global/workloadIdentityPools/${WIF_POOL}/providers/${WIF_PROVIDER}"

echo "==> Creating Compute Engine VM (skip if it already exists)..."
if [[ "${SKIP_VM:-}" == "1" ]]; then
  echo "    SKIP_VM=1 — VM creation skipped (create and bootstrap the VM manually)."
else
if ! gcloud compute instances describe "${VM_NAME}" --zone="${GCP_ZONE}" >/dev/null 2>&1; then
  gcloud compute instances create "${VM_NAME}" \
    --zone="${GCP_ZONE}" \
    --machine-type="${VM_MACHINE_TYPE}" \
    --boot-disk-size=100GB \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --tags=http-server \
    --scopes=cloud-platform

  gcloud compute firewall-rules describe allow-ai-estimate-http >/dev/null 2>&1 || \
  gcloud compute firewall-rules create allow-ai-estimate-http \
    --allow=tcp:80 \
    --target-tags=http-server \
    --description="Allow HTTP to AI Estimate nginx"

  echo "==> Installing Docker on VM..."
  gcloud compute ssh "${VM_NAME}" --zone="${GCP_ZONE}" --quiet --command="
    set -e
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo \"deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \$(. /etc/os-release && echo \$VERSION_CODENAME) stable\" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin python3-minimal
    sudo usermod -aG docker \$USER
    sudo mkdir -p /opt/ai-estimate/deploy
  "
fi
fi

echo "==> Grant VM access to pull from Artifact Registry..."
PROJECT_NUMBER="$(gcloud projects describe "${GCP_PROJECT_ID}" --format='value(projectNumber)')"
gcloud projects add-iam-policy-binding "${GCP_PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/artifactregistry.reader" \
  --quiet >/dev/null

echo
echo "=== GitHub repository configuration ==="
echo
echo "Repository variables (Settings → Secrets and variables → Actions → Variables):"
echo "  GCP_PROJECT_ID          = ${GCP_PROJECT_ID}"
echo "  GCP_REGION              = ${GCP_REGION}"
echo "  GCP_VM_INSTANCE         = ${VM_NAME}"
echo "  GCP_VM_ZONE             = ${GCP_ZONE}"
echo "  GCP_SERVICE_ACCOUNT     = ${SA_EMAIL}"
echo "  GCP_WORKLOAD_IDENTITY_PROVIDER = ${WIF_PROVIDER_FULL}"
echo
echo "Repository secret:"
echo "  GCP_SSH_PRIVATE_KEY     = SSH private key for the VM deploy user"
echo "    Generate: ssh-keygen -t ed25519 -C github-deploy -f ./github-deploy -N \"\""
echo "  gcloud compute instances add-metadata ${VM_NAME} --zone=${GCP_ZONE} \\"
echo "    --metadata-from-file ssh-keys=<(echo \"github-deploy:\$(cat github-deploy.pub)\")"
echo
echo "Then grant the deploy user Docker access (run once after adding the SSH key):"
echo "  gcloud compute ssh ${VM_NAME} --zone=${GCP_ZONE} --command=\"sudo usermod -aG docker github-deploy && sudo chown -R github-deploy:github-deploy /opt/ai-estimate\""
echo
echo "=== One-time VM setup ==="
echo
echo "Create /opt/ai-estimate/deploy/.env on the VM (copy from .env.example, set production values):"
echo "  APP_ENV=production"
echo "  COOKIE_SECURE=true"
echo "  POSTGRES_PASSWORD=<strong password>"
echo "  JWT_SECRET=<random 64 chars>"
echo "  AI API keys"
echo
echo "  gcloud compute ssh ${VM_NAME} --zone=${GCP_ZONE}"
echo "  sudo nano /opt/ai-estimate/deploy/.env"
echo
echo "After the first deploy, seed the admin user once:"
echo "  cd /opt/ai-estimate/deploy && docker compose -f docker-compose.prod.yml exec api python scripts/seed_admin.py"
echo
echo "Push to main (or run the workflow manually) to deploy."
