from enum import Enum
import time
from typing import Any, Callable


class ReservationStatus(str, Enum):
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    FULL = "full"


RESERVE_SCRIPT = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])
if redis.call('GET', KEYS[2]) then
    return 2
end
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[3]) then
    return 3
end
local reserved = redis.call('SET', KEYS[2], ARGV[5], 'EX', ARGV[6], 'NX')
if not reserved then
    return 2
end
redis.call('ZADD', KEYS[1], ARGV[2], ARGV[4])
return 1
"""

RELEASE_SCRIPT = """
if redis.call('GET', KEYS[2]) == ARGV[1] then
    redis.call('DEL', KEYS[2])
    redis.call('ZREM', KEYS[1], ARGV[2])
    return 1
end
return 0
"""

DEPTH_SCRIPT = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])
return redis.call('ZCARD', KEYS[1])
"""


class InferenceQueue:
    """Atomic capacity and per-camera reservation tracking for inference."""

    def __init__(
        self,
        redis_client: Any,
        *,
        max_pending: int,
        reservation_ttl_seconds: int,
        clock: Callable[[], float] = time.time,
        key_prefix: str = "inference",
    ):
        self.redis = redis_client
        self.max_pending = max_pending
        self.reservation_ttl_seconds = reservation_ttl_seconds
        self.clock = clock
        self.reservations_key = f"{key_prefix}:reservations"
        self.pending_key_prefix = f"{key_prefix}:pending:"

    def reserve(self, camera_id: str, job_id: str) -> ReservationStatus:
        now = int(self.clock())
        expires_at = now + self.reservation_ttl_seconds
        member = self._member(camera_id, job_id)
        code = self.redis.eval(
            RESERVE_SCRIPT,
            2,
            self.reservations_key,
            self._pending_key(camera_id),
            now,
            expires_at,
            self.max_pending,
            member,
            job_id,
            self.reservation_ttl_seconds,
        )
        return {
            1: ReservationStatus.ACCEPTED,
            2: ReservationStatus.DUPLICATE,
            3: ReservationStatus.FULL,
        }[int(code)]

    def release(self, camera_id: str, job_id: str) -> bool:
        released = self.redis.eval(
            RELEASE_SCRIPT,
            2,
            self.reservations_key,
            self._pending_key(camera_id),
            job_id,
            self._member(camera_id, job_id),
        )
        return bool(released)

    def depth(self) -> int:
        return int(
            self.redis.eval(
                DEPTH_SCRIPT,
                1,
                self.reservations_key,
                int(self.clock()),
            )
        )

    def _pending_key(self, camera_id: str) -> str:
        return f"{self.pending_key_prefix}{camera_id}"

    @staticmethod
    def _member(camera_id: str, job_id: str) -> str:
        return f"{camera_id}:{job_id}"
