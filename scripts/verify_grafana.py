#!/usr/bin/env python3
import base64
import json
from pathlib import Path
from urllib.request import Request, urlopen

root = Path(__file__).resolve().parents[1]
password = (root / 'monitoring/.secrets/grafana-admin-password').read_text().strip()
auth = base64.b64encode(('admin:' + password).encode()).decode()


def get(path):
    req = Request('http://127.0.0.1:3000' + path, headers={'Authorization': 'Basic ' + auth})
    with urlopen(req, timeout=15) as response:
        return json.load(response)


source = get('/api/datasources/uid/prometheus')
assert source['type'] == 'prometheus' and source['url'] == 'http://prometheus:9090'
print('DATASOURCE:', source['name'], source['url'])
health = get('/api/datasources/uid/prometheus/health')
assert health['status'] == 'OK', health
print('DATASOURCE HEALTH:', health['status'], health.get('message', ''))
dashboard = get('/api/dashboards/uid/ml-prediction-overview')['dashboard']
assert len(dashboard['panels']) == 8
print('DASHBOARD:', dashboard['title'])
for panel in dashboard['panels']:
    print('PANEL:', panel['title'])
assert (root / 'monitoring/grafana-dashboard.json').exists()
print('GRAFANA PROVISIONING CHECK: PASSED')
