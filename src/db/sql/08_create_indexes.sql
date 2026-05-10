            CREATE INDEX IF NOT EXISTS
                idx_sessions_name ON sessions(name);
            CREATE INDEX IF NOT EXISTS
                idx_sessions_exit_reason ON sessions(exit_reason);
            CREATE INDEX IF NOT EXISTS
                idx_actions_session_id ON actions(session_id);
            CREATE INDEX IF NOT EXISTS
                idx_reflections_session_id ON reflections(session_id);
            CREATE INDEX IF NOT EXISTS
                idx_messages_session_id ON messages(session_id);
            CREATE INDEX IF NOT EXISTS
                idx_invites_friend_session_id ON invites(friend_session_id);