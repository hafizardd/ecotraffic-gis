import json
import logging
import os
from contextvars import ContextVar
from datetime import datetime, timezone

request_id = ContextVar('request_id', default=None)
_STANDARD = set(logging.makeLogRecord({}).__dict__) | {'message', 'asctime'}
_SENSITIVE = ('password', 'secret', 'token', 'authorization', 'cookie', 'body', 'prompt', 'query', 'url')


def safe(value):
    if isinstance(value, dict):
        return {k: '[REDACTED]' if any(s in str(k).lower() for s in _SENSITIVE) else safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(v) for v in value]
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {'timestamp': datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
                'level': record.levelname, 'service': os.getenv('SERVICE_NAME', 'backend'),
                'environment': os.getenv('APP_ENV', 'development'), 'logger': record.name,
                'message': record.getMessage()}
        data.update(safe({k: v for k, v in record.__dict__.items() if k not in _STANDARD}))
        if request_id.get():
            data['request_id'] = request_id.get()
        if record.exc_info:
            # Exception messages can contain SQL parameters or credentials. Keep type and stack locations only.
            import traceback
            data['exception_type'] = record.exc_info[0].__name__
            data['stack'] = [{'file': f.filename, 'line': f.lineno, 'function': f.name}
                             for f in traceback.extract_tb(record.exc_info[2])]
        return json.dumps(data, default=str)


def configure_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'), handlers=[handler], force=True)
    for name in ('uvicorn', 'uvicorn.error', 'celery'):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
    # Access logs include raw query strings. Our middleware emits sanitized route templates.
    for name in ('uvicorn.access', 'httpx', 'httpcore', 'sqlalchemy.engine'):
        logging.getLogger(name).setLevel(logging.WARNING)
