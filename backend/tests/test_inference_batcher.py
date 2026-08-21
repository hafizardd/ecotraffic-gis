from concurrent.futures import ThreadPoolExecutor
import threading
import time

import pytest

from app.services.inference_batcher import (
    BatchResultTimeout,
    BatchResultMismatch,
    InferenceBatcher,
)


def test_full_batch_maps_each_result_to_its_original_submitter():
    processed_batches = []

    def process(values):
        processed_batches.append(list(values))
        return [f"result-{value}" for value in values]

    batcher = InferenceBatcher(process, max_batch_size=3, max_wait_ms=500)
    try:
        with ThreadPoolExecutor(max_workers=3) as executor:
            outcomes = list(executor.map(batcher.submit, ["a", "b", "c"]))
    finally:
        batcher.stop()

    assert len(processed_batches) == 1
    assert sorted(processed_batches[0]) == ["a", "b", "c"]
    assert [outcome.result for outcome in outcomes] == [
        "result-a",
        "result-b",
        "result-c",
    ]
    assert {outcome.batch_size for outcome in outcomes} == {3}


def test_partial_batch_waits_only_until_the_configured_deadline():
    processing_started = threading.Event()

    def process(values):
        processing_started.set()
        return list(values)

    batcher = InferenceBatcher(process, max_batch_size=4, max_wait_ms=60)
    started_at = time.monotonic()
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(batcher.submit, "only-job")
            assert processing_started.wait(timeout=0.02) is False
            outcome = pending.result(timeout=1)
    finally:
        batcher.stop()

    assert outcome.result == "only-job"
    assert outcome.batch_size == 1
    assert outcome.batch_wait_s >= 0.04
    assert time.monotonic() - started_at < 1


def test_batch_failure_reaches_each_job_and_next_batch_can_recover():
    call_count = 0

    def process(values):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("model unavailable")
        return list(values)

    batcher = InferenceBatcher(process, max_batch_size=2, max_wait_ms=0)
    try:
        with pytest.raises(RuntimeError, match="model unavailable"):
            batcher.submit("failed-job")
        recovered = batcher.submit("recovered-job")
    finally:
        batcher.stop()

    assert recovered.result == "recovered-job"
    assert call_count == 2


def test_mismatched_processor_results_fail_the_affected_batch():
    batcher = InferenceBatcher(
        lambda _values: [],
        max_batch_size=1,
        max_wait_ms=0,
    )
    try:
        with pytest.raises(BatchResultMismatch, match="0 results for 1 inputs"):
            batcher.submit("job")
    finally:
        batcher.stop()


def test_submit_has_an_explicit_result_timeout():
    release_processor = threading.Event()

    def process(values):
        release_processor.wait(timeout=1)
        return list(values)

    batcher = InferenceBatcher(process, max_batch_size=1, max_wait_ms=0)
    try:
        with pytest.raises(BatchResultTimeout, match="exceeded 0.02 seconds"):
            batcher.submit("slow-job", timeout_s=0.02)
    finally:
        release_processor.set()
        batcher.stop()
