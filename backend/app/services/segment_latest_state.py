"""Redis-backed latest state for road segments."""

import json
from typing import Any


class SegmentLatestStateStore:
    def __init__(self, redis_client: Any, ttl_seconds: int = 3600):
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than zero")
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def key_for(segment_id: str) -> str:
        return f"emission:segment:{segment_id}"

    def save(self, segment_id: str, state: dict) -> dict:
        payload = {"segment_id": segment_id, **state}
        self.redis.setex(self.key_for(segment_id), self.ttl_seconds, json.dumps(payload, default=str))
        return payload

    def load(self, segment_id: str) -> dict | None:
        value = self.redis.get(self.key_for(segment_id))
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        return json.loads(value)

    def load_all(self) -> dict[str, dict]:
        states = {}
        for key in self.redis.scan_iter(match="emission:segment:*"):
            if isinstance(key, bytes):
                key = key.decode("utf-8")
            segment_id = key.removeprefix("emission:segment:")
            state = self.load(segment_id)
            if state is not None:
                states[segment_id] = state
        return states
