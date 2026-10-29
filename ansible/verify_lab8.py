#!/usr/bin/env python3
import json
import subprocess
from urllib.request import Request, urlopen
import psycopg2

features = [14.23, 1.71, 2.43, 15.6, 127, 2.8, 3.06, 0.28, 2.29, 5.64, 1.04, 3.92, 1065]
for port in [5000, 5001]:
    with urlopen(f'http://localhost:{port}/health', timeout=15) as r:
        print('HEALTH:', port, json.load(r))
req = Request('http://localhost:5000/predict', json.dumps({'features': features}).encode(),
              {'Content-Type': 'application/json'})
with urlopen(req, timeout=20) as response:
    result = json.load(response)
    assert response.headers['X-Log-Status'] == 'logged'
    log_id = int(response.headers['X-Log-Id'])
    print('PREDICTION:', result, 'LOGGER ROW ID:', log_id)
config = json.loads(subprocess.check_output(['docker', 'inspect', 'logger-service']))[0]
env = dict(item.split('=', 1) for item in config['Config']['Env'])
prediction = json.loads(subprocess.check_output(['docker', 'inspect', 'prediction-service']))[0]
assert not any(x.startswith('DB_') for x in prediction['Config']['Env'])
print('PREDICTION DB VARIABLES: absent')
with psycopg2.connect(host=env['DB_HOST'], dbname=env['DB_NAME'], user=env['DB_USER'],
                     password=env['DB_PASSWORD'], sslmode='require') as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT id, input_data, prediction, model_version FROM predictions WHERE id=%s', (log_id,))
        row = cur.fetchone()
        assert row[1]['features'] == features and row[2] == result and row[3] == 'v2.0'
        print('EXACT DATABASE ROW:', row)
print('MICROSERVICE END-TO-END CHECK: PASSED')
