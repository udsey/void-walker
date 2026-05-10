"""DB functions for setup/create/drop."""

import logging

import asyncpg
import psycopg2

from src.setup import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER, SQL_DIR

logger = logging.getLogger(__name__)

DB_CONFIG = {
    "user": DB_USER,
    "password": DB_PASSWORD,
    "database": DB_NAME,
    "host": DB_HOST,
    "port": DB_PORT
}



async def create_database() -> None:
    """Create database if not exists."""
    config = DB_CONFIG.copy()
    config["database"] = "postgres"
    conn = await asyncpg.connect(**config)

    try:
        result = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            DB_NAME
        )
        if not result:
            await conn.execute(f"CREATE DATABASE {DB_NAME}")
            logger.info(f"Database '{DB_NAME}' created.")
        else:
            logger.info(f"Database '{DB_NAME}' already exists.")
    finally:
        await conn.close()


async def create_schema() -> None:
    """Create all tables."""
    conn = await asyncpg.connect(**DB_CONFIG)
    table_files = sorted(SQL_DIR.glob("[0-9]*_create_*.sql"))

    try:
        for filepath in table_files:
            query = filepath.read_text()
            await conn.execute(query)
            table_name = filepath.stem.split("_", 1)[1].replace("create_", "")
            if table_name != "indexes":
                logger.info(f"Table created: {table_name}")
            else:
                logger.info("Indexes created/verified")
        logger.info("All tables created successfully!")
    except Exception as e:
        logger.error(f"Error creating schema: {e}")
        raise
    finally:
        await conn.close()


async def setup_database() -> None:
    """Run the database setup."""
    await create_database()
    await create_schema()
    logger.info("Database setup complete!")


def drop_all_tables() -> None:
    """Drop all tables for db."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    try:
        query = (SQL_DIR / "drop_tables.sql").read_text()
        cur.execute(query)
        conn.commit()
        logger.info("All tables dropped.")
    finally:
        cur.close()
        conn.close()
