from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


CELERY_PRIORITY = {"high": 9, "medium": 5, "low": 1}


def normalize_job_priority(priority: str | None) -> str:
    normalized = (priority or "medium").lower()
    return normalized if normalized in CELERY_PRIORITY else "medium"


@dataclass(frozen=True, slots=True)
class InferenceJob:
    job_id: str
    camera_id: str
    camera_database_id: str
    captured_at: datetime
    enqueued_at: datetime
    priority: str
    sampling_interval_seconds: int | None
    frame_key: str
    frame_size_bytes: int
    frame_acquisition_latency_s: float
    frame_capture_method: str

    @property
    def celery_priority(self) -> int:
        return CELERY_PRIORITY[normalize_job_priority(self.priority)]

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["captured_at"] = self.captured_at.isoformat()
        payload["enqueued_at"] = self.enqueued_at.isoformat()
        payload["priority"] = normalize_job_priority(self.priority)
        return payload

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "InferenceJob":
        return cls(
            job_id=payload["job_id"],
            camera_id=payload["camera_id"],
            camera_database_id=payload["camera_database_id"],
            captured_at=datetime.fromisoformat(payload["captured_at"]),
            enqueued_at=datetime.fromisoformat(payload["enqueued_at"]),
            priority=normalize_job_priority(payload.get("priority")),
            sampling_interval_seconds=payload.get("sampling_interval_seconds"),
            frame_key=payload["frame_key"],
            frame_size_bytes=int(payload["frame_size_bytes"]),
            frame_acquisition_latency_s=float(
                payload["frame_acquisition_latency_s"]
            ),
            frame_capture_method=payload["frame_capture_method"],
        )
