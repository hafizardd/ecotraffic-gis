import logging
import time
import uuid

from app.observability import metrics as m
from app.observability.logging import request_id

logger = logging.getLogger(__name__)


class MetricsMiddleware:
    """Pure ASGI: preserves streaming, backpressure, disconnects and exception propagation."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['path'] in ('/metrics', '/api/telemetry'):
            return await self.app(scope, receive, send)
        started = time.monotonic()
        rid = uuid.uuid4().hex
        token = request_id.set(rid)
        status = 500
        streaming = False
        outcome = 'complete'
        method = scope['method'] if scope['method'] in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD') else 'OTHER'
        m.INFLIGHT.inc()

        def route():
            return getattr(scope.get('route'), 'path', 'unmatched')

        async def observed_send(message):
            nonlocal status, streaming
            if message['type'] == 'http.response.start':
                status = message['status']
                headers = list(message.get('headers', []))
                content_type = dict(headers).get(b'content-type', b'')
                streaming = b'multipart/' in content_type or '/live/' in scope['path'] or b'text/event-stream' in content_type
                headers.append((b'x-request-id', rid.encode()))
                message = {**message, 'headers': headers}
                m.HEADERS.labels(method, route()).observe(time.monotonic() - started)
            await send(message)

        try:
            await self.app(scope, receive, observed_send)
        except BaseException as exc:
            outcome = 'cancelled' if type(exc).__name__ == 'CancelledError' else 'error'
            if outcome == 'error':
                logger.exception('http_request_failed', extra={'route': route(), 'method': method})
            raise
        finally:
            elapsed = time.monotonic() - started
            m.INFLIGHT.dec()
            m.REQUESTS.labels(method, route(), str(status)).inc()
            if not streaming:
                m.DURATION.labels(method, route()).observe(elapsed)
            logger.info('http_request', extra={'route': route(), 'method': method, 'status': status,
                        'duration_ms': round(elapsed * 1000, 2), 'streaming': streaming, 'outcome': outcome})
            request_id.reset(token)
