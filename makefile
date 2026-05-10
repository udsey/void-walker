.PHONY: help setup-db drop-db recreate-db run-walkers report dashboard

n ?= 1

help:
	@echo ""
	@echo "  setup-db                    		create schema and tables if not exists"
	@echo "  drop-db                     		drop all tables"
	@echo "  recreate-db                 		drop and recreate all tables"
	@echo "  run-walkers n=3 parallel=True   	run n walkers, sequential by default, parallel if parallel=True"
	@echo "  report session_id=<id>      		generate report for a session"
	@echo "  dashboard                   		start the dash dashboard"
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
	@uv run python -c "from dashboard.app import app; app.run(debug=False)"