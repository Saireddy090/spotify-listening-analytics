-- ==============================================================================
-- Spotify Listening Analytics: Database Schema (SQLite 3.25+)
-- Description: Standard ANSI SQL equivalent for zero-dependency local execution
-- ==============================================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS play_history;
DROP TABLE IF EXISTS tracks;
DROP TABLE IF EXISTS albums;
DROP TABLE IF EXISTS artist_genres;
DROP TABLE IF EXISTS artists;
DROP TABLE IF EXISTS genres;
DROP TABLE IF EXISTS users;

-- 1. Genres Table
CREATE TABLE genres (
    genre_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. Artists Table
CREATE TABLE artists (
    artist_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    monthly_listeners INTEGER NOT NULL DEFAULT 0,
    country TEXT NOT NULL,
    verified INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. Artist Genres Junction
CREATE TABLE artist_genres (
    artist_id INTEGER NOT NULL,
    genre_id INTEGER NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (artist_id, genre_id),
    FOREIGN KEY (artist_id) REFERENCES artists(artist_id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(genre_id) ON DELETE CASCADE
);

-- 4. Albums Table
CREATE TABLE albums (
    album_id INTEGER PRIMARY KEY AUTOINCREMENT,
    artist_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    release_date TEXT NOT NULL,
    album_type TEXT NOT NULL DEFAULT 'album',
    total_tracks INTEGER NOT NULL DEFAULT 1,
    record_label TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (artist_id) REFERENCES artists(artist_id) ON DELETE CASCADE
);

-- 5. Tracks Table with Audio Features
CREATE TABLE tracks (
    track_id INTEGER PRIMARY KEY AUTOINCREMENT,
    album_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    duration_ms INTEGER NOT NULL,
    explicit INTEGER NOT NULL DEFAULT 0,
    tempo_bpm REAL NOT NULL,
    energy REAL NOT NULL,
    danceability REAL NOT NULL,
    loudness_db REAL NOT NULL,
    valence REAL NOT NULL,
    popularity_score INTEGER NOT NULL DEFAULT 50,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (album_id) REFERENCES albums(album_id) ON DELETE CASCADE
);

-- 6. Users Table
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    subscription_tier TEXT NOT NULL DEFAULT 'Free',
    country TEXT NOT NULL,
    joined_date TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 7. Play History Table (20,000+ records)
CREATE TABLE play_history (
    stream_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    track_id INTEGER NOT NULL,
    played_at TEXT NOT NULL,
    duration_played_ms INTEGER NOT NULL,
    completion_rate REAL NOT NULL,
    device_type TEXT NOT NULL,
    shuffle_state INTEGER NOT NULL DEFAULT 0,
    skipped INTEGER GENERATED ALWAYS AS (CASE WHEN completion_rate < 0.300 THEN 1 ELSE 0 END) STORED,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (track_id) REFERENCES tracks(track_id) ON DELETE CASCADE
);
