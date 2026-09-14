import os

from prometheus_client import Counter, Gauge, Histogram, REGISTRY, CollectorRegistry, multiprocess, start_http_server

LATENCY = (.01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10, 30, 60)
REQUESTS = Counter('eco_http_requests_total', 'Completed HTTP requests', ['method', 'route', 'status'])
DURATION = Histogram('eco_http_duration_seconds', 'Non-streaming request duration through final body', ['method', 'route'], buckets=LATENCY)
HEADERS = Histogram('eco_http_headers_seconds', 'Time until response headers', ['method', 'route'], buckets=LATENCY)
INFLIGHT = Gauge('eco_http_inflight', 'Active HTTP requests', multiprocess_mode='livesum')
STREAMS = Gauge('eco_video_active', 'Active streams', ['kind'], multiprocess_mode='livesum')
VIDEO_UPSTREAM = Histogram('eco_video_upstream_seconds', 'Upstream HLS playlist fetch duration', buckets=LATENCY)
VIDEO_FIRST = Histogram('eco_video_first_frame_seconds', 'Time to first MJPEG frame yielded by server', buckets=LATENCY)
VIDEO_BYTES = Counter('eco_video_bytes_total', 'Media payload bytes yielded by server', ['kind'])
VIDEO_FRAMES = Counter('eco_video_frames_total', 'MJPEG frames yielded by server')
VIDEO_ERRORS = Counter('eco_video_errors_total', 'Stream dependency errors', ['kind', 'reason'])
VIDEO_MISSING = Counter('eco_video_missing_frame_total', 'Redis polls without a frame')
REDIS_TIME = Histogram('eco_video_redis_seconds', 'Snapshot Redis GET duration', buckets=LATENCY)
INFERENCE = Histogram('eco_tracker_inference_seconds', 'YOLO inference duration', ['camera'], buckets=LATENCY)
TRACK_FRAMES = Counter('eco_tracker_frames_total', 'Successfully stored annotated frames', ['camera'])
TRACK_LAST = Gauge('eco_tracker_last_frame_timestamp_seconds', 'Last successfully stored frame, Unix time; zero before first frame', ['camera'])
TRACK_ERRORS = Counter('eco_tracker_errors_total', 'Tracker errors', ['camera', 'stage'])
TASKS = Counter('eco_worker_tasks_total', 'Completed Celery tasks', ['task', 'state'])
TASK_TIME = Histogram('eco_worker_task_seconds', 'Celery task execution duration', ['task'], buckets=LATENCY)
TASK_ACTIVE = Gauge('eco_worker_tasks_active', 'Executing Celery tasks', multiprocess_mode='livesum')
TASK_LAST = Gauge('eco_worker_last_task_timestamp_seconds', 'Last task completion', multiprocess_mode='max')
DB_TIME = Histogram('eco_db_query_seconds', 'SQL statement execution duration, excluding pool wait', ['database'], buckets=LATENCY)
DB_ERRORS = Counter('eco_db_errors_total', 'SQL execution errors', ['database'])
BROWSER_EVENTS = Counter('eco_browser_events_total', 'Sampled browser events; untrusted client reports', ['name', 'route', 'outcome'])
BROWSER_TIME = Histogram('eco_browser_duration_seconds', 'Sampled browser duration', ['name', 'route', 'outcome'], buckets=LATENCY)


def registry():
    if os.environ.get('PROMETHEUS_MULTIPROC_DIR'):
        result = CollectorRegistry()
        multiprocess.MultiProcessCollector(result)
        return result
    return REGISTRY


def start_exporter():
    port = int(os.getenv('METRICS_PORT', '0'))
    if port:
        start_http_server(port, registry=registry())
