.PHONY: help create_schema run-walkers report

help:
	@echo "Available commands:"
	@echo "  make setup-database    		- Create schema and tables if not exists"
	@echo "  make run-walkers n=3           - Run n consecutive walkers (default: 1)"
	@echo "  make report session_id=          - Generate report for session_id"

setup-database:
	@uv run python -c "import asyncio; from scr.logging_db import setup_database; asyncio.run(setup_database())"

run-walkers:
	@uv run python -c "from scr.llm_functions import run_walkers; run_walkers($(n))"

report:
	@uv run python -c "from scr.logging_db import generate_report; generate_report('$(session_id)')"
