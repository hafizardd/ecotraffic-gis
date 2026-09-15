import logging
import time
from celery import signals
from prometheus_client import multiprocess
from app.observability import metrics as m
from app.observability.logging import configure_logging

_started = {}
logger = logging.getLogger(__name__)


@signals.setup_logging.connect
def setup(**kwargs):
    configure_logging()


@signals.worker_ready.connect
def ready(**kwargs):
    m.start_exporter()


@signals.worker_process_shutdown.connect
def stopped(pid=None, **kwargs):
    import os
    if pid and os.getenv('PROMETHEUS_MULTIPROC_DIR'):
        multiprocess.mark_process_dead(pid)


@signals.task_prerun.connect
def before(task_id=None, **kwargs):
    _started[task_id] = time.monotonic()
    m.TASK_ACTIVE.inc()


@signals.task_postrun.connect
def after(task_id=None, task=None, state=None, **kwargs):
    started = _started.pop(task_id, None)
    if started is None:
        return
    duration = time.monotonic() - started
    name = task.name if task else 'unknown'
    m.TASK_ACTIVE.dec()
    m.TASKS.labels(name, state or 'UNKNOWN').inc()
    m.TASK_TIME.labels(name).observe(duration)
    m.TASK_LAST.set(time.time())
    logger.info('worker_task_completed', extra={'task': name, 'task_id': task_id, 'state': state, 'duration_ms': round(duration * 1000, 2)})
