"""Verify the separately provisioned VMs; never print credentials."""
import json
import os
import urllib.request
import subprocess
from pathlib import Path

# Run from the application VM so PostgreSQL keeps its app-only access rule.
# The password travels through encrypted stdin, never an argument or a file.
if os.environ.get('LAB6_VERIFY_ON_APP') != '1':
    prefix = 'import os\nos.environ["LAB6_VERIFY_ON_APP"]="1"\nos.environ["LAB6_DB_PASSWORD"]=' + repr(os.environ['LAB6_DB_PASSWORD']) + '\n'
    result = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'student@10.10.10.22', 'python3', '-'],
                            input=prefix + Path(__file__).read_text(), text=True)
    raise SystemExit(result.returncode)

import psycopg2

api = 'http://10.10.10.22:5000'
payload = {'features': [14.23, 1.71, 2.43, 15.6, 127, 2.8, 3.06, 0.28, 2.29, 5.64, 1.04, 3.92, 1065]}
with urllib.request.urlopen(api + '/health', timeout=15) as response:
    assert json.load(response)['status'] == 'ok'
print('CLEAN APP HEALTH: OK')
with psycopg2.connect(host='10.10.10.21', dbname='ml_predictions', user='ml_app',
                     password=os.environ['LAB6_DB_PASSWORD'], sslmode='require', connect_timeout=15) as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT COALESCE(MAX(id),0) FROM predictions')
        previous = cur.fetchone()[0]
        print('PREVIOUS_MAX_ID:', previous)
    request = urllib.request.Request(api + '/predict', data=json.dumps(payload).encode(),
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        prediction = json.load(response)
    print('PREDICTION:', json.dumps(prediction))
    with conn.cursor() as cur:
        cur.execute('SELECT id,input_data,prediction,model_version FROM predictions WHERE id>%s ORDER BY id', (previous,))
        records = cur.fetchall()
        assert any(row[1] == payload and row[2] == prediction for row in records)
        for row in records:
            print('NEW CLEAN DATABASE ROW:', row)
print('CLEAN DEPLOYMENT END-TO-END: PASSED')
