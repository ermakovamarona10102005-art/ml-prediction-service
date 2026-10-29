import json
import sys
from pathlib import Path

import psycopg2
from prometheus_client.parser import text_string_to_metric_families

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as service  # noqa: E402

FEATURES = [14.23, 1.71, 2.43, 15.6, 127, 2.8, 3.06, 0.28, 2.29, 5.64, 1.04, 3.92, 1065]


def counter(name):
    text = service.app.test_client().get('/metrics').get_data(as_text=True)
    return sum(sample.value for family in text_string_to_metric_families(text)
               for sample in family.samples if sample.name == name)


def test_metrics_format_and_business_names():
    response = service.app.test_client().get('/metrics')
    assert response.status_code == 200
    assert response.content_type.startswith('text/plain')
    for name in ['ml_predictions_total', 'ml_db_errors_total', 'ml_labeled_predictions_total', 'ml_model_info']:
        assert name in response.get_data(as_text=True)


def test_prediction_persists_and_updates_quality(monkeypatch):
    writes = []

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return self

        def execute(self, query, values):
            writes.append(values)

        def close(self):
            pass

    monkeypatch.setattr(service, 'get_db', Connection)
    before = counter('ml_correct_predictions_total')
    result = service.app.test_client().post('/predict', json={'features': FEATURES, 'true_class': 0})
    assert result.status_code == 200
    assert result.get_json()['class'] == 0
    assert writes[0][2] == 'v2.0'
    assert json.loads(writes[0][0])['features'] == FEATURES
    assert counter('ml_correct_predictions_total') == before + 1


def test_database_failure_is_visible(monkeypatch):
    def unavailable():
        raise psycopg2.OperationalError('test database unavailable')

    monkeypatch.setattr(service, 'get_db', unavailable)
    before = counter('ml_db_errors_total')
    response = service.app.test_client().post('/predict', json={'features': FEATURES})
    assert response.status_code == 503
    assert counter('ml_db_errors_total') == before + 1


def test_invalid_reference_class_rejected():
    response = service.app.test_client().post('/predict', json={'features': FEATURES, 'true_class': 999})
    assert response.status_code == 400
