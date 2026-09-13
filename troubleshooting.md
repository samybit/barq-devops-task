# Troubleshooting journal

Keep chronological entries. Copy this block for each meaningful investigation.

## Entry / date / time
- Symptom:
- Hypothesis:
- Command or test:
- Actual output:
- Failed attempt and what changed your thinking:
- Root cause:
- Fix:
- Retest evidence:
- Related commit:
- Remaining uncertainty:

Do not fabricate a failed attempt just to fill the template. Record actual attempts.

## Entry 1 / 2026-09-13 / 15:16
- Symptom: Running `curl -i http://127.0.0.1:8080/health` returned `curl: (56) Recv failure: Connection reset by peer`.
- Hypothesis: The NGINX container port in `docker-compose.yml` does not match the listening port configured in `nginx.conf`.
- Command or test: Inspected `docker compose ps` (saw port mapping `127.0.0.1:8080->81/tcp`) and checked line 14 of `nginx/nginx.conf` (saw `listen 80;`).
- Actual output: Confirmed host port 8080 was forwarded to container port 81, where nothing was listening.
- Failed attempt and what changed your thinking: None; port mismatch was visible directly from `docker compose ps` output.
- Root cause: Line 63 in `docker-compose.yml` mapped host port 8080 to container port 81 instead of 80.
- Fix: Changed `docker-compose.yml` line 63 from `127.0.0.1:${PUBLIC_PORT:-8080}:81` to `127.0.0.1:${PUBLIC_PORT:-8080}:80`.
- Retest evidence: Ran `docker compose up -d nginx` and re-tested with `curl -i http://127.0.0.1:8080/health`. NGINX now answers with `HTTP/1.1 502 Bad Gateway (Server: nginx/1.28.3)`, proving traffic successfully reaches NGINX.
- Related commit: fix(compose): align nginx host port mapping to container port 80
- Remaining uncertainty: NGINX returns 502 Bad Gateway because upstream Flask applications are currently unreachable or unhealthy.


## Entry 2 / 2026-09-13 / 16:06
- Symptom: `curl -i http://127.0.0.1:8080/health` returned `HTTP/1.1 502 Bad Gateway`.
- Hypothesis: NGINX cannot reach upstream Flask apps due to upstream port mismatch and/or app listening on loopback.
- Command or test: Ran `docker compose logs nginx` and saw `connect() failed (111: Connection refused) ... upstream: "http://...:8081/health"`. Tested inside container `app-01` via `urllib` on `127.0.0.1:8080`, which succeeded (200 OK), confirming the app was only listening internally on loopback.
- Actual output: Confirmed `nginx.conf` was routing `app-01` to port 8081 (instead of 8080), and `docker-compose.yml` had `APP_HOST: "127.0.0.1"`, preventing external Docker network connections from NGINX.
- Failed attempt and what changed your thinking: Fixing port 8081 in `nginx.conf` alone still returned 502 Bad Gateway. Inspecting the container logs revealed that Flask was bound to `127.0.0.1`, which prompted changing `APP_HOST` to `0.0.0.0`.
- Root cause: (1) `nginx/nginx.conf` mapped `app-01:8081` instead of `8080`. (2) `docker-compose.yml` set `APP_HOST: "127.0.0.1"` instead of `0.0.0.0`.
- Fix: Changed `server app-01:8081` to `server app-01:8080` in `nginx/nginx.conf`, and changed `APP_HOST: "127.0.0.1"` to `APP_HOST: "0.0.0.0"` in `docker-compose.yml`.
- Retest evidence: Reloaded NGINX and restarted app containers. `curl -i http://127.0.0.1:8080/health` now returns `HTTP/1.1 200 OK` with `{"instance_id":"app-01","service":"barq-api","status":"alive","version":"2.0.0"}`.
- Related commit: fix(routing): correct nginx upstream port and bind flask to 0.0.0.0
- Remaining uncertainty: Need to verify if `app-02` can also receive traffic, and check database/cache dependencies on `/ready`.
