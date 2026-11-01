#!/usr/bin/env bash
set -e

# ==============================================================================
# Spotify Listening Analytics: Unified Runner Script
# Usage:
#   ./run.sh              -> Run tests, execute benchmarks, and start web dashboard
#   ./run.sh --generate   -> Regenerate 25,000+ realistic stream records
#   ./run.sh --benchmark  -> Run query profiling and EXPLAIN benchmark
#   ./run.sh --test       -> Run unit test assertions
#   ./run.sh --server     -> Start web dashboard only
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

DB_FILE="data/spotify_analytics.db"

case "$1" in
  --generate)
    echo " Regenerating Spotify dataset (25,000+ streams)..."
    python3 data/generator.py --streams 25000 --sqlite "$DB_FILE" --sql-dump data/seed_data.sql
    ;;
  --test)
    echo " Running Unit Test Suite..."
    python3 -m unittest tests/test_analytics.py
    ;;
  --benchmark)
    echo " Running Query Execution & Composite Indexing Benchmark..."
    python3 benchmark/benchmark_engine.py --db "$DB_FILE" --runs 25
    ;;
  --server)
    echo " Starting Spotify Analytics Web Dashboard..."
    python3 web/server.py
    ;;
  *)
    # Default pipeline
    if [ ! -f "$DB_FILE" ]; then
      echo " Initializing Spotify dataset (25,000+ streams)..."
      python3 data/generator.py --streams 25000 --sqlite "$DB_FILE" --sql-dump data/seed_data.sql
    fi

    echo " Running Unit Test Suite..."
    python3 -m unittest tests/test_analytics.py

    echo " Running Performance Profiler & Benchmark Engine..."
    python3 benchmark/benchmark_engine.py --db "$DB_FILE" --runs 20

    echo " Starting Spotify Analytics Dashboard on http://localhost:8085..."
    python3 web/server.py
    ;;
esac
