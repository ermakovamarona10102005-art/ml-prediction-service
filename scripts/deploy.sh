#!/usr/bin/env bash
set -euo pipefail
image=${1:?Supply the exact container image tag}
test -s docker/.env
docker pull "$image"
previous=$(docker inspect --format '{{.Image}}' ml-app 2>/dev/null || true)
run_image() {
  docker run -d --name ml-app --restart unless-stopped -p 5000:5000 \
    --env-file docker/.env \
    -e DB_HOST=10.10.10.11 -e DB_NAME=ml_predictions -e DB_USER=ml_app \
    -e DB_SSLMODE=require -e MODEL_PATH=/model/model.pkl "$1"
}
docker rm -f ml-app >/dev/null 2>&1 || true
run_image "$image"
healthy=false
for attempt in $(seq 1 20); do
  if curl -fsS --max-time 3 http://127.0.0.1:5000/health; then
    healthy=true
    break
  fi
  sleep 3
done
if [ "$healthy" != true ]; then
  echo 'New container failed health check; restoring previous image.' >&2
  docker rm -f ml-app >/dev/null 2>&1 || true
  if [ -n "$previous" ]; then run_image "$previous"; fi
  exit 1
fi
echo 'DEPLOY HEALTH CHECK: PASSED'
