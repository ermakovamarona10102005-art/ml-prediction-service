from flask import Flask, request, jsonify, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import psycopg2
import json
import os
import math

app = Flask(__name__)
LOG_REQUESTS_TOTAL = Counter("logger_requests_total", "Log requests", ["status"])
DB_WRITE_ERRORS = Counter("logger_db_errors_total", "Database write failures")
for status in ["success", "bad_request", "error"]:
    LOG_REQUESTS_TOTAL.labels(status=status).inc(0)


def get_db():
    return psycopg2.connect(host=os.getenv("DB_HOST", "10.10.10.11"),
                            dbname=os.getenv("DB_NAME", "ml_predictions"),
                            user=os.getenv("DB_USER", "ml_app"), password=os.environ["DB_PASSWORD"],
                            sslmode=os.getenv("DB_SSLMODE", "require"), connect_timeout=5)


@app.get("/health")
def health():
    return jsonify(status="ok", service="logger")


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), content_type=CONTENT_TYPE_LATEST)


@app.post("/log")
def log():
    data = request.get_json(silent=True)
    valid = isinstance(data, dict)
    if valid:
        inputs, prediction, version = data.get("input_data"), data.get("prediction"), data.get("model_version")
        valid = (isinstance(inputs, dict) and bool(inputs) and isinstance(prediction, dict)
                 and isinstance(prediction.get("class"), int) and not isinstance(prediction.get("class"), bool)
                 and isinstance(prediction.get("probability"), (int, float))
                 and math.isfinite(prediction["probability"]) and 0 <= prediction["probability"] <= 1
                 and isinstance(version, str) and 0 < len(version) <= 32)
    if not valid:
        LOG_REQUESTS_TOTAL.labels(status="bad_request").inc()
        return jsonify(error="input_data, prediction and model_version required"), 400
    conn = None
    try:
        conn = get_db()
        with conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO predictions (input_data, prediction, model_version) "
                            "VALUES (%s, %s, %s) RETURNING id",
                            (json.dumps(inputs), json.dumps(prediction), version))
                new_id = cur.fetchone()[0]
        LOG_REQUESTS_TOTAL.labels(status="success").inc()
        app.logger.info("Prediction logged: id=%s version=%s", new_id, version)
        return jsonify(status="logged", id=new_id), 201
    except psycopg2.Error:
        DB_WRITE_ERRORS.inc()
        LOG_REQUESTS_TOTAL.labels(status="error").inc()
        app.logger.error("Prediction database write failed")
        return jsonify(error="db_error"), 500
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    app.logger.setLevel("INFO")
    app.run(host="0.0.0.0", port=5001)
