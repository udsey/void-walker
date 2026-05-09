.PHONY: help create-bd drop-db  recreate-db run-walkers report 

help:
	@echo "Available commands:"
	@echo "  make setup-db    		- Create schema and tables if not exists"
	@echo "  make run-walkers n=3           - Run n consecutive walkers (default: 1)"
	@echo "  make report session_id=          - Generate report for session_id"
	@echo "  make recreate-db          - Drops db and creates new one"

setup-db:
	@uv run python -c "import asyncio; from scr.logging_db import setup_database; asyncio.run(setup_database())"

drop-db:
	@uv run python -c "from scr.logging_db import drop_all_tables; drop_all_tables()"


recreate-db: drop-db setup-db

run-walkers:
	@uv run python -c "from scr.llm_functions import run_walkers; run_walkers($(n))"

report:
	@uv run python -c "from scr.logging_db import generate_report; generate_report('$(session_id)')"
