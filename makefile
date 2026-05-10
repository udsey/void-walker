.PHONY: help setup-db drop-db recreate-db run-walkers report dashboard docker-up docker-down docker-down-volumes docker-run-walkers docker-logs docker-logs-db docker-logs-walker docker-logs-dashboard
n ?= 1

help:
	@echo ""
	@echo "  setup-db                    		create schema and tables if not exists"
	@echo "  drop-db                     		drop all tables"
	@echo "  recreate-db                 		drop and recreate all tables"
	@echo "  run-walkers n=3 parallel=True   	run n walkers, sequential by default, parallel if parallel=True"
	@echo "  report session_id=<id>      		generate report for a session"
	@echo "  dashboard                   		start the dash dashboard"
	@echo "  docker-up                   		build and start all containers"
	@echo "  docker-down                 		stop all containers"
	@echo "  docker-down-volumes         		stop all containers and remove volumes"
	@echo "  docker-run-walkers n=3 parallel=True	run walkers in docker"
	@echo ""

setup-db:
	@uv run python -c "import asyncio; from src.db.db import setup_database; asyncio.run(setup_database())"

drop-db:
	@uv run python -c "from src.db.db import drop_all_tables; drop_all_tables()"

recreate-db: drop-db setup-db

report:
	@uv run python -c "from src.db.utils import generate_report; generate_report('$(session_id)')"

run-walkers:
	@uv run python -c "from src.walker.run import run_walkers; run_walkers($(n), $(parallel))"

dashboard:
	@uv run python -c "from dashboard.app import app; app.run(debug=False, host="0.0.0.0")"

docker-up:
	@docker compose up --build -d

docker-down:
	@docker compose down

docker-down-volumes:
	@docker compose down -v

docker-run-walkers:
	@docker compose run --rm -e WALKERS_N=$(n) -e WALKERS_PARALLEL=$(parallel) walker uv run python -c "import os; from src.walker.run import run_walkers; run_walkers(int(os.getenv('WALKERS_N', 1)), os.getenv('WALKERS_PARALLEL', 'false').lower() == 'true')"

docker-logs:
	@docker compose logs -f

docker-logs-db:
	@docker compose logs -f db

docker-logs-walker:
	@docker compose logs -f walker

docker-logs-dashboard:
	@docker compose logs -f dashboard