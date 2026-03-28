# Precis

Precis is a cloud based tool that helps you extract out important pieces from a pdf. This monorepo contains the backend API and mobile app.

## Local development

### API setup

Create a virtual environment and install dependencies in `packages/api`:

```bash
cd packages/api
python3 -m venv env
env/bin/pip install -r requirements.txt
```

The `dev` script in `packages/api/package.json` will use this venv automatically.

### Running

```bash
pnpm dev
```

This will run expo app and the api in dev mode.

---

## Deployment

The API is deployed on [Railway](https://railway.com).
