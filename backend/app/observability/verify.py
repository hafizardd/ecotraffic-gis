"""Run inside the backend container after stack startup: python -m app.observability.verify."""
import json
import sys
import time
from urllib.request import urlopen


def read(url):
    with urlopen(url, timeout=5) as response:
        return json.load(response)


def main():
    expected = {'api', 'tracker', 'worker', 'node', 'cadvisor', 'redis', 'prometheus'}
    last_error = None
    for _ in range(12):
        try:
            assert read('http://grafana:3000/api/health')['database'] == 'ok', 'Grafana database not ready'
            assert read('http://backend:8000/health')['status'] == 'ok', 'API not ready'
            targets = read('http://prometheus:9090/api/v1/targets')['data']['activeTargets']
            healthy = {t['labels']['job'] for t in targets if t['health'] == 'up'}
            assert expected <= healthy, f'Scrape targets not ready: {sorted(expected - healthy)}'
            with urlopen('http://loki:3100/ready', timeout=5) as response:
                assert response.status == 200, 'Loki not ready'
            labels = read('http://loki:3100/loki/api/v1/label/service/values')['data']
            assert 'backend' in labels, 'Backend logs not yet visible in Loki'
            print('OK: Grafana, API, Loki logs and all seven Prometheus scrape jobs are ready.')
            return 0
        except Exception as exc:
            last_error = str(exc)
            time.sleep(2)
    print(f'FAILED: {last_error}', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
