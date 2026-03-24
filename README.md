# Precis

Precis is a cloud based tool that helps you extract out important pieces from a pdf. This monorepo contains the backend API and mobile app.

## Local development

### API

```bash
cd packages/api
cp .env.example .env          # fill in your values
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

---

## Deployment

The API image is built and pushed to `ghcr.io/shivang991/precis-api` automatically on every push to `main` that touches `packages/api/`. Two tags are produced: `latest` and `sha-<commit>` for pinned rollbacks.

### First-time setup

1. Create a GitHub PAT with `read:packages` scope, then add it as a GHCR pull secret:

```bash
kubectl create secret docker-registry ghcr-credentials \
  --namespace precis \
  --docker-server=ghcr.io \
  --docker-username=shivang991 \
  --docker-password=<your-github-PAT>
```

2. Copy `.env.example`, fill in all values, then run the deploy script:

```bash
cp packages/api/.env.example .env
# edit .env
./k8s/deploy.sh
```

`deploy.sh` applies all manifests, upserts the Kubernetes secret from your `.env`, and waits for the rollout to complete.

### Subsequent deploys

CI pushes a new image on every merge to `main`. To pull it into the cluster:

```bash
kubectl rollout restart deployment/precis-api -n precis
```

To pin a specific SHA:

```bash
kubectl set image deployment/precis-api \
  api=ghcr.io/shivang991/precis-api:sha-<commit> \
  -n precis
```

### Rollback

```bash
kubectl rollout undo deployment/precis-api -n precis
```

---

## Adding new environment variables

All configuration lives in `.env`. The deploy script reads it and upserts both the Kubernetes Secret and ConfigMap automatically.

**Secrets** (API keys, passwords, etc.):

1. Add the key with a placeholder to `.env.example`.
2. Add the key name to the `required_keys` array in [k8s/deploy.sh](k8s/deploy.sh).

**Config** (feature flags, URLs, limits, etc.):

1. Add the key with its default to `.env.example`.
2. Add the key name to the `configmap_keys` array in [k8s/deploy.sh](k8s/deploy.sh).

Re-run `./k8s/deploy.sh` to apply the changes to the cluster.
