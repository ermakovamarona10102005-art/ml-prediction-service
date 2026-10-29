import importlib.util
from pathlib import Path
import psycopg2
from prometheus_client.parser import text_string_to_metric_families

spec = importlib.util.spec_from_file_location('lab8_logger', Path(__file__).resolve().parents[1] / 'app.py')
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)
PAYLOAD = {'input_data': {'features': [1, 2]}, 'prediction': {'class': 0, 'probability': 0.99}, 'model_version': 'v2.0'}


def test_health_and_metrics():
    client = service.app.test_client()
    assert client.get('/health').get_json()['service'] == 'logger'
    assert 'logger_requests_total' in client.get('/metrics').get_data(as_text=True)


def test_missing_fields():
    assert service.app.test_client().post('/log', json={}).status_code == 400


def test_successful_write_returns_id_and_closes_connection(monkeypatch):
    writes = []

    class Connection:
        closed = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return self

        def execute(self, query, values):
            writes.append(values)

        def fetchone(self):
            return (42,)

        def close(self):
            self.closed = True

    conn = Connection()
    monkeypatch.setattr(service, 'get_db', lambda: conn)
    response = service.app.test_client().post('/log', json=PAYLOAD)
    assert response.status_code == 201
    assert response.get_json() == {'status': 'logged', 'id': 42}
    assert writes[0][2] == 'v2.0'
    assert conn.closed


def test_db_error_is_reported(monkeypatch):
    def fail():
        raise psycopg2.OperationalError('controlled failure')

    monkeypatch.setattr(service, 'get_db', fail)
    assert service.app.test_client().post('/log', json=PAYLOAD).status_code == 500
    text = service.app.test_client().get('/metrics').get_data(as_text=True)
    values = [s.value for f in text_string_to_metric_families(text)
              for s in f.samples if s.name == 'logger_db_errors_total']
    assert sum(values) >= 1
