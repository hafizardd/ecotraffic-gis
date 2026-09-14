"""Clean only this container's ephemeral Prometheus files before prefork starts."""
import os
from pathlib import Path

if __name__ == '__main__':
    directory = Path('/tmp/ecotraffic-prometheus')
    directory.mkdir(exist_ok=True)
    for file in directory.glob('*.db'):
        file.unlink()
    os.environ['PROMETHEUS_MULTIPROC_DIR'] = str(directory)
    os.execvp('celery', ['celery', '-A', 'app.workers.celery_app', 'worker', '-Q', 'inference', '--loglevel=info', '--concurrency=1'])
