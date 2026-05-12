.PHONY: help setup-db drop-db recreate-db run-walkers report dashboard docker-up docker-down docker-down-volumes docker-run-walkers docker-logs docker-logs-db docker-logs-walker docker-logs-dashboard build-up
.DEFAULT_GOAL := help
n ?= 1
parallel ?= false

help:
	@echo ""
	@echo "-----------------------------------------------"
	@echo " Local Run"
	@echo "-----------------------------------------------"
	@echo ""
	@echo "  make setup-db                               	create schema and tables if not exists"
	@echo "  make drop-db                                	drop all tables"
	@echo "  make recreate-db                            	drop and recreate all tables"
	@echo "  make run-walkers n=3 parallel=false          	run n walkers, sequential by default"
	@echo "  make report session_id=<id>                 	generate report for a session"
	@echo "  make dashboard                              	start the dash dashboard"
	@echo ""
	@echo "-----------------------------------------------"
	@echo " Docker Run"
	@echo "-----------------------------------------------"
	@echo ""
	@echo " ~~~~~~~~~~~~~~~~~~~ Start ~~~~~~~~~~~~~~~~~~~~"
	@echo ""
	@echo "  make docker-up                              	build and start all containers"
	@echo "  make build-up c=dashboard              	re-build and start container"
	@echo ""
	@echo " ~~~~~~~~~~~~~~~~~~ Run ~~~~~~~~~~~~~~~~~~~"
	@echo ""
	@echo "  make docker-run-walkers n=3 parallel=false   	run walkers in docker"
	@echo ""
	@echo " ~~~~~~~~~~~~~~~~~~ Stop ~~~~~~~~~~~~~~~~~~"
	@echo ""
	@echo "  make docker-down                            	stop all containers"
	@echo "  make docker-down-volumes                    	stop all containers and remove volumes"
	@echo ""
	@echo " ~~~~~~~~~~~~~~~~~~ Logs ~~~~~~~~~~~~~~~~~~"
	@echo ""
	@echo "  make docker-health                       	check all containers health"
	@echo "  make docker-logs                            	follow all logs"
	@echo "  make docker-logs-db                         	follow db logs"
	@echo "  make docker-logs-translate                    follow translator logs"
	@echo "  make docker-logs-walker                     	follow walker logs"
	@echo "  make docker-logs-dashboard                  	follow dashboard logs"
	@echo ""

setup-db:
	@uv run python -c "import asyncio; from src.db.db import setup_database; asyncio.run(setup_database())"

drop-db:
	@uv run python -c "from src.db.db import drop_all_tables; drop_all_tables()"

recreate-db: drop-db setup-db

report:
	@uv run python -c "from src.db.utils import generate_report; generate_report('$(session_id)')"

run-walkers:
	@uv run python -c "from src.walker.run import run_walkers; run_walkers($(n), '$(parallel)'.lower() == 'true')"

dashboard:
	@uv run python -c 'from dashboard.app import app; app.run(debug=True, host="0.0.0.0")'

docker-up:
	@docker compose up --build -d

build-up:
	docker compose build --no-cache $(c) && docker compose up -d $(c)

docker-down:
	@docker compose down

docker-down-volumes:
	@docker compose down -v

docker-run-walkers:
	@docker compose run --rm \
		-e WALKERS_N=$(n) \
		-e WALKERS_PARALLEL=$(parallel) \
		walker uv run python -c \
		"import os; from src.walker.run import run_walkers; run_walkers(int(os.getenv('WALKERS_N', 1)), os.getenv('WALKERS_PARALLEL', 'false').lower() == 'true')"

docker-logs:
	@docker compose logs -f

docker-logs-db:
	@docker compose logs -f db

docker-logs-walker:
	@docker compose logs -f walker

docker-logs-dashboard:
	@docker compose logs -f dashboard

docker-logs-translate:
	@docker compose logs -f libretranslate

docker-health:
	@echo "========== Container Status =========="
	@docker compose ps
	@echo ""
	@echo "========== Health Checks =========="
	@docker inspect --format='{{.Name}} → {{.State.Health.Status}}' $$(docker ps -q) 2>/dev/null || echo ""