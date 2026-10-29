import io
import json
import urllib.error
import app as service
from prometheus_client.parser import text_string_to_metric_families

FEATURES = [14.23, 1.71, 2.43, 15.6, 127, 2.8, 3.06, 0.28, 2.29, 5.64, 1.04, 3.92, 1065]


def counter(name):
    text = service.app.test_client().get('/metrics').get_data(as_text=True)
    return sum(s.value for f in text_string_to_metric_families(text) for s in f.samples if s.name == name)


def test_metrics():
    response = service.app.test_client().get('/metrics')
    assert response.status_code == 200
    assert 'ml_logger_errors_total' in response.get_data(as_text=True)


def test_prediction_calls_logger_via_http(monkeypatch):
    captured = []

    class Response(io.BytesIO):
        status = 201

    def send(req, timeout):
        captured.append(json.loads(req.data))
        assert req.full_url == 'http://logger-service:5001/log'
        assert timeout == 5
        return Response(b'{"status":"logged","id":42}')

    monkeypatch.setattr(service.urllib.request, 'urlopen', send)
    result = service.app.test_client().post('/predict', json={'features': FEATURES, 'true_class': 0})
    assert result.status_code == 200
    assert result.headers['X-Log-Id'] == '42'
    assert captured[0]['input_data']['features'] == FEATURES
    assert captured[0]['prediction'] == result.get_json()
    assert captured[0]['model_version'] == 'v2.0'


def test_logger_failure_keeps_prediction_available(monkeypatch):
    def unavailable(*args, **kwargs):
        raise urllib.error.URLError('controlled test')

    monkeypatch.setattr(service.urllib.request, 'urlopen', unavailable)
    before = counter('ml_logger_errors_total')
    result = service.app.test_client().post('/predict', json={'features': FEATURES})
    assert result.status_code == 200
    assert result.headers['X-Log-Status'] == 'failed'
    assert result.get_json()['class'] == 0
    assert counter('ml_logger_errors_total') == before + 1


def test_bad_reference_rejected():
    assert service.app.test_client().post('/predict', json={'features': FEATURES, 'true_class': 999}).status_code == 400
