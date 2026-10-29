#!/usr/bin/env python3
"""Read-only verification of the running monitoring stack."""
import json
from urllib.request import urlopen


def get(port, path):
    with urlopen(f'http://127.0.0.1:{port}{path}', timeout=15) as response:
        return json.load(response)


print('HEALTH:', get(5000, '/health'))
targets = get(9090, '/api/v1/targets')['data']['activeTargets']
for target in targets:
    print('TARGET:', target['labels']['job'], target['health'], target['lastError'] or 'no errors')
assert len(targets) == 3 and all(t['health'] == 'up' for t in targets)
rules = get(9090, '/api/v1/rules')['data']['groups']
for group in rules:
    for rule in group['rules']:
        print('RULE:', rule['name'], rule['health'], rule.get('state', ''))
        assert rule['health'] == 'ok'
print('GRAFANA:', get(3000, '/api/health')['database'])
print('MONITORING CHECK: PASSED')
