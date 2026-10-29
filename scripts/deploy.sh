#!/usr/bin/env bash
set -euo pipefail
prediction=${1:?Supply prediction image}
logger=${2:?Supply logger image}
docker pull "$prediction"
docker pull "$logger"
umask 077
printf 'PREDICTION_IMAGE=%s\nLOGGER_IMAGE=%s\n' "$prediction" "$logger" > docker/images.env
docker compose --env-file docker/.env --env-file docker/images.env -f docker/docker-compose.yml up -d --no-build --remove-orphans
for attempt in $(seq 1 60); do
  if curl -fsS --max-time 3 http://localhost:5000/health && curl -fsS --max-time 3 http://localhost:5001/health; then
    echo 'MICROSERVICE DEPLOY HEALTH CHECK: PASSED'
    exit 0
  fi
  sleep 3
done
exit 1
