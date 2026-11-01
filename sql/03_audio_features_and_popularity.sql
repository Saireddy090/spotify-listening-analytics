-- ==============================================================================
-- Spotify Listening Analytics: Module 3
-- Audio Feature Correlations, Popularity Quartiles, and Skip Dynamics
-- Concepts: NTILE(4), Correlated Subqueries, Acoustic Profiling, Skip Metrics
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 3.1 Audio Feature Profiling Across Popularity Quartiles (NTILE(4))
-- Segments tracks into 4 popularity quartiles (Q1: Global Hits to Q4: Niche)
-- and correlates acoustic properties (danceability, energy, tempo, valence).
-- ------------------------------------------------------------------------------
WITH track_quartiles AS (
    SELECT 
        track_id,
        title,
        popularity_score,
        tempo_bpm,
        energy,
        danceability,
        loudness_db,
        valence,
        NTILE(4) OVER (ORDER BY popularity_score DESC) AS popularity_quartile
    FROM tracks
),
quartile_stream_metrics AS (
    SELECT 
        tq.popularity_quartile,
        COUNT(DISTINCT tq.track_id) AS tracks_in_cohort,
        ROUND(AVG(tq.popularity_score), 1) AS avg_popularity,
        ROUND(AVG(tq.danceability), 3) AS avg_danceability,
        ROUND(AVG(tq.energy), 3) AS avg_energy,
        ROUND(AVG(tq.tempo_bpm), 1) AS avg_tempo_bpm,
        ROUND(AVG(tq.valence), 3) AS avg_musical_positivity,
        COUNT(ph.stream_id) AS total_streams_logged,
        ROUND(AVG(ph.completion_rate) * 100, 1) AS avg_completion_pct
    FROM track_quartiles tq
    LEFT JOIN play_history ph ON tq.track_id = ph.track_id
    GROUP BY tq.popularity_quartile
)
SELECT 
    popularity_quartile,
    CASE popularity_quartile
        WHEN 1 THEN 'Top Tier (Hits & Virals)'
        WHEN 2 THEN 'High Rotation'
        WHEN 3 THEN 'Mid Catalog'
        WHEN 4 THEN 'Long Tail / Niche'
    END AS tier_label,
    tracks_in_cohort,
    avg_popularity,
    avg_danceability,
    avg_energy,
    avg_tempo_bpm,
    avg_musical_positivity,
    total_streams_logged,
    avg_completion_pct
FROM quartile_stream_metrics
ORDER BY popularity_quartile;


-- ------------------------------------------------------------------------------
-- 3.2 High-Skip vs High-Completion Audio Characteristics
-- Analyzes tracks with >25% skip rate vs tracks with >80% completion rate to
-- surface what musical attributes keep listeners engaged.
-- ------------------------------------------------------------------------------
WITH track_skip_stats AS (
    SELECT 
        t.track_id,
        t.title,
        t.danceability,
        t.energy,
        t.tempo_bpm,
        t.valence,
        COUNT(ph.stream_id) AS stream_count,
        SUM(CASE WHEN ph.skipped = 1 THEN 1 ELSE 0 END) AS skip_count,
        ROUND(SUM(CASE WHEN ph.skipped = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(ph.stream_id), 2) AS skip_rate_pct,
        ROUND(AVG(ph.completion_rate) * 100, 2) AS avg_completion_pct
    FROM tracks t
    JOIN play_history ph ON t.track_id = ph.track_id
    GROUP BY t.track_id, t.title, t.danceability, t.energy, t.tempo_bpm, t.valence
    HAVING stream_count >= 10
)
SELECT 
    CASE 
        WHEN skip_rate_pct >= 25.0 THEN 'High Skip (Unfavorable)'
        WHEN avg_completion_pct >= 80.0 THEN 'High Completion (Sticky)'
        ELSE 'Neutral Rotation'
    END AS cohort,
    COUNT(track_id) AS track_count,
    ROUND(AVG(danceability), 3) AS avg_danceability,
    ROUND(AVG(energy), 3) AS avg_energy,
    ROUND(AVG(tempo_bpm), 1) AS avg_tempo_bpm,
    ROUND(AVG(valence), 3) AS avg_valence,
    ROUND(AVG(skip_rate_pct), 1) AS cohort_avg_skip_pct,
    ROUND(AVG(avg_completion_pct), 1) AS cohort_avg_completion_pct
FROM track_skip_stats
GROUP BY cohort
ORDER BY cohort_avg_completion_pct DESC;


-- ------------------------------------------------------------------------------
-- 3.3 "One-Hit Wonder" Index: Top Track Dominance vs Catalog Median
-- Calculates whether an artist's streaming volume is concentrated in a single
-- viral track or distributed evenly across their studio albums.
-- ------------------------------------------------------------------------------
WITH artist_track_streams AS (
    SELECT 
        a.artist_id,
        a.name AS artist_name,
        t.track_id,
        t.title AS track_title,
        COUNT(ph.stream_id) AS track_streams,
        ROW_NUMBER() OVER (
            PARTITION BY a.artist_id 
            ORDER BY COUNT(ph.stream_id) DESC
        ) AS track_rank_in_artist,
        SUM(COUNT(ph.stream_id)) OVER (
            PARTITION BY a.artist_id
        ) AS total_artist_streams
    FROM artists a
    JOIN albums alb ON a.artist_id = alb.artist_id
    JOIN tracks t ON alb.album_id = t.album_id
    LEFT JOIN play_history ph ON t.track_id = ph.track_id
    GROUP BY a.artist_id, a.name, t.track_id, t.title
)
SELECT 
    artist_name,
    track_title AS top_streamed_track,
    track_streams AS top_track_streams,
    total_artist_streams,
    ROUND((track_streams * 100.0) / NULLIF(total_artist_streams, 0), 2) AS top_track_share_pct,
    CASE 
        WHEN (track_streams * 100.0) / NULLIF(total_artist_streams, 0) > 40.0 THEN 'High Concentration (One-Track Heavy)'
        WHEN (track_streams * 100.0) / NULLIF(total_artist_streams, 0) BETWEEN 20.0 AND 40.0 THEN 'Moderate Balance'
        ELSE 'Well-Distributed Catalog'
    END AS catalog_distribution_profile
FROM artist_track_streams
WHERE track_rank_in_artist = 1 AND total_artist_streams >= 100
ORDER BY top_track_share_pct DESC
LIMIT 15;
