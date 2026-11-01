-- ==============================================================================
-- Spotify Listening Analytics: Module 4
-- Baseline Queries Before Optimization (Unindexed / High-Cost Execution)
-- Used for EXPLAIN profiling and baseline execution time measurements.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- Baseline Query 1: User Timeline & Chronological Play History Lookups
-- Problem: Filtering by high-cardinality user_id and ordering by played_at.
-- Engine behavior without composite index:
--   - Scans entire play_history table or requires a secondary filesort to sort
--     thousands of records by played_at.
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
-- Baseline Query 2: Track Skip Rate & Completion Aggregation
-- Problem: Aggregating 25,000+ stream records across high-cardinality track_id
-- and filtering by completion rate.
-- Engine behavior without index:
--   - Full table scan on play_history (25,000 rows examined).
--   - Temporary hash table or filesort created for GROUP BY.
-- ------------------------------------------------------------------------------
SELECT 
    t.track_id,
    t.title,
    a.name AS artist_name,
    COUNT(ph.stream_id) AS total_plays,
    SUM(CASE WHEN ph.completion_rate >= 0.85 THEN 1 ELSE 0 END) AS completed_plays,
    SUM(CASE WHEN ph.completion_rate < 0.30 THEN 1 ELSE 0 END) AS skipped_plays,
    ROUND(AVG(ph.completion_rate) * 100, 2) AS avg_completion_pct
FROM tracks t
JOIN albums alb ON t.album_id = alb.album_id
JOIN artists a ON alb.artist_id = a.artist_id
JOIN play_history ph ON t.track_id = ph.track_id
WHERE ph.played_at >= '2026-08-01 00:00:00'
GROUP BY t.track_id, t.title, a.name
HAVING total_plays >= 15
ORDER BY total_plays DESC, avg_completion_pct DESC;


-- ------------------------------------------------------------------------------
-- Baseline Query 3: Multi-Table Top Track Ranking by Popularity Score
-- Problem: Filtering tracks by album release date and ranking by popularity_score.
-- Engine behavior without index:
--   - Full scan on tracks table and sort over memory buffer.
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
