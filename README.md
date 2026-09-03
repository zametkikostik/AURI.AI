<p align="center">
  <img src="docs/assets/logo-placeholder.svg" alt="AURI.AI" width="72" height="72" />
</p>

<h1 align="center">AURI.AI</h1>

<p align="center">
  <strong>Privacy-first AI Meeting Assistant & Knowledge Platform</strong><br/>
  Enterprise-minded alternative to Fireflies / Recall — your data stays yours.
</p>

<p align="center">
  <a href="#features">Features</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="#i18n">Languages</a> ·
  <a href="#license">License</a>
</p>

<p align="center">
  <img alt="Stack" src="https://img.shields.io/badge/FastAPI-Next.js-Qdrant-0ea5e9" />
  <img alt="AI" src="https://img.shields.io/badge/AI-Ollama%20%2B%20Whisper-22c55e" />
  <img alt="Privacy" src="https://img.shields.io/badge/Default-strict__private-a855f7" />
  <img alt="License" src="https://img.shields.io/badge/License-Source--Available-red" />
</p>

---

## Why AURI.AI?

Most meeting AI tools send audio and transcripts to third-party clouds.
**AURI.AI defaults to `strict_private`**: local speech-to-text and local LLM (Ollama) so sensitive conversations never leave your infrastructure.

Built for **funds, foundations, and enterprises** that need trust, SSO, audit logs, and deploy control.

## Features

| Area | Capabilities |
|------|----------------|
| **Capture** | Upload recordings · Zoom webhook ingest · bot join stubs |
| **Intelligence** | Transcription · summaries · topics · action items · knowledge extract |
| **Search** | Semantic · keyword · hybrid over Qdrant |
| **Privacy** | Ollama-first · encrypted integration secrets · retention / GDPR export |
| **Team** | Invites · RBAC · audit trail · multi-language UI |
| **Billing** | Free limits · Stripe Checkout · Customer Portal |
| **Ops** | Docker · Helm · blue/green · Prometheus / Grafana / Loki |

## Architecture

```
Next.js UI  →  FastAPI API  →  Postgres · Redis · MinIO
                    │
              Celery worker  →  Whisper · Ollama · Qdrant
```

- **Backend:** Python 3.12, FastAPI, Celery, SQLAlchemy, Alembic
- **Frontend:** Next.js App Router, Tailwind
- **AI:** faster-whisper, Ollama (`strict_private`), optional pyannote
- **Search:** Qdrant vectors + hybrid ranking

## Quick Start

```bash
git clone https://github.com/zametkikostik/AURI.AI.git
cd AURI.AI
cp .env.example .env
./scripts/gen-secrets.sh
./scripts/start-infra.sh

cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
celery -A app.workers.celery_app.celery_app worker -l info

cd ../frontend && npm install && npm run dev
```

Open http://localhost:3000 — API docs http://localhost:8000/docs (dev only).

> **License notice:** viewing the code is allowed. Running or forking for product use requires a commercial license — see [LICENSE](LICENSE).

## Production

```bash
./scripts/deploy.sh
./scripts/backup.sh
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml --profile monitoring up -d
./scripts/blue-green-deploy.sh
```

See [`docs/PRODUCTION.md`](docs/PRODUCTION.md) and [`docs/OPS.md`](docs/OPS.md).

## i18n

Language switcher in the sidebar:

| Code | Language |
|------|----------|
| `en` | English |
| `ru` | Русский |
| `bg` | Български |
| `th` | ไทย |
| `it` | Italiano |

Stored in `localStorage` (`auri_locale`). Dictionaries: `frontend/lib/i18n/dictionaries/`.

## API (high level)

```
/api/v1/auth · meetings · search · knowledge · exports
/api/v1/billing · gdpr · oidc · members · webhooks
/metrics · /live · /ready · /health
```

## License

**Source-available proprietary.**

You may **view** this repository. You may **not** run it in production, fork it, or build products on it without a written commercial license from the authors.

Full terms: [LICENSE](LICENSE).

---

<p align="center">Built for organizations that treat meetings as confidential by default.</p>
