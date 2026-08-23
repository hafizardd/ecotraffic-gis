from collections import deque
from collections.abc import Callable, Sequence
from concurrent.futures import Future
from dataclasses import dataclass
import logging
import threading
import time
from typing import Generic, TypeVar


InputType = TypeVar("InputType")
ResultType = TypeVar("ResultType")
logger = logging.getLogger(__name__)


class BatchResultMismatch(RuntimeError):
    pass


class BatcherStopped(RuntimeError):
    pass


class BatchResultTimeout(TimeoutError):
    pass


@dataclass(frozen=True, slots=True)
class BatchOutcome(Generic[ResultType]):
    result: ResultType
    batch_size: int
    batch_wait_s: float
    batch_inference_latency_s: float


@dataclass(slots=True)
class _PendingItem(Generic[InputType, ResultType]):
    value: InputType
    queued_at: float
    future: Future[BatchOutcome[ResultType]]


class InferenceBatcher(Generic[InputType, ResultType]):
    """Collect concurrent task inputs into short-lived ordered model batches."""

    def __init__(
        self,
        processor: Callable[[Sequence[InputType]], Sequence[ResultType]],
        *,
        max_batch_size: int,
        max_wait_ms: int,
        clock: Callable[[], float] = time.monotonic,
    ):
        if max_batch_size <= 0:
            raise ValueError("max_batch_size must be greater than zero")
        if max_wait_ms < 0:
            raise ValueError("max_wait_ms must not be negative")

        self.processor = processor
        self.max_batch_size = max_batch_size
        self.max_wait_s = max_wait_ms / 1000
        self.clock = clock
        self._condition = threading.Condition()
        self._pending: deque[_PendingItem[InputType, ResultType]] = deque()
        self._thread: threading.Thread | None = None
        self._stopping = False

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        with self._condition:
            if self.running:
                return
            self._stopping = False
            self._thread = threading.Thread(
                target=self._run,
                name="inference-micro-batcher",
                daemon=True,
            )
            self._thread.start()

    def submit(
        self,
        value: InputType,
        *,
        timeout_s: float | None = None,
    ) -> BatchOutcome[ResultType]:
        self.start()
        future: Future[BatchOutcome[ResultType]] = Future()
        with self._condition:
            if self._stopping:
                raise BatcherStopped("inference batcher is stopping")
            self._pending.append(
                _PendingItem(
                    value=value,
                    queued_at=self.clock(),
                    future=future,
                )
            )
            self._condition.notify_all()
        try:
            return future.result(timeout=timeout_s)
        except TimeoutError as exc:
            if future.done():
                processor_exception = future.exception()
                if isinstance(processor_exception, TimeoutError):
                    raise processor_exception
            raise BatchResultTimeout(
                f"inference batch result exceeded {timeout_s} seconds"
            ) from exc

    def stop(self) -> None:
        with self._condition:
            thread = self._thread
            if thread is None:
                return
            self._stopping = True
            self._condition.notify_all()

        if thread is not threading.current_thread():
            thread.join()

        with self._condition:
            self._thread = None

    def _run(self) -> None:
        while True:
            batch = self._collect_batch()
            if batch is None:
                return
            self._process_batch(batch)

    def _collect_batch(
        self,
    ) -> list[_PendingItem[InputType, ResultType]] | None:
        with self._condition:
            while not self._pending and not self._stopping:
                self._condition.wait()

            if not self._pending and self._stopping:
                return None

            deadline = self._pending[0].queued_at + self.max_wait_s
            while len(self._pending) < self.max_batch_size and not self._stopping:
                remaining = deadline - self.clock()
                if remaining <= 0:
                    break
                self._condition.wait(remaining)

            batch_size = min(len(self._pending), self.max_batch_size)
            return [self._pending.popleft() for _index in range(batch_size)]

    def _process_batch(
        self,
        batch: list[_PendingItem[InputType, ResultType]],
    ) -> None:
        inference_started_at = self.clock()
        try:
            results = list(self.processor([item.value for item in batch]))
            if len(results) != len(batch):
                raise BatchResultMismatch(
                    "batch processor returned "
                    f"{len(results)} results for {len(batch)} inputs"
                )
        except Exception as exc:
            logger.exception(
                "inference_batch_failed",
                extra={"batch_size": len(batch)},
            )
            for item in batch:
                item.future.set_exception(exc)
            return

        inference_latency_s = self.clock() - inference_started_at
        logger.info(
            "inference_batch_completed",
            extra={
                "batch_size": len(batch),
                "batch_inference_latency_s": round(inference_latency_s, 3),
            },
        )
        for item, result in zip(batch, results):
            item.future.set_result(
                BatchOutcome(
                    result=result,
                    batch_size=len(batch),
                    batch_wait_s=max(0.0, inference_started_at - item.queued_at),
                    batch_inference_latency_s=max(0.0, inference_latency_s),
                )
            )
