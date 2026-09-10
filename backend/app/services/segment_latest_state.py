"""Redis-backed latest state for road segments."""

import json
from datetime import datetime
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
        def epoch(value):
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() if value else 0
        payload["_observed_epoch"] = epoch(state.get("observed_at"))
        payload["_processed_epoch"] = epoch(state.get("processed_at") or state.get("calculated_at"))
        serialized = json.dumps(payload, default=str)
        if hasattr(self.redis, "eval"):
            # Compare-and-set is atomic even when worker retries finish out of order.
            result = self.redis.eval("""
                local old = redis.call('GET', KEYS[1])
                local incoming = cjson.decode(ARGV[2])
                if old then
                    local current = cjson.decode(old)
                    local a = current._observed_epoch or 0
                    local b = incoming._observed_epoch or 0
                    if a > b or (a == b and (current._processed_epoch or 0) > (incoming._processed_epoch or 0)) then
                        return old
                    end
                end
                redis.call('SETEX', KEYS[1], ARGV[1], ARGV[2])
                return ARGV[2]
            """, 1, self.key_for(segment_id), self.ttl_seconds, serialized)
            return json.loads(result)
        current = self.load(segment_id)
        if current and (current.get("_observed_epoch", 0), current.get("_processed_epoch", 0)) > (payload["_observed_epoch"], payload["_processed_epoch"]):
            return current
        self.redis.setex(self.key_for(segment_id), self.ttl_seconds, serialized)
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
