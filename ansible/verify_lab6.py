"""End-to-end lab verification; does not print credentials."""
import json
import urllib.request
from pathlib import Path

import psycopg2

base = Path(__file__).resolve().parents[1]
values = dict(line.split('=', 1) for line in (base / 'docker/.env').read_text().splitlines()
              if line and not line.startswith('#') and '=' in line)
with urllib.request.urlopen('http://localhost:5000/health', timeout=15) as response:
    print('HEALTH:', response.read().decode())
payload = {'features': [14.23, 1.71, 2.43, 15.6, 127, 2.8, 3.06, 0.28, 2.29, 5.64, 1.04, 3.92, 1065]}
conn = psycopg2.connect(host='10.10.10.11', dbname='ml_predictions', user='ml_app',
                        password=values['DB_PASSWORD'], sslmode='require', connect_timeout=15)
with conn.cursor() as cursor:
    cursor.execute('SELECT COALESCE(MAX(id), 0) FROM predictions')
    previous_id = cursor.fetchone()[0]
request = urllib.request.Request('http://localhost:5000/predict', data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(request, timeout=30) as response:
    result = json.loads(response.read())
    print('PREDICTION:', json.dumps(result))
with conn.cursor() as cursor:
    cursor.execute('SELECT id, timestamp, input_data, prediction, model_version FROM predictions WHERE id > %s ORDER BY id DESC', (previous_id,))
    rows = cursor.fetchall()
    assert any(row[2] == payload and row[3] == result for row in rows), 'New prediction was not saved correctly'
    for row in rows:
        print('NEW DATABASE ROW:', row)
conn.close()
print('END-TO-END CHECK: PASSED')
