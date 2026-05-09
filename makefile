.PHONY: help setup-db drop-db recreate-db run-walkers report dashboard

n ?= 1

help:
	@echo ""
	@echo "  setup-db                    create schema and tables if not exists"
	@echo "  drop-db                     drop all tables"
	@echo "  recreate-db                 drop and recreate all tables"
	@echo "  run-walkers n=3             run n consecutive walkers (default: 1)"
	@echo "  report session_id=<id>      generate report for a session"
	@echo "  dashboard                   start the dash dashboard"
	@echo ""

setup-db:
	@uv run python -c "import asyncio; from scr.logging_db import setup_database; asyncio.run(setup_database())"

drop-db:
	@uv run python -c "from scr.logging_db import drop_all_tables; drop_all_tables()"

recreate-db: drop-db setup-db

run-walkers:
	@uv run python -c "from scr.llm_functions import run_walkers; run_walkers($(n))"

report:
	@uv run python -c "from scr.logging_db import generate_report; generate_report('$(session_id)')"

dashboard:
	@uv run python -c "from dashboard.app import app; app.run(debug=False)"