# Laboratory 7 monitoring

The app uses the existing Wine model v2.0 (13 numeric features). PostgreSQL
remains on VM100, 10.10.10.11. Monitoring runs with the app on VM101,
10.10.10.12. Inspect the current DHCP address before opening browser pages.

## Start

Use PowerShell SSH to connect to app-server, then run:

```sh
cd ~/ml-prediction-service
mkdir -p monitoring/.secrets
chmod 700 monitoring/.secrets
openssl rand -base64 24 > monitoring/.secrets/grafana-admin-password
chmod 644 monitoring/.secrets/grafana-admin-password
# Keep the existing docker/.env with DB_PASSWORD. Do not commit it.
docker compose --env-file docker/.env -f docker/docker-compose.yml up -d --build
python3 scripts/verify_monitoring.py
```

Create the Grafana password file only for a new installation. Existing Grafana
data keeps its administrator password; replacing the file does not reset it.
The secret directory has mode 0700, and the file must be readable by the
container's Grafana user. Secrets are excluded from Git and Docker context.

Services: Flask 5000, Grafana 3000, Prometheus 9090, Alertmanager 9093,
Node Exporter 9100. Grafana's login is `admin`; its password is in the local
secret file. The data source and eight-panel dashboard are provisioned from
the files in this directory. Monitoring data uses named Docker volumes.

## Metric semantics

`ml_predictions_total` counts successful predictions whose database write
succeeded, labeled with model version and predicted class. The histogram
`ml_prediction_latency_seconds` includes inference and database work.
Database write failures return 503 and increment `ml_db_errors_total`.

An optional `true_class` in a prediction request supplies a reference label.
Only these requests increment `ml_labeled_predictions_total`; a matching
result also increments `ml_correct_predictions_total`. Grafana displays their
rate ratio. This is accuracy on labeled requests, not model confidence and
not a claim about unknown production labels. At least ten labeled samples in
the alert's ten-minute window are required for LowPredictionAccuracy.

## Alerts and notifications

Prometheus scrapes the application, Node Exporter and itself every 15 seconds.
Rules cover service outage, p95 latency above one second, labeled accuracy
below 80%, database errors and absent traffic. Alertmanager sends firing and
resolved notifications to the actual local `alert-receiver` service. Inspect:

```sh
docker logs alert-receiver
docker exec alert-receiver cat /data/notifications.jsonl
```

The laboratory receiver records notifications locally; it sends no email,
Telegram or other third-party message.

For the outage exercise, stop `ml-app`, wait at least 90 seconds, check
Prometheus and Alertmanager, then start it again. A deliberate Docker stop
does not invoke the restart policy. For a crash exercise, kill PID 1 inside
the container and compare RestartCount and health before and after recovery.
Keep failure exercises separate from normal traffic.

## Database backups

On the database VM, install `scripts/backup_db.sh` as
`/usr/local/sbin/lab7-backup-db` (root:root, 0700), and install `backup.cron` as
`/etc/cron.d/lab7-postgresql` (root:root, 0644). The daily 02:00 schedule uses
the database server's time zone. Backups use PostgreSQL peer authentication,
contain no embedded database password and are kept for seven days in
`/var/backups/ml-predictions` (0700). The script prevents overlapping runs,
creates a custom-format dump atomically, validates its archive directory and
writes a SHA256 checksum. Check actual restore in a separate temporary
database before relying on the backup; never overwrite the working database
for a test.

## Application deployment

`scripts/deploy.sh <exact-image-tag>` deploys only the app service with Compose
so its healthcheck and monitoring network remain attached. The app supports
APP_IMAGE overrides for CI-produced images. Grafana's secret is stored
outside docker/.env so the CI database secret update does not remove it.
