# CI / Deploy secrets

Configure in **GitHub → Settings → Secrets and variables → Actions**.

## Required for private deploys

| Secret | Description |
|--------|-------------|
| `DEPLOY_HOST` | SSH hostname or IP |
| `DEPLOY_USER` | SSH user (e.g. `deploy`) |
| `DEPLOY_SSH_KEY` | Private key (ed25519) |
| `DEPLOY_PATH` | Optional. Default `/opt/auri` |

## Optional

| Secret | Description |
|--------|-------------|
| `NEXT_PUBLIC_API_URL` | Public API URL for frontend image |
| `KUBE_CONFIG` | Kubeconfig for Helm |
| `SENTRY_DSN` | Error tracking |
| `STRIPE_SECRET_KEY` | Billing |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhooks |
| `STRIPE_PRICE_ENTERPRISE` | Enterprise price ID |

## Environments

1. **staging**
2. **production** (required reviewers recommended)

Deploy: Actions → Deploy → Run workflow, or push tag `v*`.

## Local smoke

```bash
docker compose up -d postgres redis minio qdrant ollama
docker compose up -d --build backend worker frontend
docker compose exec backend alembic upgrade head
python scripts/seed_dev.py

curl -s http://localhost:8000/health | jq
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"dev@auri.ai","password":"devpassword123"}' | jq
```

Generate secrets: `./scripts/gen-secrets.sh`
Default AI mode: `strict_private` (Ollama only).
