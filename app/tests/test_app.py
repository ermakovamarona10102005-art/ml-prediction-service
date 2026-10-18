import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "app"))

os.environ["MODEL_PATH"] = str(PROJECT_ROOT / "model" / "model.pkl")

from app import app  # noqa: E402


def test_health():
    client = app.test_client()
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_predict_without_features():
    client = app.test_client()
    response = client.post("/predict", json={})

    assert response.status_code == 400
