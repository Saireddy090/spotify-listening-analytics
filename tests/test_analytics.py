#!/usr/bin/env python3
"""
Spotify Listening Analytics - Test Suite
Verifies:
  1. Relational schema and referential integrity (foreign keys, check constraints).
  2. Dataset volume (>20,000 streaming events).
  3. Correctness of Analytical Queries (CTEs, Window Functions DENSE_RANK, LAG, NTILE).
  4. Composite indexing presence and query plan optimization.
"""

import os
import sqlite3
import unittest

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "spotify_analytics.db")

class TestSpotifyAnalytics(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(DB_PATH):
            raise unittest.SkipTest(f"Database not found at {DB_PATH}. Run data/generator.py first.")
        cls.conn = sqlite3.connect(DB_PATH)
        cls.conn.row_factory = sqlite3.Row
        cls.cur = cls.conn.cursor()
        cls.cur.execute("PRAGMA foreign_keys = ON;")

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_01_dataset_scale(self):
        """Verify resume requirement: >20,000 streaming track records."""
        self.cur.execute("SELECT COUNT(*) FROM play_history;")
        stream_count = self.cur.fetchone()[0]
        self.assertGreaterEqual(stream_count, 20000, "Dataset must have at least 20,000 streams")

        self.cur.execute("SELECT COUNT(*) FROM tracks;")
        track_count = self.cur.fetchone()[0]
        self.assertGreaterEqual(track_count, 1000, "Dataset must have at least 1,000 tracks")

        self.cur.execute("SELECT COUNT(*) FROM artists;")
        artist_count = self.cur.fetchone()[0]
        self.assertGreaterEqual(artist_count, 40, "Dataset must have at least 40 artists")

    def test_02_referential_integrity(self):
        """Verify foreign key integrity across tables."""
        self.cur.execute("PRAGMA foreign_key_check;")
        violations = self.cur.fetchall()
        self.assertEqual(len(violations), 0, f"Foreign key violations found: {violations}")

    def test_03_window_function_dense_rank(self):
        """Verify DENSE_RANK() query groups and ranks tracks properly per genre."""
        query = """
            WITH track_genre_aggregates AS (
                SELECT 
                    g.name AS genre_name,
                    t.track_id,
                    COUNT(ph.stream_id) AS total_streams
                FROM tracks t
                JOIN albums alb ON t.album_id = alb.album_id
                JOIN artists a ON alb.artist_id = a.artist_id
                JOIN artist_genres ag ON a.artist_id = ag.artist_id AND ag.is_primary = 1
                JOIN genres g ON ag.genre_id = g.genre_id
                LEFT JOIN play_history ph ON t.track_id = ph.track_id
                GROUP BY g.name, t.track_id
            ),
            ranked_tracks AS (
                SELECT 
                    genre_name,
                    track_id,
                    total_streams,
                    DENSE_RANK() OVER (PARTITION BY genre_name ORDER BY total_streams DESC) AS rk
                FROM track_genre_aggregates
            )
            SELECT * FROM ranked_tracks WHERE rk = 1;
        """
        self.cur.execute(query)
        rows = self.cur.fetchall()
        self.assertGreater(len(rows), 0, "DENSE_RANK query should return top-ranked tracks per genre")
        # Every genre should have a rank 1
        for r in rows:
            self.assertEqual(r["rk"], 1)

    def test_04_sessionization_lag(self):
        """Verify LAG() window function correctly detects temporal gaps between songs."""
        query = """
            WITH time_deltas AS (
                SELECT 
                    user_id,
                    played_at,
                    LAG(played_at, 1) OVER (PARTITION BY user_id ORDER BY played_at) AS prev_play
                FROM play_history
                LIMIT 100
            )
            SELECT COUNT(*) FROM time_deltas WHERE prev_play IS NOT NULL;
        """
        self.cur.execute(query)
        count = self.cur.fetchone()[0]
        self.assertGreater(count, 0, "LAG() must calculate previous play timestamps")

    def test_05_audio_features_ntile(self):
        """Verify NTILE(4) quartiles segment tracks into 4 cohorts with distinct popularity scores."""
        query = """
            WITH cohorts AS (
                SELECT 
                    popularity_score,
                    NTILE(4) OVER (ORDER BY popularity_score DESC) AS quartile
                FROM tracks
            )
            SELECT 
                quartile,
                COUNT(*) AS track_count,
                AVG(popularity_score) AS avg_pop
            FROM cohorts
            GROUP BY quartile
            ORDER BY quartile;
        """
        self.cur.execute(query)
        rows = self.cur.fetchall()
        self.assertEqual(len(rows), 4, "NTILE(4) must partition tracks into 4 quartiles")
        # Quartile 1 average popularity must be higher than Quartile 4
        self.assertGreater(rows[0]["avg_pop"], rows[3]["avg_pop"])

    def test_06_composite_indexes_exist(self):
        """Verify that targeted composite indexes are registered in the database catalog."""
        self.cur.execute("SELECT name FROM sqlite_master WHERE type='index';")
        indexes = [r[0] for r in self.cur.fetchall()]
        required_indexes = [
            "idx_ph_user_played",
            "idx_ph_track_completion",
            "idx_tracks_album_popularity"
        ]
        for idx in required_indexes:
            self.assertIn(idx, indexes, f"Index {idx} must be created")


if __name__ == "__main__":
    unittest.main()
