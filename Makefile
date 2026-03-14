PYTHON ?= python

.PHONY: dev-api test dev-console

dev-api:
	uvicorn apps.api.app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest apps/api/tests packages/db/tests packages/orchestrator/tests

dev-console:
	cd apps/console && npm run dev
