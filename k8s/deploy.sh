#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-"$SCRIPT_DIR/../.env"}"

echo "Deploying Precis API..."

kubectl apply -f "$SCRIPT_DIR/namespace.yaml"

# Load secrets from .env and upsert the Kubernetes secret
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: .env file not found at $ENV_FILE" >&2
  exit 1
fi

# Parse .env: skip blank lines and comments, export KEY=VALUE pairs
declare -A env_vars
while IFS='=' read -r key value; do
  [[ -z "$key" || "$key" == \#* ]] && continue
  # Strip surrounding quotes from value
  value="${value%\"}"
  value="${value#\"}"
  value="${value%\'}"
  value="${value#\'}"
  env_vars["$key"]="$value"
done < <(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$')

required_keys=(DATABASE_URL JWT_SECRET_KEY GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY STORAGE_BUCKET)
literal_args=()
for key in "${required_keys[@]}"; do
  if [[ -z "${env_vars[$key]+set}" ]]; then
    echo "ERROR: $key not found in $ENV_FILE" >&2
    exit 1
  fi
  literal_args+=("--from-literal=${key}=${env_vars[$key]}")
done

kubectl create secret generic precis-api-secrets \
  --namespace=precis \
  "${literal_args[@]}" \
  --dry-run=client -o yaml | kubectl apply -f -

configmap_keys=(DEBUG GOOGLE_REDIRECT_URI STORAGE_REGION STORAGE_ENDPOINT_URL MAX_UPLOAD_SIZE_MB OCR_LANGUAGE)
configmap_args=()
for key in "${configmap_keys[@]}"; do
  if [[ -z "${env_vars[$key]+set}" ]]; then
    echo "ERROR: $key not found in $ENV_FILE" >&2
    exit 1
  fi
  configmap_args+=("--from-literal=${key}=${env_vars[$key]}")
done

kubectl create configmap precis-api-config \
  --namespace=precis \
  "${configmap_args[@]}" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f "$SCRIPT_DIR/api-deployment.yaml"
kubectl apply -f "$SCRIPT_DIR/api-service.yaml"
kubectl apply -f "$SCRIPT_DIR/api-ingress.yaml"
kubectl apply -f "$SCRIPT_DIR/api-hpa.yaml"

echo "Waiting for rollout..."
kubectl rollout status deployment/precis-api -n precis

echo "Done."
