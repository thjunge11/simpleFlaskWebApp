"""
One-off migration script: copies cached AI game info from Redis into the
`game_ai_info` table in PostgreSQL.

The app used to cache Claude-fetched game info in Redis under keys like
`game_info:<game_id>` -> JSON string with fields:
    description, metacritic_score, avg_playtime_hours, fetched_at

This script reads all such keys from Redis and upserts them into the
`game_ai_info` table (game_id, description, metacritic_score,
avg_playtime_hours, fetched_at), which the app now reads from directly.

Requires the `redis` and `psycopg2-binary` packages:
    pip install redis psycopg2-binary

Usage:
    python migrate_redis_to_postgres.py [--dry-run]

Configuration is read from environment variables (matching the app's .env):
    REDIS_HOST, REDIS_PORT
    DB_HOST, DB_NAME, DB_USER, DB_PASS
"""
import argparse
import json
import os
import sys
from datetime import datetime

import psycopg2
import redis as redis_lib

REDIS_KEY_PREFIX = "game_info:"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS game_ai_info (
    game_id bigint PRIMARY KEY REFERENCES games(game_id) ON UPDATE CASCADE ON DELETE CASCADE,
    description text,
    metacritic_score smallint,
    avg_playtime_hours numeric,
    fetched_at timestamp without time zone
);
"""

UPSERT_SQL = """
INSERT INTO game_ai_info (game_id, description, metacritic_score, avg_playtime_hours, fetched_at)
VALUES (%(game_id)s, %(description)s, %(metacritic_score)s, %(avg_playtime_hours)s, %(fetched_at)s)
ON CONFLICT (game_id) DO UPDATE SET
    description = EXCLUDED.description,
    metacritic_score = EXCLUDED.metacritic_score,
    avg_playtime_hours = EXCLUDED.avg_playtime_hours,
    fetched_at = EXCLUDED.fetched_at;
"""


def parse_fetched_at(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                         help="Read from Redis and print what would be migrated, without writing to Postgres.")
    args = parser.parse_args()

    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS")

    if not args.dry_run and not all([db_host, db_name, db_user, db_pass]):
        sys.exit("DB_HOST, DB_NAME, DB_USER and DB_PASS must be set (see utils/.env.example).")

    print(f"Connecting to Redis at {redis_host}:{redis_port} ...")
    r = redis_lib.Redis(host=redis_host, port=redis_port, decode_responses=True)
    try:
        r.ping()
    except redis_lib.exceptions.ConnectionError as e:
        sys.exit(f"Could not connect to Redis: {e}")

    conn = None
    if not args.dry_run:
        print(f"Connecting to PostgreSQL at {db_host}/{db_name} ...")
        conn = psycopg2.connect(host=db_host, dbname=db_name, user=db_user, password=db_pass)
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
        conn.commit()

    migrated = 0
    skipped = 0

    try:
        for key in r.scan_iter(match=f"{REDIS_KEY_PREFIX}*"):
            game_id_str = key[len(REDIS_KEY_PREFIX):]
            try:
                game_id = int(game_id_str)
            except ValueError:
                print(f"Skipping key with non-numeric game_id: {key}")
                skipped += 1
                continue

            raw = r.get(key)
            if not raw:
                skipped += 1
                continue

            try:
                info = json.loads(raw)
            except json.JSONDecodeError:
                print(f"Skipping key with invalid JSON: {key}")
                skipped += 1
                continue

            row = {
                "game_id": game_id,
                "description": info.get("description"),
                "metacritic_score": info.get("metacritic_score"),
                "avg_playtime_hours": info.get("avg_playtime_hours"),
                "fetched_at": parse_fetched_at(info.get("fetched_at")),
            }

            if args.dry_run:
                print(f"Would migrate game_id={game_id}: {row}")
            else:
                with conn.cursor() as cur:
                    cur.execute(UPSERT_SQL, row)
            migrated += 1
    finally:
        if conn:
            if not args.dry_run:
                conn.commit()
            conn.close()

    action = "Would migrate" if args.dry_run else "Migrated"
    print(f"{action} {migrated} game info record(s). Skipped {skipped}.")


if __name__ == "__main__":
    main()
