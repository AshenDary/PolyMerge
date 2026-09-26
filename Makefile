.PHONY: up down install backend ml migrate sprint4-compare sprint4-viz

up: ## Start Neo4j + MySQL containers
	docker-compose up -d

down: ## Stop containers
	docker-compose down

install: ## Install backend + ml_engine dependencies
	cd backend && npm install
	cd ml_engine && python3 -m pip install -r requirements.txt

migrate: ## Apply Prisma schema to MySQL
	cd backend && set -a; . ../.env; set +a; npx prisma migrate dev --name init

backend: ## Run Fastify dev server
	cd backend && npm run dev

ml: ## Run FastAPI dev server
	cd ml_engine && python3 -m uvicorn main:app --reload --port 8000

sprint4-compare: ## Run Sprint 4 model comparison (CV on training data)
	python3 ml_engine/scripts/run_sprint4_model_comparison.py

sprint4-viz: ## Generate Sprint 4 comparison visualizations
	python3 ml_engine/scripts/visualize_model_comparison.py
