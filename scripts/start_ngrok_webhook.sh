#!/usr/bin/env bash
set -euo pipefail
if [ -f ".env" ]; then export $(grep -v '^#' .env | xargs) || true; fi
python3 scripts/run_webhook_with_ngrok.py
