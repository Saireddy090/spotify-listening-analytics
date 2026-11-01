-- ==============================================================================
-- Spotify Listening Analytics: Module 5
-- Targeted Composite Indexing Strategy
-- Objective: Eliminate Full Table Scans, remove disk filesorts, and reduce query
--            execution time by >30% on high-cardinality streaming logs.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- Index 1: Composite Index on play_history (user_id, played_at)
-- Rationale:
--   - High Cardinality: user_id (650 users) + played_at (timestamps).
--   - Query Pattern: WHERE user_id = ? AND played_at >= ? ORDER BY played_at DESC
--   - Benefit: Serves equality filter on user_id, followed by B-Tree range scan
--     on played_at in sorted order. Completely eliminates filesort overhead!
-- ------------------------------------------------------------------------------
CREATE INDEX idx_ph_user_played ON play_history (user_id, played_at);

-- ------------------------------------------------------------------------------
-- Index 2: Composite Index on play_history (track_id, completion_rate, played_at)
-- Rationale:
--   - Query Pattern: Aggregate plays and skip rate per track over a date window.
--   - Benefit: Functions as a "Covering Index" for track-level streaming queries.
--     The database engine satisfies the count, filter, and aggregation directly
--     from the index B-tree leaves without touching disk table pages.
-- ------------------------------------------------------------------------------
CREATE INDEX idx_ph_track_completion ON play_history (track_id, completion_rate, played_at);

-- ------------------------------------------------------------------------------
-- Index 3: Composite Index on tracks (album_id, popularity_score)
-- Rationale:
--   - Query Pattern: JOIN tracks ON albums.album_id = tracks.album_id
--                    ORDER BY popularity_score DESC
--   - Benefit: Speeds up album-to-track joins while reading popularity scores
--     in pre-sorted B-tree index order.
-- ------------------------------------------------------------------------------
CREATE INDEX idx_tracks_album_popularity ON tracks (album_id, popularity_score);

-- ------------------------------------------------------------------------------
-- Index 4: Date Range Index on play_history (played_at)
-- Rationale:
--   - Query Pattern: Global hourly distribution, daily active users, rolling trends.
--   - Benefit: Fast index range scans for time-series window queries.
-- ------------------------------------------------------------------------------
CREATE INDEX idx_ph_played_at ON play_history (played_at);

-- ------------------------------------------------------------------------------
-- Index 5: High-cardinality Index on artists (monthly_listeners)
-- Rationale:
--   - Query Pattern: ORDER BY monthly_listeners DESC LIMIT N
--   - Benefit: Direct backward index scan for top-tier artist leaderboards.
-- ------------------------------------------------------------------------------
CREATE INDEX idx_artists_listeners ON artists (monthly_listeners);
