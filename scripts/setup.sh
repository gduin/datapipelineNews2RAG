#!/usr/bin/env bash
set -euo pipefail
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
cp -n .env.example .env || true
echo "Setup complete. Activate with: source .venv/bin/activate"
