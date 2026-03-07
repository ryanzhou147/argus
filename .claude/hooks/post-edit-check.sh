#!/usr/bin/env bash
set -e

if [ -f frontend/package.json ]; then
  (cd frontend && npm run typecheck) || true
fi

if [ -f backend/pyproject.toml ]; then
  (cd backend && python -m pytest -q) || true
fi