-- ==============================================================================
-- Spotify Listening Analytics: Module 1
-- Listening Patterns, Sessionization, and User Retention
-- Concepts: Multi-table joins, CTEs, Window functions (LAG, LEAD, SUM OVER)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1.1 Hourly Listening Distribution & Peak Traffic Analysis
-- Surfaces peak listening hours, total stream volume, active listeners, and
-- average track completion rate across hours of the day.
-- ------------------------------------------------------------------------------
WITH hourly_metrics AS (
    SELECT 
        CAST(strftime('%H', ph.played_at) AS INTEGER) AS hour_of_day,
        COUNT(ph.stream_id) AS total_streams,
        COUNT(DISTINCT ph.user_id) AS active_listeners,
        ROUND(AVG(ph.completion_rate) * 100, 2) AS avg_completion_pct,
        ROUND(SUM(ph.duration_played_ms) / 3600000.0, 2) AS total_listening_hours,
        SUM(CASE WHEN ph.skipped = 1 THEN 1 ELSE 0 END) AS skipped_streams
    FROM play_history ph
    GROUP BY hour_of_day
)
SELECT 
    hour_of_day,
    total_streams,
    active_listeners,
    avg_completion_pct,
    total_listening_hours,
    ROUND((skipped_streams * 100.0) / total_streams, 2) AS skip_rate_pct,
    CASE 
        WHEN hour_of_day BETWEEN 6 AND 10 THEN 'Morning Commute'
        WHEN hour_of_day BETWEEN 12 AND 14 THEN 'Lunch Peak'
        WHEN hour_of_day BETWEEN 18 AND 22 THEN 'Evening Prime'
        ELSE 'Off-Peak / Night'
    END AS daypart_category
FROM hourly_metrics
ORDER BY total_streams DESC;


-- ------------------------------------------------------------------------------
-- 1.2 Listening Sessionization using LAG() Window Function
-- Identifies distinct listening sessions by calculating idle gaps between
-- consecutive tracks for each user. A gap > 30 minutes denotes a new session.
-- ------------------------------------------------------------------------------
WITH track_time_deltas AS (
    SELECT 
        ph.stream_id,
        ph.user_id,
        ph.track_id,
        ph.played_at,
        ph.duration_played_ms,
        LAG(ph.played_at, 1) OVER (
            PARTITION BY ph.user_id 
            ORDER BY ph.played_at
        ) AS prev_played_at
    FROM play_history ph
),
session_markers AS (
    SELECT 
        stream_id,
        user_id,
        track_id,
        played_at,
        duration_played_ms,
        -- Calculate gap in minutes from previous song
        CASE 
            WHEN prev_played_at IS NULL THEN 1
            -- SQLite julianday delta in minutes (for MySQL: TIMESTAMPDIFF(MINUTE, prev_played_at, played_at))
            WHEN (julianday(played_at) - julianday(prev_played_at)) * 1440.0 > 30.0 THEN 1
            ELSE 0 
        END AS is_new_session
    FROM track_time_deltas
),
session_clustered AS (
    SELECT 
        stream_id,
        user_id,
        track_id,
        played_at,
        duration_played_ms,
        SUM(is_new_session) OVER (
            PARTITION BY user_id 
            ORDER BY played_at 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS session_id
    FROM session_markers
)
SELECT 
    user_id,
    session_id,
    COUNT(stream_id) AS tracks_in_session,
    MIN(played_at) AS session_start,
    MAX(played_at) AS session_end,
    ROUND(SUM(duration_played_ms) / 60000.0, 2) AS total_session_minutes
FROM session_clustered
GROUP BY user_id, session_id
HAVING tracks_in_session >= 3
ORDER BY total_session_minutes DESC
LIMIT 20;


-- ------------------------------------------------------------------------------
-- 1.3 Subscription Tier Engagement & Retention Profile
-- Evaluates listener engagement, average listening time, and device preferences
-- partitioned by Free vs Premium vs Student vs Family subscriptions.
-- ------------------------------------------------------------------------------
SELECT 
    u.subscription_tier,
    COUNT(DISTINCT u.user_id) AS total_registered_users,
    COUNT(ph.stream_id) AS total_streams_logged,
    ROUND(COUNT(ph.stream_id) * 1.0 / COUNT(DISTINCT u.user_id), 1) AS streams_per_user,
    ROUND(AVG(ph.duration_played_ms) / 1000.0, 1) AS avg_duration_sec,
    ROUND(AVG(ph.completion_rate) * 100, 2) AS avg_completion_pct,
    ROUND(SUM(CASE WHEN ph.device_type = 'Smartphone' THEN 1 ELSE 0 END) * 100.0 / COUNT(ph.stream_id), 2) AS smartphone_share_pct
FROM users u
LEFT JOIN play_history ph ON u.user_id = ph.user_id
GROUP BY u.subscription_tier
ORDER BY total_streams_logged DESC;
