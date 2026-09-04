#!/usr/bin/env bash
set -euo pipefail
echo "SECRET_KEY=$(openssl rand -hex 48)"
echo "SETTINGS_ENCRYPTION_KEY=$(openssl rand -hex 32)"
