"""Deterministic load simulator for the scalable CCTV orchestration pipeline."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json
from queue import Empty, Full, Queue
import random
import statistics
import threading
import time
import tracemalloc

from app.services.camera_scheduler import CameraSchedulingPolicy, plan_due_cameras
from app.services.data_freshness import FreshnessPolicy, FreshnessStatus, classify_freshness
from app.services.emission_aggregation import EmissionObservation, EmissionWindowAggregator
from app.services.inference_batcher import InferenceBatcher
from app.services.latest_emission_state import LatestEmissionStateStore
from cv.emission_factors import calculate_emission


@dataclass(slots=True)
class SimulatedCamera:
    camera_id: str
    database_id: str
    priority: str
    sampling_interval_seconds: int | None = None
    next_sample_at: datetime | None = None
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class SimulatedJob:
    job_id: str
    camera_id: str
    database_id: str
    captured_at: datetime
    enqueued_at: float


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    virtual_duration_seconds: int = 120
    time_scale: float = 0.01
    stream_failure_rate: float = 0.02
    queue_capacity: int = 64
    worker_concurrency: int = 8
    max_batch_size: int = 8
    max_batch_wait_ms: int = 10
    base_batch_latency_ms: float = 12.0
    per_item_latency_ms: float = 1.0
    random_seed: int = 20260821

    def __post_init__(self) -> None:
        if self.virtual_duration_seconds <= 0:
            raise ValueError("virtual_duration_seconds must be greater than zero")
        if self.time_scale < 0:
            raise ValueError("time_scale must not be negative")
        if not 0 <= self.stream_failure_rate <= 1:
            raise ValueError("stream_failure_rate must be between zero and one")
        if self.queue_capacity <= 0 or self.worker_concurrency <= 0:
            raise ValueError("queue and worker limits must be greater than zero")


@dataclass(frozen=True, slots=True)
class SimulationResult:
    camera_count: int
    virtual_duration_seconds: int
    wall_time_seconds: float
    process_cpu_time_seconds: float
    approximate_process_cpu_percent: float
    python_heap_peak_mib: float
    scheduled_samples: int
    successful_jobs: int
    stream_failures: int
    overload_skips: int
    max_queue_depth: int
    mean_queue_wait_ms: float
    p95_queue_wait_ms: float
    mean_batch_size: float
    max_batch_size: int
    mean_batch_inference_ms: float
    inference_throughput_jobs_per_second: float
    latest_state_writes: int
    historical_aggregate_writes: int
    websocket_updates: int
    fresh_cameras: int
    aging_cameras: int
    stale_cameras: int
    unknown_cameras: int


class _MemoryRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def setex(self, key: str, _ttl_seconds: int, value: str) -> None:
        self.values[key] = value

    def get(self, key: str) -> str | None:
        return self.values.get(key)


def _cameras(count: int) -> list[SimulatedCamera]:
    cameras = []
    for index in range(count):
        remainder = index % 10
        priority = "high" if remainder < 2 else "medium" if remainder < 6 else "low"
        cameras.append(
            SimulatedCamera(
                camera_id=f"camera-{index + 1:03d}",
                database_id=f"00000000-0000-0000-0000-{index + 1:012d}",
                priority=priority,
            )
        )
    return cameras


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int((len(ordered) - 1) * fraction))
    return ordered[index]


def run_stage(camera_count: int, config: SimulationConfig) -> SimulationResult:
    if camera_count <= 0:
        raise ValueError("camera_count must be greater than zero")
    if config.virtual_duration_seconds <= 0:
        raise ValueError("virtual_duration_seconds must be greater than zero")

    random_generator = random.Random(config.random_seed + camera_count)
    cameras = _cameras(camera_count)
    camera_by_id = {camera.camera_id: camera for camera in cameras}
    scheduling_policy = CameraSchedulingPolicy(
        high_interval_seconds=10,
        medium_interval_seconds=60,
        low_interval_seconds=60,
        max_dispatch_per_tick=8,
    )
    freshness_policy = FreshnessPolicy(
        fresh_threshold_seconds=30,
        aging_threshold_seconds=90,
    )
    aggregator = EmissionWindowAggregator(window_seconds=60)
    latest_state_store = LatestEmissionStateStore(_MemoryRedis(), ttl_seconds=3600)
    jobs: Queue[SimulatedJob | None] = Queue(maxsize=config.queue_capacity)
    state_lock = threading.Lock()
    queue_waits: list[float] = []
    batch_sizes: list[int] = []
    batch_latencies: list[float] = []
    latest_capture: dict[str, datetime] = {}
    processed: list[tuple[SimulatedJob, dict[str, int]]] = []
    successful_jobs = 0
    historical_writes = 0
    latest_state_writes = 0
    maximum_queue_depth = 0

    def process_batch(batch: list[SimulatedJob]) -> list[dict[str, int]]:
        time.sleep(
            (
                config.base_batch_latency_ms
                + config.per_item_latency_ms * len(batch)
            )
            / 1000
        )
        results = []
        for job in batch:
            camera_number = int(job.camera_id.rsplit("-", 1)[1])
            tick = int(job.captured_at.timestamp())
            results.append(
                {
                    "car": (camera_number + tick) % 12,
                    "motorcycle": (camera_number * 3 + tick) % 20,
                    "bus": (camera_number + tick) % 3,
                    "truck": (camera_number * 2 + tick) % 5,
                }
            )
        return results

    batcher = InferenceBatcher(
        process_batch,
        max_batch_size=config.max_batch_size,
        max_wait_ms=config.max_batch_wait_ms,
    )

    def consume() -> None:
        nonlocal successful_jobs
        while True:
            try:
                job = jobs.get(timeout=1)
            except Empty:
                continue
            try:
                if job is None:
                    return
                queue_wait_ms = max(0.0, time.monotonic() - job.enqueued_at) * 1000
                outcome = batcher.submit(job, timeout_s=10)
                counts = outcome.result
                calculate_emission(counts)
                with state_lock:
                    successful_jobs += 1
                    processed.append((job, counts))
                    queue_waits.append(queue_wait_ms)
                    batch_sizes.append(outcome.batch_size)
                    batch_latencies.append(outcome.batch_inference_latency_s * 1000)
            finally:
                jobs.task_done()

    consumers = [
        threading.Thread(target=consume, name=f"sim-worker-{index}", daemon=True)
        for index in range(config.worker_concurrency)
    ]
    for consumer in consumers:
        consumer.start()

    scheduled_samples = 0
    stream_failures = 0
    overload_skips = 0
    failure_counts = {camera.camera_id: 0 for camera in cameras}
    virtual_start = datetime(2026, 8, 21, tzinfo=timezone.utc)
    tracemalloc.start()
    wall_started_at = time.monotonic()
    cpu_started_at = time.process_time()

    plan_due_cameras(cameras, virtual_start, scheduling_policy)
    for offset in range(config.virtual_duration_seconds + 1):
        virtual_now = virtual_start + timedelta(seconds=offset)
        plan = plan_due_cameras(cameras, virtual_now, scheduling_policy)
        for scheduled in plan.due_cameras:
            scheduled_samples += 1
            if random_generator.random() < config.stream_failure_rate:
                stream_failures += 1
                failure_counts[scheduled.camera_id] += 1
                retry_delay = min(
                    5 * (2 ** (failure_counts[scheduled.camera_id] - 1)),
                    60,
                )
                camera_by_id[scheduled.camera_id].next_sample_at = (
                    virtual_now + timedelta(seconds=retry_delay)
                )
                continue
            camera = camera_by_id[scheduled.camera_id]
            job = SimulatedJob(
                job_id=f"{scheduled.camera_id}-{offset}",
                camera_id=scheduled.camera_id,
                database_id=camera.database_id,
                captured_at=virtual_now,
                enqueued_at=time.monotonic(),
            )
            try:
                jobs.put_nowait(job)
                failure_counts[scheduled.camera_id] = 0
            except Full:
                overload_skips += 1
            maximum_queue_depth = max(maximum_queue_depth, jobs.qsize())
        if config.time_scale > 0:
            time.sleep(config.time_scale)

    jobs.join()
    for _consumer in consumers:
        jobs.put(None)
    jobs.join()
    for consumer in consumers:
        consumer.join(timeout=5)
    batcher.stop()

    for job, counts in sorted(
        processed,
        key=lambda item: (item[0].captured_at, item[0].camera_id),
    ):
        update = aggregator.add(
            EmissionObservation(
                camera_id=job.camera_id,
                camera_database_id=job.database_id,
                job_id=job.job_id,
                captured_at=job.captured_at,
                vehicle_counts=counts,
            )
        )
        latest_state_store.save(update.current)
        latest_state_writes += 1
        historical_writes += len(update.completed)
        latest_capture[job.camera_id] = job.captured_at

    wall_time = time.monotonic() - wall_started_at
    cpu_time = time.process_time() - cpu_started_at
    _current_heap, peak_heap = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    freshness_counts = {status: 0 for status in FreshnessStatus}
    virtual_end = virtual_start + timedelta(seconds=config.virtual_duration_seconds)
    for camera in cameras:
        freshness = classify_freshness(
            latest_capture.get(camera.camera_id),
            now=virtual_end,
            policy=freshness_policy,
        )
        freshness_counts[freshness.status] += 1

    return SimulationResult(
        camera_count=camera_count,
        virtual_duration_seconds=config.virtual_duration_seconds,
        wall_time_seconds=round(wall_time, 4),
        process_cpu_time_seconds=round(cpu_time, 4),
        approximate_process_cpu_percent=round(
            100 * cpu_time / wall_time if wall_time else 0,
            2,
        ),
        python_heap_peak_mib=round(peak_heap / (1024 * 1024), 3),
        scheduled_samples=scheduled_samples,
        successful_jobs=successful_jobs,
        stream_failures=stream_failures,
        overload_skips=overload_skips,
        max_queue_depth=maximum_queue_depth,
        mean_queue_wait_ms=round(statistics.fmean(queue_waits) if queue_waits else 0, 3),
        p95_queue_wait_ms=round(_percentile(queue_waits, 0.95), 3),
        mean_batch_size=round(statistics.fmean(batch_sizes) if batch_sizes else 0, 3),
        max_batch_size=max(batch_sizes, default=0),
        mean_batch_inference_ms=round(
            statistics.fmean(batch_latencies) if batch_latencies else 0,
            3,
        ),
        inference_throughput_jobs_per_second=round(
            successful_jobs / wall_time if wall_time else 0,
            2,
        ),
        latest_state_writes=latest_state_writes,
        historical_aggregate_writes=historical_writes,
        websocket_updates=successful_jobs,
        fresh_cameras=freshness_counts[FreshnessStatus.FRESH],
        aging_cameras=freshness_counts[FreshnessStatus.AGING],
        stale_cameras=freshness_counts[FreshnessStatus.STALE],
        unknown_cameras=freshness_counts[FreshnessStatus.UNKNOWN],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--camera-counts",
        type=int,
        nargs="+",
        default=[5, 10, 20, 40, 56],
    )
    parser.add_argument("--virtual-duration-seconds", type=int, default=120)
    parser.add_argument("--time-scale", type=float, default=0.01)
    parser.add_argument("--stream-failure-rate", type=float, default=0.02)
    parser.add_argument("--queue-capacity", type=int, default=64)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = SimulationConfig(
        virtual_duration_seconds=args.virtual_duration_seconds,
        time_scale=args.time_scale,
        stream_failure_rate=args.stream_failure_rate,
        queue_capacity=args.queue_capacity,
    )
    print(json.dumps({"simulation_config": asdict(config)}, sort_keys=True))
    for camera_count in args.camera_counts:
        print(json.dumps(asdict(run_stage(camera_count, config)), sort_keys=True))


if __name__ == "__main__":
    main()
