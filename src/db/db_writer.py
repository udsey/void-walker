"""DatabaseWriter class."""

import logging

import psycopg2
from psycopg2.extras import execute_values

from src.db.db import DB_CONFIG
from src.models import AgentState

logger = logging.getLogger(__name__)


class DatabaseWriter:
    """DatabaseWriter class."""

    def __init__(self) -> None:
        """Init method."""

        self.conn = None
        self.buffer = {key: [] for key in ["actions", "reflections",
                                           "messages", "invites",
                                           "feedback", "persona"]}

    def add(self, event_name: str, event: dict) -> None:
        """Add an event to buffer."""

        self.buffer[event_name].append(event)

    def init_pool(self) -> None:
        """Initialize database connection"""

        self.conn = psycopg2.connect(**DB_CONFIG)

    def flush(self, final_state: AgentState) -> None:
        """Write everything to DB in a single transaction"""

        if self.conn is None:
            message = "Database not initialized. Call init_pool() first."
            raise RuntimeError(message)

        cur = self.conn.cursor()
        session_id = final_state.session_id
        try:

            # Insert session record
            cur.execute("""
                INSERT INTO sessions
                        (session_id, parent_session_id, start_time, end_time,
                        model_name, model_temperature,
                        name, system_prompt, mood,
                        initial_url, current_url, is_friend, total_actions,
                        total_invited, exit_reason, summary)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s)
            """, (final_state.session_id, final_state.parent_session_id,
                  final_state.start_time, final_state.end_time,
                  final_state.model_name, final_state.model_temperature,
                  final_state.name, final_state.system_prompt,
                  final_state.mood, final_state.initial_url,
                  final_state.current_url, final_state.is_friend,
                  len(final_state.actions), len(final_state.invited_friends),
                  final_state.exit_reason, final_state.summary))

            # Insert persona record

            if self.buffer["persona"]:
                p = self.buffer["persona"][0]
                cur.execute("""
                    INSERT INTO personas (
                            session_id, timestamp, name, age, generation,
                            gender, country, mother_language, second_languages,
                            archetype, archetype_description, social_tendency,
                            attention_span, mood, is_friend, system_prompt)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                             %s, %s, %s, %s, %s)
                """, (session_id,
                      p['timestamp'],
                      p['name'],
                      p['age'],
                      p['generation'],
                      p['gender'],
                      p['country'],
                      p['mother_language'],
                      p['second_languages'],
                      p['archetype'],
                      p['archetype_description'],
                      p['social_tendency'],
                      p['attention_span'],
                      p['mood'],
                      p['is_friend'],
                      p['system_prompt']))

            # Batch insert actions - convert dicts to tuples

            if self.buffer["actions"]:
                actions_data = [(
                    session_id, d['name'], d['timestamp'], d['llm_prompt'],
                    d['llm_answer'], d['llm_reason'], d['function_result']
                ) for d in self.buffer["actions"]]
                execute_values(cur, """
                    INSERT INTO actions (
                               session_id, name, timestamp, llm_prompt,
                               llm_answer, llm_reason, function_result)
                    VALUES %s
                """, actions_data)

            # Batch insert reflections

            if self.buffer["reflections"]:
                reflections_data = [(
                    session_id, d['timestamp'], d['action_name'],
                    d['mood_before'], d['mood_after'], d['reflection']
                ) for d in self.buffer["reflections"]]
                execute_values(cur, """
                    INSERT INTO reflections (
                               session_id, timestamp, action_name,
                               mood_before, mood_after, reflection)
                    VALUES %s
                """, reflections_data)

            # Batch insert messages

            if self.buffer["messages"]:
                messages_data = [(
                    session_id, d['timestamp'], d['message'], d['reply_to'],
                    d['is_sent'], d['last_read_messages']
                ) for d in self.buffer["messages"]]
                execute_values(cur, """
                    INSERT INTO messages (
                               session_id, timestamp, message, reply_to,
                               is_sent, last_read_messages)
                    VALUES %s
                """, messages_data)
            # Batch insert invites

            if self.buffer["invites"]:
                invites_data = [(
                    session_id, d['timestamp'], d['name'], d['friends_name'],
                    d['common_language'], d['shared_url'], d['message'],
                    d['friend_session_id']
                ) for d in self.buffer["invites"]]
                execute_values(cur, """
                    INSERT INTO invites (
                               session_id, timestamp, name, friends_name,
                               common_language, shared_url, message,
                               friend_session_id)
                    VALUES %s
                """, invites_data)

            # Batch insert feedback

            if self.buffer["feedback"]:
                feedback_data = [(
                    session_id, d['timestamp'], d['feedback_text']
                ) for d in self.buffer["feedback"]]
                execute_values(cur, """
                    INSERT INTO feedback (session_id, timestamp, feedback_text)
                    VALUES %s
                """, feedback_data)

            self.conn.commit()

            # Clear buffer after successful write

            self.buffer = {k: [] for k in self.buffer}
            logger.info(f"Session {session_id} saved to DB")

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to save session {session_id}: {e}")
            raise e
        finally:
            cur.close()
