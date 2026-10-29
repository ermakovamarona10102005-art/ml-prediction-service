#!/usr/bin/env bash
set -euo pipefail
image=${1:?Supply the exact container image tag}
test -s docker/.env
docker pull "$image"
previous=$(docker inspect --format '{{.Image}}' ml-app 2>/dev/null || true)
deploy_image() {
  APP_IMAGE="$1" docker compose --env-file docker/.env -f docker/docker-compose.yml up -d --no-build app
}
deploy_image "$image"
healthy=false
for attempt in $(seq 1 30); do
  if curl -fsS --max-time 3 http://127.0.0.1:5000/health && curl -fsS --max-time 3 http://127.0.0.1:5000/metrics >/dev/null; then
    healthy=true
    break
  fi
  sleep 3
done
if [ "$healthy" != true ]; then
  echo 'New container failed health check; restoring previous image.' >&2
  if [ -n "$previous" ]; then deploy_image "$previous"; fi
  exit 1
fi
echo 'DEPLOY HEALTH AND METRICS CHECK: PASSED'
