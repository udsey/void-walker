.PHONY: help create_schema

help:
	@echo "Available commands:"
	@echo "  make setup-database    		- Create schema and tables if not exists"


setup-database:
	@uv run python -c "import asyncio; from scr.logging_db import setup_database; asyncio.run(setup_database())"