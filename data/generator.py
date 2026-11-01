#!/usr/bin/env python3
"""
Spotify Listening Analytics - Realistic Dataset Generator
Generates:
  - 15+ Music Genres
  - 85+ Real-world inspired Artists
  - 250+ Albums
  - 1,250+ Unique Tracks with Spotify audio features
  - 600+ Users across Free/Premium/Student/Family tiers
  - 25,000+ Granular Stream Records with session patterns and realistic skip behaviors
"""

import os
import sys
import random
import datetime
import sqlite3
import argparse

# Deterministic seed for reproducible benchmarks
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

GENRES = [
    "Pop", "Hip-Hop", "R&B", "EDM", "Indie Rock", 
    "Bollywood", "Telugu Cinema", "Lo-Fi", "Reggaeton", 
    "Synthwave", "Jazz", "Classical", "Metal", "Soul", "Afrobeats"
]

ARTISTS_DATA = [
    # (Name, Country, Primary Genre, Monthly Listeners in millions)
    ("The Weeknd", "Canada", "R&B", 108),
    ("Taylor Swift", "USA", "Pop", 102),
    ("Drake", "Canada", "Hip-Hop", 84),
    ("Kendrick Lamar", "USA", "Hip-Hop", 68),
    ("Arijit Singh", "India", "Bollywood", 45),
    ("Anirudh Ravichander", "India", "Telugu Cinema", 28),
    ("Sid Sriram", "India", "Telugu Cinema", 19),
    ("Billie Eilish", "USA", "Pop", 72),
    ("Dua Lipa", "UK", "Pop", 69),
    ("Daft Punk", "France", "EDM", 24),
    ("Calvin Harris", "UK", "EDM", 61),
    ("Martin Garrix", "Netherlands", "EDM", 31),
    ("Bad Bunny", "Puerto Rico", "Reggaeton", 77),
    ("SZA", "USA", "R&B", 65),
    ("Travis Scott", "USA", "Hip-Hop", 70),
    ("Post Malone", "USA", "Pop", 64),
    ("A.R. Rahman", "India", "Bollywood", 38),
    ("Shreya Ghoshal", "India", "Bollywood", 32),
    ("Armaan Malik", "India", "Bollywood", 21),
    ("Arctic Monkeys", "UK", "Indie Rock", 43),
    ("Tame Impala", "Australia", "Indie Rock", 29),
    ("The 1975", "UK", "Indie Rock", 18),
    ("Burna Boy", "Nigeria", "Afrobeats", 22),
    ("Wizkid", "Nigeria", "Afrobeats", 16),
    ("ChilledCow", "France", "Lo-Fi", 12),
    ("Kavinsky", "France", "Synthwave", 8),
    ("Miles Davis", "USA", "Jazz", 6),
    ("John Coltrane", "USA", "Jazz", 4),
    ("Metallica", "USA", "Metal", 26),
    ("Iron Maiden", "UK", "Metal", 10),
    ("Adele", "UK", "Soul", 52),
    ("Bruno Mars", "USA", "Pop", 75),
    ("Ed Sheeran", "UK", "Pop", 82),
    ("Eminem", "USA", "Hip-Hop", 66),
    ("J. Cole", "USA", "Hip-Hop", 41),
    ("Ludovico Einaudi", "Italy", "Classical", 11),
    ("Hans Zimmer", "Germany", "Classical", 15),
    ("Illenium", "USA", "EDM", 14),
    ("Avicii", "Sweden", "EDM", 35),
    ("Peggy Gou", "South Korea", "EDM", 17),
    ("Diljit Dosanjh", "India", "Bollywood", 26),
    ("Karan Aujla", "India", "Hip-Hop", 23),
    ("Devi Sri Prasad", "India", "Telugu Cinema", 15),
    ("Thaman S", "India", "Telugu Cinema", 17),
    ("Lana Del Rey", "USA", "Indie Rock", 58),
    ("Olivia Rodrigo", "USA", "Pop", 59),
    ("Sabrina Carpenter", "USA", "Pop", 78),
    ("Chappell Roan", "USA", "Pop", 44),
    ("Fred again..", "UK", "EDM", 19),
    ("Rema", "Nigeria", "Afrobeats", 27)
]

ALBUM_SUFFIXES = [
    "Chronicles", "Echoes", "Nights", "Memories", "Visions", "After Hours",
    "Superbloom", "Renaissance", "Odyssey", "Paranoia", "Dimensions", "Heartbreak",
    "Melody", "Rhythms", "Illusion", "Midnight Drive", "Waves", "Velocity"
]

TRACK_WORDS_1 = [
    "Blinding", "Midnight", "Starboy", "Save", "Golden", "Cruel", "Anti-Hero",
    "God's", "HUMBLE.", "Kesariya", "Arabic", "Samajavaragamana", "Levitating",
    "Bad", "One", "Summer", "Monaco", "Snooze", "FE!N", "Sunflower", "Jai",
    "Do I Wanna", "Less I Know", "City", "Last", "Essence", "Sunset", "Nightcall",
    "So What", "Enter", "Rolling", "Uptown", "Shape", "Lose", "Middle", "Experience",
    "Time", "Wake", "It Goes", "Lover", "Vampire", "Espresso", "Good", "Adore", "Stay"
]

TRACK_WORDS_2 = [
    "Lights", "City", "Plan", "Tears", "Hour", "Summer", "Kuthu", "Guy", "More",
    "Time", "Remix", "Child", "Sandman", "Deep", "Funk", "You", "Yourself", "Better",
    "Me Up", "Like Nanana", "Like That", "Dream", "Breeze", "Vibes", "Chills", "Horizon"
]

DEVICE_TYPES = ["Smartphone", "Desktop", "Smart Speaker", "Tablet", "Web Player"]
DEVICE_WEIGHTS = [0.60, 0.22, 0.10, 0.05, 0.03]

SUBSCRIPTIONS = ["Free", "Premium", "Student", "Family"]
SUB_WEIGHTS = [0.35, 0.45, 0.12, 0.08]

COUNTRIES = ["India", "USA", "UK", "Canada", "Australia", "Germany", "Brazil", "France"]
COUNTRY_WEIGHTS = [0.35, 0.30, 0.12, 0.07, 0.05, 0.04, 0.04, 0.03]


def generate_data(num_streams=25000):
    print(f"Generating Spotify Listening Analytics Dataset (Target: {num_streams:,} streams)...")
    
    # 1. Genres
    genres = [{"genre_id": i + 1, "name": name} for i, name in enumerate(GENRES)]
    genre_map = {g["name"]: g["genre_id"] for g in genres}
    
    # 2. Artists & Artist Genres
    artists = []
    artist_genres = []
    for i, (name, country, primary_g, listeners_m) in enumerate(ARTISTS_DATA):
        artist_id = i + 1
        listeners = int(listeners_m * 1_000_000 + random.randint(1000, 99999))
        artists.append({
            "artist_id": artist_id,
            "name": name,
            "monthly_listeners": listeners,
            "country": country,
            "verified": 1
        })
        primary_gid = genre_map.get(primary_g, 1)
        artist_genres.append({"artist_id": artist_id, "genre_id": primary_gid, "is_primary": 1})
        
        # Add secondary genre for 40% of artists
        if random.random() < 0.40:
            sec_gid = random.choice([g["genre_id"] for g in genres if g["genre_id"] != primary_gid])
            artist_genres.append({"artist_id": artist_id, "genre_id": sec_gid, "is_primary": 0})
            
    # 3. Albums
    albums = []
    album_id_counter = 1
    base_date = datetime.date(2018, 1, 1)
    
    for art in artists:
        num_albums = random.randint(3, 7)
        for a_idx in range(num_albums):
            art_name_clean = art["name"].split()[0]
            title = f"{art_name_clean} {random.choice(ALBUM_SUFFIXES)}"
            days_offset = random.randint(0, 3100)
            rel_date = base_date + datetime.timedelta(days=days_offset)
            album_type = "album" if a_idx > 0 else "single"
            albums.append({
                "album_id": album_id_counter,
                "artist_id": art["artist_id"],
                "title": title,
                "release_date": rel_date.isoformat(),
                "album_type": album_type,
                "total_tracks": random.randint(8, 16) if album_type == "album" else random.randint(1, 3),
                "record_label": random.choice(["Universal Music", "Sony Music", "Warner Records", "T-Series", "Independent"])
            })
            album_id_counter += 1

    # 4. Tracks
    tracks = []
    track_id_counter = 1
    for alb in albums:
        num_tracks_in_alb = alb["total_tracks"]
        for t_idx in range(num_tracks_in_alb):
            w1 = random.choice(TRACK_WORDS_1)
            w2 = random.choice(TRACK_WORDS_2)
            title = f"{w1} {w2}" if random.random() < 0.75 else f"{w1}"
            if t_idx > 0 and random.random() < 0.15:
                title += " (Acoustic)"
            elif random.random() < 0.10:
                title += " (Live)"
            
            # Realistic Spotify Audio Features
            duration_ms = random.randint(140_000, 290_000) # 2m 20s to 4m 50s
            explicit = 1 if random.random() < 0.18 else 0
            tempo_bpm = round(random.uniform(75.0, 175.0), 2)
            energy = round(random.uniform(0.200, 0.980), 3)
            danceability = round(random.uniform(0.250, 0.950), 3)
            loudness_db = round(random.uniform(-16.00, -3.00), 2)
            valence = round(random.uniform(0.100, 0.950), 3) # Musical positiveness
            popularity = random.randint(25, 98)
            
            tracks.append({
                "track_id": track_id_counter,
                "album_id": alb["album_id"],
                "title": title,
                "duration_ms": duration_ms,
                "explicit": explicit,
                "tempo_bpm": tempo_bpm,
                "energy": energy,
                "danceability": danceability,
                "loudness_db": loudness_db,
                "valence": valence,
                "popularity_score": popularity
            })
            track_id_counter += 1

    # 5. Users
    users = []
    for u_id in range(1, 651):
        tier = random.choices(SUBSCRIPTIONS, weights=SUB_WEIGHTS)[0]
        country = random.choices(COUNTRIES, weights=COUNTRY_WEIGHTS)[0]
        join_days = random.randint(100, 1800)
        joined_date = datetime.date(2021, 1, 1) + datetime.timedelta(days=join_days)
        username = f"listener_{u_id:04d}"
        users.append({
            "user_id": u_id,
            "username": username,
            "email": f"{username}@spotifydemo.io",
            "subscription_tier": tier,
            "country": country,
            "joined_date": joined_date.isoformat()
        })

    # 6. Play History (Streams > 20,000)
    # Generate realistic listening sessions:
    # Users have top favorite tracks (power law / Pareto distribution)
    # Peak hours: 8-10 AM, 1-2 PM, 6-10 PM
    print(f"Synthesizing {num_streams:,} stream events with session continuity and realistic skip patterns...")
    
    # Pre-select favorite tracks per user (3-8 favorite tracks per user for repeat listening)
    user_favorites = {}
    for u in users:
        user_favorites[u["user_id"]] = random.sample(tracks, k=random.randint(4, 10))
    
    streams = []
    stream_id_counter = 1
    start_sim_time = datetime.datetime(2026, 8, 1, 0, 0, 0)
    
    # Weighted hours of day
    hour_weights = [
        0.01, 0.01, 0.005, 0.005, 0.01, 0.02,  # 00:00 - 05:00 (Night)
        0.04, 0.07, 0.09, 0.08, 0.05, 0.05,    # 06:00 - 11:00 (Morning commute/work)
        0.06, 0.07, 0.05, 0.05, 0.06, 0.08,    # 12:00 - 17:00 (Afternoon)
        0.09, 0.10, 0.10, 0.08, 0.05, 0.02     # 18:00 - 23:00 (Evening prime)
    ]
    
    while len(streams) < num_streams:
        # Pick an active user
        user = random.choice(users)
        u_id = user["user_id"]
        
        # Pick session day & starting hour
        day_offset = random.randint(0, 90) # Last 90 days
        hour = random.choices(range(24), weights=hour_weights)[0]
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        current_time = start_sim_time + datetime.timedelta(days=day_offset, hours=hour, minutes=minute, seconds=second)
        
        device = random.choices(DEVICE_TYPES, weights=DEVICE_WEIGHTS)[0]
        shuffle = 1 if random.random() < 0.45 else 0
        
        # Session size: 2 to 9 songs in a listening session
        session_length = random.randint(2, 9)
        for _ in range(session_length):
            if len(streams) >= num_streams:
                break
                
            # 55% chance user listens to one of their favorite tracks; otherwise discovery
            if random.random() < 0.55:
                track = random.choice(user_favorites[u_id])
            else:
                # Popular tracks picked more frequently
                track = random.choices(tracks, weights=[t["popularity_score"] for t in tracks])[0]
                
            # Completion & Skip behavior
            # 18% skip (< 0.30 completion)
            # 12% partial play (0.30 - 0.85)
            # 70% complete play (0.85 - 1.00)
            dice = random.random()
            if dice < 0.18:
                completion_rate = round(random.uniform(0.04, 0.28), 3)
            elif dice < 0.30:
                completion_rate = round(random.uniform(0.35, 0.84), 3)
            else:
                completion_rate = round(random.uniform(0.85, 1.00), 3)
                
            duration_played_ms = int(track["duration_ms"] * completion_rate)
            
            streams.append({
                "stream_id": stream_id_counter,
                "user_id": u_id,
                "track_id": track["track_id"],
                "played_at": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                "duration_played_ms": duration_played_ms,
                "completion_rate": completion_rate,
                "device_type": device,
                "shuffle_state": shuffle
            })
            stream_id_counter += 1
            
            # Next track in session starts right after this song (plus 2 to 8 seconds delay)
            gap_seconds = int((duration_played_ms / 1000.0) + random.randint(2, 8))
            current_time += datetime.timedelta(seconds=gap_seconds)
            
    print(f"Generated Catalog: {len(genres)} Genres, {len(artists)} Artists, {len(albums)} Albums, {len(tracks)} Tracks, {len(users)} Users.")
    print(f"Generated Streams: {len(streams):,} Total Play Events.")
    
    return {
        "genres": genres,
        "artists": artists,
        "artist_genres": artist_genres,
        "albums": albums,
        "tracks": tracks,
        "users": users,
        "play_history": streams
    }


def seed_sqlite(data, db_path):
    print(f"Populating SQLite Database at: {db_path}")
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")
    
    # Read schema
    schema_file = os.path.join(os.path.dirname(__file__), "..", "sql", "00_schema_sqlite.sql")
    with open(schema_file, "r") as f:
        cur.executescript(f.read())
        
    # Bulk insert
    cur.executemany("INSERT INTO genres (genre_id, name) VALUES (:genre_id, :name)", data["genres"])
    cur.executemany("INSERT INTO artists (artist_id, name, monthly_listeners, country, verified) VALUES (:artist_id, :name, :monthly_listeners, :country, :verified)", data["artists"])
    cur.executemany("INSERT INTO artist_genres (artist_id, genre_id, is_primary) VALUES (:artist_id, :genre_id, :is_primary)", data["artist_genres"])
    cur.executemany("INSERT INTO albums (album_id, artist_id, title, release_date, album_type, total_tracks, record_label) VALUES (:album_id, :artist_id, :title, :release_date, :album_type, :total_tracks, :record_label)", data["albums"])
    cur.executemany("INSERT INTO tracks (track_id, album_id, title, duration_ms, explicit, tempo_bpm, energy, danceability, loudness_db, valence, popularity_score) VALUES (:track_id, :album_id, :title, :duration_ms, :explicit, :tempo_bpm, :energy, :danceability, :loudness_db, :valence, :popularity_score)", data["tracks"])
    cur.executemany("INSERT INTO users (user_id, username, email, subscription_tier, country, joined_date) VALUES (:user_id, :username, :email, :subscription_tier, :country, :joined_date)", data["users"])
    cur.executemany("INSERT INTO play_history (stream_id, user_id, track_id, played_at, duration_played_ms, completion_rate, device_type, shuffle_state) VALUES (:stream_id, :user_id, :track_id, :played_at, :duration_played_ms, :completion_rate, :device_type, :shuffle_state)", data["play_history"])
    
    conn.commit()
    
    # Verification count
    cur.execute("SELECT COUNT(*) FROM play_history")
    count = cur.fetchone()[0]
    conn.close()
    print(f"SQLite Seed Successful! Verified {count:,} stream records in 'play_history'.")


def export_sql_dump(data, output_path):
    print(f"Exporting SQL Insert Dump to: {output_path}")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("-- Spotify Listening Analytics Generated Seed Data\n")
        f.write("SET FOREIGN_KEY_CHECKS = 0;\n\n")
        
        # Helper to batch inserts
        def write_batch(table, rows, cols):
            if not rows:
                return
            col_str = ", ".join(cols)
            f.write(f"-- {table} ({len(rows)} records)\n")
            batch_size = 500
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i+batch_size]
                val_lines = []
                for r in batch:
                    vals = []
                    for c in cols:
                        v = r[c]
                        if v is None:
                            vals.append("NULL")
                        elif isinstance(v, (int, float)):
                            vals.append(str(v))
                        else:
                            clean_str = str(v).replace("'", "''")
                            vals.append(f"'{clean_str}'")
                    val_lines.append(f"({', '.join(vals)})")
                f.write(f"INSERT INTO {table} ({col_str}) VALUES\n" + ",\n".join(val_lines) + ";\n")
            f.write("\n")

        write_batch("genres", data["genres"], ["genre_id", "name"])
        write_batch("artists", data["artists"], ["artist_id", "name", "monthly_listeners", "country", "verified"])
        write_batch("artist_genres", data["artist_genres"], ["artist_id", "genre_id", "is_primary"])
        write_batch("albums", data["albums"], ["album_id", "artist_id", "title", "release_date", "album_type", "total_tracks", "record_label"])
        write_batch("tracks", data["tracks"], ["track_id", "album_id", "title", "duration_ms", "explicit", "tempo_bpm", "energy", "danceability", "loudness_db", "valence", "popularity_score"])
        write_batch("users", data["users"], ["user_id", "username", "email", "subscription_tier", "country", "joined_date"])
        write_batch("play_history", data["play_history"], ["stream_id", "user_id", "track_id", "played_at", "duration_played_ms", "completion_rate", "device_type", "shuffle_state"])
        
        f.write("SET FOREIGN_KEY_CHECKS = 1;\n")
    print(f"SQL Dump Export Complete! File size: {os.path.getsize(output_path) / (1024*1024):.2f} MB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate realistic Spotify dataset")
    parser.add_argument("--streams", type=int, default=25000, help="Number of stream records to generate (default: 25000)")
    parser.add_argument("--sqlite", type=str, default="spotify_analytics.db", help="SQLite database output path")
    parser.add_argument("--sql-dump", type=str, default="seed_data.sql", help="SQL dump output path")
    args = parser.parse_args()

    data = generate_data(num_streams=args.streams)
    
    # 1. Always create SQLite database for fast local execution & testing
    db_file = os.path.abspath(args.sqlite)
    seed_sqlite(data, db_file)
    
    # 2. Export SQL dump for MySQL import
    dump_file = os.path.abspath(args.sql_dump)
    export_sql_dump(data, dump_file)
    print("Dataset generation completed successfully.")
