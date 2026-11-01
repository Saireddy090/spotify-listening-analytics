#!/usr/bin/env python3
"""
Spotify Listening Analytics - Web Server & REST API
Lightweight embedded server using Python's standard library (zero external dependencies).
Serves the Glassmorphic Spotify Analytics Dashboard and REST API endpoints.
"""

import os
import sys
import json
import time
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PORT = 8085
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(ROOT_DIR, "data", "spotify_analytics.db")

QUERIES_CATALOG = {
    "hourly_patterns": {
        "title": "Hourly Listening Distribution & Dayparts",
        "description": "Aggregates stream volume, active listeners, and skip rates across 24 hours of the day.",
        "sql": """
            WITH hourly_metrics AS (
                SELECT 
                    CAST(strftime('%H', ph.played_at) AS INTEGER) AS hour_of_day,
                    COUNT(ph.stream_id) AS total_streams,
                    COUNT(DISTINCT ph.user_id) AS active_listeners,
                    ROUND(AVG(ph.completion_rate) * 100, 1) AS avg_completion_pct,
                    ROUND(SUM(ph.duration_played_ms) / 3600000.0, 1) AS total_hours
                FROM play_history ph
                GROUP BY hour_of_day
            )
            SELECT 
                hour_of_day,
                total_streams,
                active_listeners,
                avg_completion_pct,
                total_hours,
                CASE 
                    WHEN hour_of_day BETWEEN 6 AND 10 THEN 'Morning Commute'
                    WHEN hour_of_day BETWEEN 12 AND 14 THEN 'Lunch Peak'
                    WHEN hour_of_day BETWEEN 18 AND 22 THEN 'Evening Prime'
                    ELSE 'Off-Peak'
                END AS daypart
            FROM hourly_metrics
            ORDER BY hour_of_day ASC;
        """
    },
    "dense_rank_genres": {
        "title": "Top 3 Tracks Per Genre (DENSE_RANK)",
        "description": "Ranks the most-streamed tracks within each musical genre using DENSE_RANK() partitioning.",
        "sql": """
            WITH track_genre_aggregates AS (
                SELECT 
                    g.name AS genre_name,
                    a.name AS artist_name,
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
            ranked AS (
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
            SELECT genre_name, rank_in_genre, artist_name, track_title, popularity_score, total_streams, avg_completion_pct
            FROM ranked
            WHERE rank_in_genre <= 3
            ORDER BY genre_name, rank_in_genre;
        """
    },
    "sessionization_lag": {
        "title": "Listening Sessionization via LAG()",
        "description": "Calculates temporal gaps between consecutive songs per user to detect session boundaries (gap > 30m).",
        "sql": """
            WITH track_deltas AS (
                SELECT 
                    ph.stream_id,
                    ph.user_id,
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
                    played_at,
                    duration_played_ms,
                    CASE 
                        WHEN prev_played_at IS NULL THEN 1
                        WHEN (julianday(played_at) - julianday(prev_played_at)) * 1440.0 > 30.0 THEN 1
                        ELSE 0 
                    END AS is_new_session
                FROM track_deltas
            ),
            clustered AS (
                SELECT 
                    user_id,
                    duration_played_ms,
                    played_at,
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
                COUNT(*) AS tracks_in_session,
                MIN(played_at) AS session_start,
                MAX(played_at) AS session_end,
                ROUND(SUM(duration_played_ms) / 60000.0, 1) AS session_duration_minutes
            FROM clustered
            GROUP BY user_id, session_id
            HAVING tracks_in_session >= 4
            ORDER BY session_duration_minutes DESC
            LIMIT 25;
        """
    },
    "cumulative_market_share": {
        "title": "Artist Cumulative Market Share (UNBOUNDED PRECEDING)",
        "description": "Measures each artist's streaming volume and running cumulative share within their primary genre.",
        "sql": """
            WITH artist_streams AS (
                SELECT 
                    g.name AS genre_name,
                    a.name AS artist_name,
                    a.monthly_listeners,
                    COUNT(ph.stream_id) AS streams
                FROM artists a
                JOIN artist_genres ag ON a.artist_id = ag.artist_id AND ag.is_primary = 1
                JOIN genres g ON ag.genre_id = g.genre_id
                JOIN albums alb ON a.artist_id = alb.artist_id
                JOIN tracks t ON alb.album_id = t.album_id
                LEFT JOIN play_history ph ON t.track_id = ph.track_id
                GROUP BY g.name, a.name, a.monthly_listeners
            ),
            totals AS (
                SELECT 
                    genre_name,
                    artist_name,
                    monthly_listeners,
                    streams,
                    ROUND((streams * 100.0) / NULLIF(SUM(streams) OVER (PARTITION BY genre_name), 0), 2) AS share_pct
                FROM artist_streams
            )
            SELECT 
                genre_name,
                artist_name,
                streams,
                share_pct,
                ROUND(SUM(share_pct) OVER (
                    PARTITION BY genre_name 
                    ORDER BY streams DESC 
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ), 2) AS cumulative_share_pct
            FROM totals
            ORDER BY genre_name, streams DESC;
        """
    },
    "audio_feature_quartiles": {
        "title": "Audio Feature Correlations via NTILE(4) Quartiles",
        "description": "Correlates danceability, energy, and tempo across 4 popularity quartiles from Hits to Niche tracks.",
        "sql": """
            WITH track_quartiles AS (
                SELECT 
                    track_id,
                    title,
                    popularity_score,
                    tempo_bpm,
                    energy,
                    danceability,
                    valence,
                    NTILE(4) OVER (ORDER BY popularity_score DESC) AS quartile
                FROM tracks
            )
            SELECT 
                tq.quartile,
                CASE tq.quartile
                    WHEN 1 THEN 'Q1: Top Tier Hits'
                    WHEN 2 THEN 'Q2: High Rotation'
                    WHEN 3 THEN 'Q3: Mid Catalog'
                    WHEN 4 THEN 'Q4: Long Tail / Niche'
                END AS quartile_label,
                COUNT(DISTINCT tq.track_id) AS total_tracks,
                ROUND(AVG(tq.popularity_score), 1) AS avg_popularity,
                ROUND(AVG(tq.danceability), 3) AS avg_danceability,
                ROUND(AVG(tq.energy), 3) AS avg_energy,
                ROUND(AVG(tq.tempo_bpm), 1) AS avg_tempo_bpm,
                ROUND(AVG(tq.valence), 3) AS avg_valence,
                COUNT(ph.stream_id) AS total_streams
            FROM track_quartiles tq
            LEFT JOIN play_history ph ON tq.track_id = ph.track_id
            GROUP BY tq.quartile
            ORDER BY tq.quartile;
        """
    },
    "cross_genre_affinity": {
        "title": "Cross-Genre Listener Affinity Matrix",
        "description": "Surfaces co-listening trends by finding multi-genre listening overlap for the same users.",
        "sql": """
            WITH user_genres AS (
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
                ROUND(COUNT(g1.user_id) * 100.0 / (SELECT COUNT(DISTINCT user_id) FROM users), 1) AS pct_of_listeners
            FROM user_genres g1
            JOIN user_genres g2 ON g1.user_id = g2.user_id AND g1.genre_name < g2.genre_name
            GROUP BY g1.genre_name, g2.genre_name
            HAVING co_listening_users >= 45
            ORDER BY co_listening_users DESC
            LIMIT 20;
        """
    },
    "skip_rate_dynamics": {
        "title": "Track Skip Rate Dynamics vs Acoustic Energy",
        "description": "Compares songs with high skip rates (<0.30 completion) vs sticky songs (>0.85 completion).",
        "sql": """
            WITH track_skips AS (
                SELECT 
                    t.track_id,
                    t.title,
                    t.danceability,
                    t.energy,
                    t.tempo_bpm,
                    COUNT(ph.stream_id) AS stream_count,
                    ROUND(SUM(CASE WHEN ph.skipped = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(ph.stream_id), 1) AS skip_pct,
                    ROUND(AVG(ph.completion_rate) * 100, 1) AS avg_completion_pct
                FROM tracks t
                JOIN play_history ph ON t.track_id = ph.track_id
                GROUP BY t.track_id, t.title, t.danceability, t.energy, t.tempo_bpm
                HAVING stream_count >= 10
            )
            SELECT 
                CASE 
                    WHEN skip_pct >= 25.0 THEN 'High Skip (>25% Skipped)'
                    WHEN avg_completion_pct >= 80.0 THEN 'High Completion (>80% Sticky)'
                    ELSE 'Moderate Rotation'
                END AS listener_behavior,
                COUNT(*) AS track_count,
                ROUND(AVG(danceability), 3) AS avg_danceability,
                ROUND(AVG(energy), 3) AS avg_energy,
                ROUND(AVG(tempo_bpm), 1) AS avg_tempo_bpm,
                ROUND(AVG(skip_pct), 1) AS avg_skip_pct,
                ROUND(AVG(avg_completion_pct), 1) AS avg_completion_pct
            FROM track_skips
            GROUP BY listener_behavior
            ORDER BY avg_completion_pct DESC;
        """
    }
}


class AnalyticsHandler(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            index_path = os.path.join(BASE_DIR, "index.html")
            if os.path.exists(index_path):
                with open(index_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "index.html not found")
            return

        if path == "/api/kpis":
            self.handle_kpis()
        elif path == "/api/hourly":
            self.handle_hourly()
        elif path == "/api/leaderboard":
            self.handle_leaderboard()
        elif path == "/api/audio-features":
            self.handle_audio_features()
        elif path == "/api/queries":
            queries_meta = [{
                "key": k,
                "title": v["title"],
                "description": v["description"],
                "sql": v["sql"].strip()
            } for k, v in QUERIES_CATALOG.items()]
            self.send_json(queries_meta)
        elif path == "/api/benchmark":
            self.handle_benchmark_results()
        else:
            self.send_error(404, "Endpoint not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/run-query":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(post_data)
                query_sql = payload.get("sql", "")
                if not query_sql and "key" in payload:
                    key = payload["key"]
                    if key in QUERIES_CATALOG:
                        query_sql = QUERIES_CATALOG[key]["sql"]
                if not query_sql:
                    self.send_json({"error": "No SQL query provided"}, status=400)
                    return

                # Prevent destructive SQL
                clean_sql = query_sql.strip()
                forbidden = ["DROP", "DELETE", "ALTER", "TRUNCATE", "UPDATE", "INSERT"]
                first_word = clean_sql.split()[0].upper()
                if first_word in forbidden:
                    self.send_json({"error": "Read-only analytics mode: data modification queries are disabled."}, status=403)
                    return

                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()

                t0 = time.perf_counter()
                cur.execute(clean_sql)
                rows = cur.fetchall()
                t1 = time.perf_counter()
                elapsed_ms = round((t1 - t0) * 1000.0, 2)

                col_names = [description[0] for description in cur.description] if cur.description else []
                data = [dict(r) for r in rows[:150]] # Limit return to 150 rows for snappy UI

                # Also grab EXPLAIN plan
                try:
                    cur.execute(f"EXPLAIN QUERY PLAN {clean_sql}")
                    plan_rows = [p[3] for p in cur.fetchall()]
                except Exception:
                    plan_rows = ["Plan unavailable"]

                conn.close()
                self.send_json({
                    "columns": col_names,
                    "rows": data,
                    "total_rows": len(rows),
                    "elapsed_ms": elapsed_ms,
                    "plan": plan_rows
                })
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)

    def handle_kpis(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    COUNT(ph.stream_id) AS total_streams,
                    ROUND(SUM(ph.duration_played_ms) / 3600000.0, 1) AS total_hours,
                    COUNT(DISTINCT ph.user_id) AS active_users,
                    COUNT(DISTINCT ph.track_id) AS unique_tracks,
                    ROUND(AVG(ph.completion_rate) * 100, 1) AS avg_completion_pct,
                    ROUND(SUM(CASE WHEN ph.skipped = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(ph.stream_id), 1) AS skip_rate_pct
                FROM play_history ph;
            """)
            r = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM artists;")
            artist_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM genres;")
            genre_count = cur.fetchone()[0]
            conn.close()

            self.send_json({
                "total_streams": r[0],
                "total_hours": r[1],
                "active_users": r[2],
                "unique_tracks": r[3],
                "avg_completion_pct": r[4],
                "skip_rate_pct": r[5],
                "total_artists": artist_count,
                "total_genres": genre_count
            })
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def handle_hourly(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    CAST(strftime('%H', played_at) AS INTEGER) AS hr,
                    COUNT(stream_id) AS streams
                FROM play_history
                GROUP BY hr
                ORDER BY hr ASC;
            """)
            rows = [{"hour": r[0], "streams": r[1]} for r in cur.fetchall()]
            conn.close()
            self.send_json(rows)
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def handle_leaderboard(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    a.artist_id,
                    a.name,
                    a.country,
                    g.name AS primary_genre,
                    ROUND(a.monthly_listeners / 1000000.0, 1) AS listeners_m,
                    COUNT(ph.stream_id) AS total_streams
                FROM artists a
                JOIN artist_genres ag ON a.artist_id = ag.artist_id AND ag.is_primary = 1
                JOIN genres g ON ag.genre_id = g.genre_id
                JOIN albums alb ON a.artist_id = alb.artist_id
                JOIN tracks t ON alb.album_id = t.album_id
                LEFT JOIN play_history ph ON t.track_id = ph.track_id
                GROUP BY a.artist_id, a.name, a.country, g.name, a.monthly_listeners
                ORDER BY total_streams DESC
                LIMIT 10;
            """)
            rows = [{
                "id": r[0],
                "name": r[1],
                "country": r[2],
                "genre": r[3],
                "listeners_m": r[4],
                "streams": r[5]
            } for r in cur.fetchall()]
            conn.close()
            self.send_json(rows)
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def handle_audio_features(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    g.name AS genre,
                    ROUND(AVG(t.danceability), 3) AS danceability,
                    ROUND(AVG(t.energy), 3) AS energy,
                    ROUND(AVG(t.valence), 3) AS valence,
                    ROUND(AVG(t.tempo_bpm), 1) AS tempo
                FROM genres g
                JOIN artist_genres ag ON g.genre_id = ag.genre_id AND ag.is_primary = 1
                JOIN artists a ON ag.artist_id = a.artist_id
                JOIN albums alb ON a.artist_id = alb.artist_id
                JOIN tracks t ON alb.album_id = t.album_id
                GROUP BY g.name
                ORDER BY COUNT(t.track_id) DESC
                LIMIT 8;
            """)
            rows = [{
                "genre": r[0],
                "danceability": r[1],
                "energy": r[2],
                "valence": r[3],
                "tempo": r[4]
            } for r in cur.fetchall()]
            conn.close()
            self.send_json(rows)
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def handle_benchmark_results(self):
        # Read the latest generated benchmark results or run a quick pass
        report_file = os.path.join(ROOT_DIR, "benchmark", "benchmark_report.md")
        if os.path.exists(report_file):
            with open(report_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.send_json({"report_markdown": content})
        else:
            self.send_json({"report_markdown": "Benchmark report not yet generated."})


def run_server():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, AnalyticsHandler)
    print(f" Spotify Listening Analytics Dashboard running at http://localhost:{PORT}")
    print(f" Database connected: {DB_PATH}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
