#!/usr/bin/env python3
import json
from urllib.request import urlopen

with urlopen('http://127.0.0.1:9090/api/v1/alerts', timeout=10) as response:
    alerts = json.load(response)['data']['alerts']
for alert in alerts:
    print(alert['labels']['alertname'], alert['state'], 'value=' + alert['value'])
if not alerts:
    print('No active Prometheus alerts')
