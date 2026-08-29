# PolyMerge: AI-Powered Polypill Formulation

An AI decision-support system using Graph Neural Networks to predict drug interactions and optimize safe fixed-dose combinations.

## Architecture

This is a decoupled monorepo containing:

- `backend/`: Fastify & Prisma API handling routing, security, and query logging.
- `ml_engine/`: PyTorch & PyTorch Geometric models served via FastAPI.
- `graph_db/`: Neo4j Knowledge Graph storing Hetionet and DrugBank data.

## Quick Start

1. Run `docker-compose up -d` to start the Neo4j instance.
2. In `/backend`, run `npm install` and `npm run dev`.
3. In `/ml_engine`, run `pip install -r requirements.txt` and `uvicorn main:app --reload`.
