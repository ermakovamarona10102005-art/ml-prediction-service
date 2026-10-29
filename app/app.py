from flask import Flask, request, jsonify, Response
from pathlib import Path
from prometheus_client import Counter, Histogram, Gauge
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import urllib.request
import urllib.error
import json
import os
import pickle
import time
import math

app = Flask(__name__)
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "model" / "model.pkl"
MODEL_PATH = os.getenv("MODEL_PATH", str(DEFAULT_MODEL_PATH))
MODEL_VERSION = "v2.0"
with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

PREDICTIONS_TOTAL = Counter("ml_predictions_total", "Successful predictions", ["model_version", "predicted_class"])
PREDICTION_LATENCY = Histogram("ml_prediction_latency_seconds", "Prediction and database latency in seconds")
LOGGER_ERRORS_TOTAL = Counter("ml_logger_errors_total", "HTTP logging failures")
LABELED_TOTAL = Counter("ml_labeled_predictions_total", "Predictions with a supplied reference class")
CORRECT_TOTAL = Counter("ml_correct_predictions_total", "Predictions matching the supplied reference class")
MODEL_INFO = Gauge("ml_model_info", "Loaded model version", ["version"])
MODEL_INFO.labels(version=MODEL_VERSION).set(1)
for cls in model.classes_:
    PREDICTIONS_TOTAL.labels(model_version=MODEL_VERSION, predicted_class=str(cls)).inc(0)


LOGGER_URL = os.getenv("LOGGER_URL", "http://logger-service:5001/log")


def send_log(features, result):
    payload = json.dumps({"input_data": {"features": features},
                          "prediction": result, "model_version": MODEL_VERSION}).encode()
    req = urllib.request.Request(LOGGER_URL, payload, {"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            logged = json.load(response)
            if response.status != 201 or logged.get("status") != "logged" or not isinstance(logged.get("id"), int):
                raise ValueError("Unexpected logger response")
            return logged["id"]
    except (urllib.error.URLError, OSError, ValueError):
        LOGGER_ERRORS_TOTAL.inc()
        app.logger.warning("Logger service unavailable; prediction returned without persistence")
        return None


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "prediction"})


@app.route("/metrics", methods=["GET"])
def metrics():
    return Response(generate_latest(), content_type=CONTENT_TYPE_LATEST)


@app.route("/predict", methods=["POST"])
def predict():
    start = time.perf_counter()
    data = request.get_json(force=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    features = data.get("features", [])
    if not isinstance(features, list) or len(features) != model.n_features_in_:
        return jsonify({"error": f"Expected {model.n_features_in_} features"}), 400
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in features):
        return jsonify({"error": "Features must be finite numbers"}), 400
    true_class = data.get("true_class")
    if true_class is not None and (isinstance(true_class, bool) or true_class not in model.classes_):
        return jsonify({"error": "Invalid reference class"}), 400
    try:
        pred = int(model.predict([features])[0])
        proba = float(max(model.predict_proba([features])[0]))
        result = {"class": pred, "probability": proba}
        log_id = send_log(features, result)
        PREDICTIONS_TOTAL.labels(model_version=MODEL_VERSION, predicted_class=str(pred)).inc()
        if true_class is not None:
            LABELED_TOTAL.inc()
            if pred == true_class:
                CORRECT_TOTAL.inc()
        response = jsonify(result)
        response.headers["X-Log-Status"] = "logged" if log_id is not None else "failed"
        if log_id is not None:
            response.headers["X-Log-Id"] = str(log_id)
        return response
    finally:
        PREDICTION_LATENCY.observe(time.perf_counter() - start)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
