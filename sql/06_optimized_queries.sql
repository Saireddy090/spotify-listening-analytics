-- ==============================================================================
-- Spotify Listening Analytics: Module 6
-- Optimized Query Implementations
-- Demonstrating execution plan improvements after targeted composite indexing.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- Optimized Query 1: User Timeline & Recent Play History Lookups
-- Utilizing: Composite index `idx_ph_user_played (user_id, played_at)`
-- Improvements:
--   - Replaces Full Table Scan with B-Tree Index Range Scan.
--   - Eliminates temporary filesort since the index natively preserves played_at ordering.
-- ------------------------------------------------------------------------------
SELECT 
    ph.stream_id,
    ph.user_id,
    ph.track_id,
    t.title AS track_title,
    a.name AS artist_name,
    ph.played_at,
    ph.duration_played_ms,
    ph.device_type
FROM play_history ph
JOIN tracks t ON ph.track_id = t.track_id
JOIN albums alb ON t.album_id = alb.album_id
JOIN artists a ON alb.artist_id = a.artist_id
WHERE ph.user_id IN (12, 45, 88, 120, 205, 310, 420)
  AND ph.played_at >= '2026-08-15 00:00:00'
ORDER BY ph.user_id, ph.played_at DESC;


-- ------------------------------------------------------------------------------
-- Optimized Query 2: Track Skip Rate & Completion Aggregation (CTE Pre-aggregation)
-- Utilizing: Covering Composite Index `idx_ph_track_completion (track_id, completion_rate, played_at)`
-- Improvements:
--   - Uses a Common Table Expression to aggregate play_history FIRST, touching only
--     the index tree leaves without reading rows from the main table.
--   - Joins tracks, albums, and artists ONLY for the aggregated resulting tracks,
--     reducing join volume from 25,000 rows to the distinct track count.
-- ------------------------------------------------------------------------------
WITH aggregated_streams AS (
    SELECT 
        track_id,
        COUNT(stream_id) AS total_plays,
        SUM(CASE WHEN completion_rate >= 0.85 THEN 1 ELSE 0 END) AS completed_plays,
        SUM(CASE WHEN completion_rate < 0.30 THEN 1 ELSE 0 END) AS skipped_plays,
        ROUND(AVG(completion_rate) * 100, 2) AS avg_completion_pct
    FROM play_history
    WHERE played_at >= '2026-08-01 00:00:00'
    GROUP BY track_id
    HAVING total_plays >= 15
)
SELECT 
    t.track_id,
    t.title,
    a.name AS artist_name,
    agg.total_plays,
    agg.completed_plays,
    agg.skipped_plays,
    agg.avg_completion_pct
FROM aggregated_streams agg
JOIN tracks t ON agg.track_id = t.track_id
JOIN albums alb ON t.album_id = alb.album_id
JOIN artists a ON alb.artist_id = a.artist_id
ORDER BY agg.total_plays DESC, agg.avg_completion_pct DESC;


-- ------------------------------------------------------------------------------
-- Optimized Query 3: Multi-Table Top Track Ranking
-- Utilizing: Composite index `idx_tracks_album_popularity (album_id, popularity_score)`
-- Improvements:
--   - Index covering both the join key (album_id) and the filter/sort column (popularity_score).
--   - Avoids memory sort buffer allocation.
-- ------------------------------------------------------------------------------
SELECT 
    a.name AS artist_name,
    alb.title AS album_title,
    alb.release_date,
    t.title AS track_title,
    t.popularity_score,
    t.duration_ms,
    t.tempo_bpm
FROM tracks t
JOIN albums alb ON t.album_id = alb.album_id
JOIN artists a ON alb.artist_id = a.artist_id
WHERE alb.release_date >= '2022-01-01'
  AND t.popularity_score >= 60
ORDER BY alb.album_id, t.popularity_score DESC;
