#!/bin/bash
# Controlled laboratory crash of ml-app only. Run on app-server with sudo.
set -euo pipefail
test "$(id -u)" -eq 0
container=ml-app
before=$(docker inspect --format '{{.RestartCount}}' "$container")
pid=$(docker inspect --format '{{.State.Pid}}' "$container")
test "$pid" -gt 1
test "$(docker inspect --format '{{.State.Running}}' "$container")" = true
tr '\0' ' ' < "/proc/$pid/cmdline" | grep -q 'python app.py'
echo "BEFORE CRASH: restart_count=$before; container PID on VM=$pid"
echo 'Injecting SIGKILL into the actual ml-app process from the VM host namespace'
kill -KILL "$pid"
for attempt in $(seq 1 40); do
    after=$(docker inspect --format '{{.RestartCount}}' "$container")
    status=$(docker inspect --format '{{.State.Health.Status}}' "$container")
    if [ "$after" -gt "$before" ] && [ "$status" = healthy ]; then
        echo "AFTER CRASH: restart_count=$after; health=$status"
        curl -fsS --max-time 5 http://127.0.0.1:5000/health
        echo
        echo 'AUTOMATIC RESTART CHECK: PASSED'
        exit 0
    fi
    sleep 2
done
echo 'AUTOMATIC RESTART CHECK: FAILED' >&2
exit 1
