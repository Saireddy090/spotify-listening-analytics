-- ==============================================================================
-- Spotify Listening Analytics: Module 2
-- Artist & Genre Rankings, Market Share, and Affinity Trends
-- Concepts: DENSE_RANK(), RANK(), Cumulative Window Framing, CTE Self-Joins
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 2.1 Top 3 Tracks Ranked Per Genre (DENSE_RANK Partitioning)
-- Evaluates streaming volume per track and ranks the top tracks within each
-- musical genre, handling ties gracefully with DENSE_RANK().
-- ------------------------------------------------------------------------------
WITH track_genre_aggregates AS (
    SELECT 
        g.name AS genre_name,
        a.name AS artist_name,
        t.track_id,
        t.title AS track_title,
        t.popularity_score,
        COUNT(ph.stream_id) AS total_streams,
        ROUND(AVG(ph.completion_rate) * 100, 1) AS avg_completion_pct
    FROM tracks t
    JOIN albums alb ON t.album_id = alb.album_id
    JOIN artists a ON alb.artist_id = a.artist_id
    JOIN artist_genres ag ON a.artist_id = ag.artist_id AND ag.is_primary = 1
    JOIN genres g ON ag.genre_id = g.genre_id
    LEFT JOIN play_history ph ON t.track_id = ph.track_id
    GROUP BY g.name, a.name, t.track_id, t.title, t.popularity_score
),
ranked_genre_tracks AS (
    SELECT 
        genre_name,
        artist_name,
        track_title,
        popularity_score,
        total_streams,
        avg_completion_pct,
        DENSE_RANK() OVER (
            PARTITION BY genre_name 
            ORDER BY total_streams DESC, popularity_score DESC
        ) AS rank_in_genre
    FROM track_genre_aggregates
)
SELECT 
    genre_name,
    rank_in_genre,
    artist_name,
    track_title,
    popularity_score,
    total_streams,
    avg_completion_pct
FROM ranked_genre_tracks
WHERE rank_in_genre <= 3
ORDER BY genre_name, rank_in_genre;


-- ------------------------------------------------------------------------------
-- 2.2 Artist Streaming Market Share & Cumulative Genre Dominance
-- Computes each artist's stream share within their genre, plus cumulative
-- genre share using window frame UNBOUNDED PRECEDING.
-- ------------------------------------------------------------------------------
WITH artist_genre_streams AS (
    SELECT 
        g.name AS genre_name,
        a.artist_id,
        a.name AS artist_name,
        a.monthly_listeners,
        COUNT(ph.stream_id) AS artist_genre_streams
    FROM artists a
    JOIN artist_genres ag ON a.artist_id = ag.artist_id AND ag.is_primary = 1
    JOIN genres g ON ag.genre_id = g.genre_id
    JOIN albums alb ON a.artist_id = alb.artist_id
    JOIN tracks t ON alb.album_id = t.album_id
    LEFT JOIN play_history ph ON t.track_id = ph.track_id
    GROUP BY g.name, a.artist_id, a.name, a.monthly_listeners
),
genre_totals AS (
    SELECT 
        genre_name,
        artist_id,
        artist_name,
        monthly_listeners,
        artist_genre_streams,
        SUM(artist_genre_streams) OVER (PARTITION BY genre_name) AS total_genre_streams,
        ROUND((artist_genre_streams * 100.0) / NULLIF(SUM(artist_genre_streams) OVER (PARTITION BY genre_name), 0), 2) AS stream_share_pct
    FROM artist_genre_streams
)
SELECT 
    genre_name,
    artist_name,
    artist_genre_streams,
    total_genre_streams,
    stream_share_pct,
    ROUND(SUM(stream_share_pct) OVER (
        PARTITION BY genre_name 
        ORDER BY artist_genre_streams DESC 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ), 2) AS cumulative_genre_share_pct
FROM genre_totals
ORDER BY genre_name, artist_genre_streams DESC;


-- ------------------------------------------------------------------------------
-- 2.3 Cross-Genre Listener Affinity Matrix
-- Identifies listeners who bridge genres by finding co-occurrences of streams
-- between distinct genres for the same user within our 25,000+ stream dataset.
-- ------------------------------------------------------------------------------
WITH user_genre_activity AS (
    SELECT DISTINCT
        ph.user_id,
        g.name AS genre_name
    FROM play_history ph
    JOIN tracks t ON ph.track_id = t.track_id
    JOIN albums alb ON t.album_id = alb.album_id
    JOIN artist_genres ag ON alb.artist_id = ag.artist_id AND ag.is_primary = 1
    JOIN genres g ON ag.genre_id = g.genre_id
)
SELECT 
    g1.genre_name AS primary_genre,
    g2.genre_name AS affinity_genre,
    COUNT(g1.user_id) AS co_listening_users,
    ROUND(COUNT(g1.user_id) * 100.0 / (SELECT COUNT(DISTINCT user_id) FROM users), 2) AS pct_of_userbase
FROM user_genre_activity g1
JOIN user_genre_activity g2 
  ON g1.user_id = g2.user_id 
 AND g1.genre_name < g2.genre_name -- Eliminate reflexive pairs & duplicate reversals
GROUP BY g1.genre_name, g2.genre_name
HAVING co_listening_users >= 50
ORDER BY co_listening_users DESC
LIMIT 15;
