-- ==============================================================================
-- Spotify Listening Analytics: Database Schema (MySQL 8.0+)
-- Description: 3NF Relational Schema modeling Artists, Albums, Tracks, Genres,
--              Users, and Streaming Play History (>20,000 records).
-- ==============================================================================

DROP DATABASE IF EXISTS spotify_analytics;
CREATE DATABASE spotify_analytics CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE spotify_analytics;

-- ------------------------------------------------------------------------------
-- 1. Genres Table: Normalized music genres
-- ------------------------------------------------------------------------------
CREATE TABLE genres (
    genre_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(60) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 2. Artists Table: Master directory of recording artists
-- ------------------------------------------------------------------------------
CREATE TABLE artists (
    artist_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    monthly_listeners INT UNSIGNED NOT NULL DEFAULT 0,
    country VARCHAR(60) NOT NULL,
    verified BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 3. Artist Genres Junction: Many-to-many relationship
-- ------------------------------------------------------------------------------
CREATE TABLE artist_genres (
    artist_id INT NOT NULL,
    genre_id INT NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (artist_id, genre_id),
    CONSTRAINT fk_ag_artist FOREIGN KEY (artist_id) REFERENCES artists(artist_id) ON DELETE CASCADE,
    CONSTRAINT fk_ag_genre FOREIGN KEY (genre_id) REFERENCES genres(genre_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 4. Albums Table: Studio albums, singles, and EPs
-- ------------------------------------------------------------------------------
CREATE TABLE albums (
    album_id INT AUTO_INCREMENT PRIMARY KEY,
    artist_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    release_date DATE NOT NULL,
    album_type ENUM('album', 'single', 'ep', 'compilation') NOT NULL DEFAULT 'album',
    total_tracks SMALLINT UNSIGNED NOT NULL DEFAULT 1,
    record_label VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_albums_artist FOREIGN KEY (artist_id) REFERENCES artists(artist_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 5. Tracks Table: Track catalog with high-fidelity Spotify audio features
-- ------------------------------------------------------------------------------
CREATE TABLE tracks (
    track_id INT AUTO_INCREMENT PRIMARY KEY,
    album_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    duration_ms INT UNSIGNED NOT NULL,
    explicit BOOLEAN NOT NULL DEFAULT FALSE,
    tempo_bpm DECIMAL(5, 2) NOT NULL,
    energy DECIMAL(4, 3) NOT NULL,
    danceability DECIMAL(4, 3) NOT NULL,
    loudness_db DECIMAL(5, 2) NOT NULL,
    valence DECIMAL(4, 3) NOT NULL,
    popularity_score TINYINT UNSIGNED NOT NULL DEFAULT 50, -- 0 to 100
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tracks_album FOREIGN KEY (album_id) REFERENCES albums(album_id) ON DELETE CASCADE,
    CONSTRAINT chk_audio_energy CHECK (energy BETWEEN 0.000 AND 1.000),
    CONSTRAINT chk_audio_danceability CHECK (danceability BETWEEN 0.000 AND 1.000),
    CONSTRAINT chk_audio_valence CHECK (valence BETWEEN 0.000 AND 1.000),
    CONSTRAINT chk_popularity CHECK (popularity_score <= 100)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 6. Users Table: Spotify listener accounts across subscription tiers
-- ------------------------------------------------------------------------------
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(150) NOT NULL UNIQUE,
    subscription_tier ENUM('Free', 'Premium', 'Student', 'Family') NOT NULL DEFAULT 'Free',
    country VARCHAR(60) NOT NULL,
    joined_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 7. Play History Table: Granular streaming log (Target: >20,000+ records)
-- ------------------------------------------------------------------------------
CREATE TABLE play_history (
    stream_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    track_id INT NOT NULL,
    played_at DATETIME NOT NULL,
    duration_played_ms INT UNSIGNED NOT NULL,
    completion_rate DECIMAL(4, 3) NOT NULL,
    device_type ENUM('Smartphone', 'Desktop', 'Smart Speaker', 'Tablet', 'Web Player') NOT NULL,
    shuffle_state BOOLEAN NOT NULL DEFAULT FALSE,
    skipped BOOLEAN GENERATED ALWAYS AS (completion_rate < 0.300) STORED,
    CONSTRAINT fk_ph_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_ph_track FOREIGN KEY (track_id) REFERENCES tracks(track_id) ON DELETE CASCADE,
    CONSTRAINT chk_completion CHECK (completion_rate BETWEEN 0.000 AND 1.000)
) ENGINE=InnoDB;
