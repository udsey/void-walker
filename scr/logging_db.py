import asyncio
import inspect
from typing import Any
import asyncpg
from asyncpg import Connection
import logging
import psycopg2
from scr.models import AgentState
from scr.setup import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER
from scr.db_schemas import *
from psycopg2.extras import execute_values


logger = logging.getLogger(__name__)

DB_CONFIG = {
    "user": DB_USER,
    "password": DB_PASSWORD,
    "database": DB_NAME,
    "host": DB_HOST,
    "port": DB_PORT
}

logger.info(DB_CONFIG)



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

    try:
        for table in [sessions, actions, feedback, reflections, invites, messages]:
            await conn.execute(table)
            table_name = table.split(' (')[0].split()[-1]
            logger.info(f"Table created: {table_name}")
        
        await conn.execute(create_indexes)
        logger.info("Indexes created/verified")
        logger.info("All tables created successfully!")
        
    except Exception as e:
        logger.error(f"Error creating schema: {e}")
        raise
    finally:
        await conn.close()
    

async def setup_database() -> None:
    """Run the database setup"""
    await create_database()
    await create_schema()
    logger.info("Database setup complete!")



class DatabaseWriter:

    def __init__(self, session_id: str):
        self.conn = None
        self.session_id = session_id
        self.buffer = {
            "actions": [],
            "reflections": [],
            "messages": [],
            "invites": [],
            "feedback": []
        }
    
    def add(self, event_name: str, event: dict) -> None:
        """Add an event to buffer. Event dict should NOT contain session_id."""
        event_with_session = {"session_id": self.session_id, **event}
        self.buffer[event_name].append(event_with_session)

    def init_pool(self) -> None:
        """Initialize database connection"""
        self.conn = psycopg2.connect(**DB_CONFIG)

    def flush(self, final_state: AgentState) -> None:
        """Write everything to DB in a single transaction"""
        if self.conn is None:
            raise RuntimeError("Database not initialized. Call init_pool() first.")
        
        cur = self.conn.cursor()
        try:
            # Insert session record
            cur.execute("""
                INSERT INTO sessions (session_id, start_time, end_time, name, persona, 
                                    current_url, is_friend, total_actions, total_invited, 
                                    exit_reason, summary)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (self.session_id, final_state.start_time, final_state.end_time,
                final_state.name, final_state.system_prompt, final_state.current_url,
                final_state.is_friend, len(final_state.actions), 
                len(final_state.invited_friends), final_state.exit_reason, final_state.summary))
            
            # Batch insert actions - convert dicts to tuples
            if self.buffer["actions"]:
                actions_data = [(
                    d['session_id'], d['name'], d['timestamp'], d['llm_prompt'],
                    d['llm_answer'], d['llm_reason'], d['function_result']
                ) for d in self.buffer["actions"]]
                execute_values(cur, """
                    INSERT INTO actions (session_id, name, timestamp, llm_prompt, 
                                        llm_answer, llm_reason, function_result)
                    VALUES %s
                """, actions_data)
            
            # Batch insert reflections
            if self.buffer["reflections"]:
                reflections_data = [(
                    d['session_id'], d['timestamp'], d['action_name'],
                    d['mood_before'], d['mood_after'], d['reflection']
                ) for d in self.buffer["reflections"]]
                execute_values(cur, """
                    INSERT INTO reflections (session_id, timestamp, action_name, 
                                            mood_before, mood_after, reflection)
                    VALUES %s
                """, reflections_data)
            
            # Batch insert messages
            if self.buffer["messages"]:
                messages_data = [(
                    d['session_id'], d['timestamp'], d['message'], d['reply_to'],
                    True, d['last_read_messages']  # is_sent always True
                ) for d in self.buffer["messages"]]
                execute_values(cur, """
                    INSERT INTO messages (session_id, timestamp, message, reply_to, 
                                        is_sent, last_read_messages)
                    VALUES %s
                """, messages_data)
            
            # Batch insert invites
            if self.buffer["invites"]:
                invites_data = [(
                    d['session_id'], d['timestamp'], d['name'], d['friends_name'],
                    d['common_language'], d['shared_url'], d['message'], d['friend_session_id']
                ) for d in self.buffer["invites"]]
                execute_values(cur, """
                    INSERT INTO invites (session_id, timestamp, name, friends_name,
                                        common_language, shared_url, message, friend_session_id)
                    VALUES %s
                """, invites_data)
            
            # Batch insert feedback
            if self.buffer["feedback"]:
                feedback_data = [(
                    d['session_id'], d['timestamp'], d['feedback_text']
                ) for d in self.buffer["feedback"]]
                execute_values(cur, """
                    INSERT INTO feedback (session_id, timestamp, feedback_text)
                    VALUES %s
                """, feedback_data)
            
            self.conn.commit()
            
            # Clear buffer after successful write
            self.buffer = {k: [] for k in self.buffer}
            logger.info(f"Session {self.session_id} saved to DB")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to save session {self.session_id}: {e}")
            raise e
        finally:
            cur.close()