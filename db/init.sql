-- Выполняется от имени пользователя postgres.
CREATE DATABASE ml_predictions;

CREATE USER ml_app WITH ENCRYPTED PASSWORD 'your_password_here';
GRANT CONNECT ON DATABASE ml_predictions TO ml_app;

\connect ml_predictions

CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    input_data JSONB NOT NULL,
    prediction JSONB NOT NULL,
    model_version VARCHAR(50) NOT NULL
);

GRANT USAGE ON SCHEMA public TO ml_app;
GRANT SELECT, INSERT ON TABLE predictions TO ml_app;
GRANT USAGE, SELECT ON SEQUENCE predictions_id_seq TO ml_app;
