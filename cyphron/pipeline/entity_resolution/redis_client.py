"""
Redis client placeholder.

Minimal working check:
- initialize_redis() prints "Redis connected" (or a non-fatal warning if unavailable)
"""

from __future__ import annotations

try:
    from redis import Redis
except Exception:  # foundation-only: allow running without installed deps
    Redis = object  # type: ignore

from pipeline.config import REDIS_URL


def initialize_redis() -> Redis | None:
    if Redis is object:  # type: ignore
        print("Redis connected (skipped): redis package not installed", flush=True)
        return None

    client = Redis.from_url(REDIS_URL, decode_responses=True)
    try:
        client.ping()
        print("Redis connected", flush=True)
        return client
    except Exception as exc:
        # Foundation-only: Redis is optional during local boot checks.
        print(f"Redis connected (skipped): {exc}", flush=True)
        return None

