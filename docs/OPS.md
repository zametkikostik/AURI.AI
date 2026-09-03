# Operations

## Multi-env

```bash
cp infra/env/staging.env.example infra/env/staging.env
cp infra/env/prod.env.example infra/env/prod.env
./scripts/gen-secrets.sh
```

## Blue/green

```bash
./scripts/blue-green-deploy.sh
```

## Monitoring

```bash
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml --profile monitoring up -d
```

Grafana :3001 · Prometheus :9090 · App /metrics
