#!/usr/bin/env python3
import json
from urllib.request import urlopen

with urlopen('http://localhost:9090/api/v1/targets') as r:
    targets = json.load(r)['data']['activeTargets']
for t in targets:
    print('TARGET:', t['labels']['job'], t['health'], t['lastError'] or 'no errors')
assert len(targets) == 4 and all(t['health'] == 'up' for t in targets)
for port in [5000, 5001]:
    with urlopen(f'http://localhost:{port}/metrics') as r:
        for line in r.read().decode().splitlines():
            names = ('ml_predictions_total', 'ml_logger_errors_total', 'logger_requests_total', 'logger_db_errors_total')
            if line.startswith(names):
                print(line)
print('FOUR MONITORING TARGETS: PASSED')
