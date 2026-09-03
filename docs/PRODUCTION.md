# Production guide — AURI.AI

## Checklist

- Strong SECRET_KEY and SETTINGS_ENCRYPTION_KEY
- Postgres backups
- Redis
- S3/MinIO
- AI_MODE=strict_private for sensitive orgs
- TLS via Caddy or Nginx
- Stripe webhooks
- SMTP for invites
- Sentry DSN

## Deploy

```bash
cp .env.example .env
./scripts/deploy.sh
```

## Probes

- GET /live
- GET /ready
- GET /health
- GET /metrics

## GDPR

```
PUT /api/v1/gdpr/retention
POST /api/v1/gdpr/retention/purge?dry_run=true
GET /api/v1/gdpr/export/me
```
