from flask import Flask, request, jsonify, Response
from pathlib import Path
from prometheus_client import Counter, Histogram, Gauge
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import psycopg2
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
DB_ERRORS_TOTAL = Counter("ml_db_errors_total", "Database write errors")
LABELED_TOTAL = Counter("ml_labeled_predictions_total", "Predictions with a supplied reference class")
CORRECT_TOTAL = Counter("ml_correct_predictions_total", "Predictions matching the supplied reference class")
MODEL_INFO = Gauge("ml_model_info", "Loaded model version", ["version"])
MODEL_INFO.labels(version=MODEL_VERSION).set(1)
for cls in model.classes_:
    PREDICTIONS_TOTAL.labels(model_version=MODEL_VERSION, predicted_class=str(cls)).inc(0)


def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "10.10.10.11"),
        dbname=os.getenv("DB_NAME", "ml_predictions"),
        user=os.getenv("DB_USER", "ml_app"),
        password=os.getenv("DB_PASSWORD"),
        sslmode=os.getenv("DB_SSLMODE", "require"),
        connect_timeout=5
    )


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


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
        conn = None
        try:
            conn = get_db()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO predictions (input_data, prediction, model_version) VALUES (%s, %s, %s)",
                        (json.dumps({"features": features}), json.dumps(result), MODEL_VERSION)
                    )
        except psycopg2.Error:
            DB_ERRORS_TOTAL.inc()
            app.logger.error("Prediction database write failed")
            return jsonify({"error": "Database unavailable"}), 503
        finally:
            if conn is not None:
                conn.close()
        PREDICTIONS_TOTAL.labels(model_version=MODEL_VERSION, predicted_class=str(pred)).inc()
        if true_class is not None:
            LABELED_TOTAL.inc()
            if pred == true_class:
                CORRECT_TOTAL.inc()
        return jsonify(result)
    finally:
        PREDICTION_LATENCY.observe(time.perf_counter() - start)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
