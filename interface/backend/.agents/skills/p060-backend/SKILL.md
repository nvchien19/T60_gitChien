---
name: p060-backend
description: Build and fix the P-060 FastAPI backend in interface/backend, including Pydantic contracts, async database access, repositories, services and AI adapter integration. Use for API and backend behavior in this folder.
---

# P-060 backend

Read interface/backend/README.md and the affected implementation before editing; resolve conflicts using current code and explicit project instructions. Run Python commands from the repository root so interface.backend imports resolve. Use the existing .venv and root requirements.txt.

## Architecture

- Keep routers in api/, request and response models in schemas/, orchestration in services/, and persistence queries in repositories/. Follow the existing dependency injection and async session patterns.
- The dependency direction is interface.backend to src. Keep src independent of FastAPI and database infrastructure. Imports of src.agents belong in agent_adapter/; backend services may use pure functions from src.tools and src.core.
- Preserve the /api/v1 contract in main.py and coordinate response changes with interface/fontend/lib/api.ts. Validate inputs with the existing Pydantic models and retain actionable error responses.
- Read config.py for settings. Keep credentials out of responses, client code and logs. Use existing configuration instead of hardcoding provider secrets.
- Inspect existing transactions and schema conventions before changing persistence. For schema changes, use the repository's Alembic migration workflow; inspect migrations and avoid applying destructive changes without task authorization.

## Evidence and safety behavior

Interaction severity and safety decisions must remain grounded in database records and rule-based guardrails. LLM text explains evidence and does not determine severity. Preserve source citations, translation metadata, unknown medicines and no-record results. Check the grounding tests when changing the check or explanation pipeline.

## Verification

Select relevant tests in tests/test_api and, for pure core behavior, tests/test_tools. Use .venv/Scripts/python.exe -m pytest with the specific test paths from the repository root; inspect tests/conftest.py for database requirements first. Run the configured Ruff checks on changed Python files when available. Report verified behavior and any missing database or provider setup; do not use live credentials merely to validate unrelated changes.
