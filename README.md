# PolyMerge: AI-Powered Polypill Formulation

An AI decision-support system using Graph Neural Networks to predict drug interactions and optimize safe fixed-dose combinations.

## Architecture

Decoupled monorepo:

- `backend/`: Fastify & Prisma API handling routing, auth/query logging, and hard-coded safety fallback rules.
- `ml_engine/`: PyTorch & PyTorch Geometric models served via FastAPI.
- Neo4j: Knowledge Graph storing Hetionet and DrugBank data (containerized).
- MySQL: relational store for `backend/` user/query-log schemas (containerized).

## Quick Start

```bash
# 1. Copy env template and start Neo4j + MySQL
cp .env.example .env
docker-compose up -d

# 2. Backend
cd backend
npm install
set -a; . ../.env; set +a
npx prisma migrate dev --name init   # creates User/QueryLog tables in MySQL
npm run dev                          # http://localhost:3000/health

# 3. ML engine (separate terminal)
cd ml_engine
python3 -m pip install -r requirements.txt
python3 -m uvicorn main:app --reload --port 8000   # http://localhost:8000/health
```

Or, with `make`:

```bash
make up && make install
make backend   # terminal 1
make ml        # terminal 2
```

## Verifying the setup

- `curl http://localhost:3000/health` -> `{"status":"ok","service":"polymerge-backend"}`
- `curl http://localhost:8000/health` -> `{"status":"ok","service":"polymerge-ml-engine"}`
- `curl -X POST http://localhost:3000/api/combinations/search -H "Content-Type: application/json" -d '{"diseases":["hypertension"]}'` -> proxies to the ML engine and applies the hard-coded contraindication check.

## Notes

- `main.py`'s `/predict/combination` is a stub (Sprint 1 goal: connectivity before AI). Real GNN scoring + set-cover search land in Sprints 2-3 per `ROADMAP.md`.
- `backend/src/rules/contraindications.js` enforces absolute contraindications (e.g. MAOI + SSRI) independent of any model score -- extend this list before adding new drug classes.
- This is a formulation-screening decision-support tool for researchers, not an autonomous prescribing system.
