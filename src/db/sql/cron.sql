CREATE EXTENSION IF NOT EXISTS pg_cron;

SELECT cron.schedule('0 0 * * *', $$
    DELETE FROM sessions WHERE session_id IN (
        SELECT session_id FROM (
            SELECT session_id, COUNT(*) as cnt,
                   SUM(COUNT(*)) OVER (ORDER BY MAX(created_at) ASC) as running_total
            FROM actions
            GROUP BY session_id
        ) sub
        WHERE running_total <= (SELECT COUNT(*) - __ACTIONS_LIMIT__ FROM actions)
    );
$$);