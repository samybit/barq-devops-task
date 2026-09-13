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


## Entry 3 / 2026-09-13 / 17:30
- Symptom: `app-01` and `app-02` remained stuck in `(unhealthy)` status in `docker compose ps`, and querying `/instance` returned duplicate identity `"instance_id": "app-01"` for both backends.
- Hypothesis: Container healthcheck is querying an invalid endpoint, and `app-02` environment has a copy-pasted `INSTANCE_ID`.
- Command or test: Checked container logs (`docker compose logs app-01`), which showed repeated `404 - GET /healthz`. Checked `docker-compose.yml` lines 12 and 59.
- Actual output: Confirmed healthcheck in `docker-compose.yml` was hitting `/healthz` (which does not exist in Flask API contract), causing `urllib` to fail and mark containers unhealthy. Confirmed `app-02` was configured with `INSTANCE_ID: "app-01"`.
- Failed attempt and what changed your thinking: None; both flaws were directly visible in container logs and Compose file.
- Root cause: (1) Healthcheck path mismatch (`/healthz` vs `/health`). (2) Duplicate `INSTANCE_ID: "app-01"` assigned to `app-02` in `docker-compose.yml`.
- Fix: In `docker-compose.yml`, updated healthcheck URL to `http://127.0.0.1:8080/health`, and changed `app-02` environment to `INSTANCE_ID: "app-02"`.
- Retest evidence: Ran `docker compose up -d app-01 app-02`. After interval, `docker compose ps` reports both containers as `Up (healthy)`. Ran 30 requests to `/instance` via NGINX, which balanced across `app-01` (17) and `app-02` (13).
- Related commit: fix(compose): fix app healthcheck route and assign distinct instance id
- Remaining uncertainty: Need to test database and Redis connectivity on `/ready`, `/records`, and `/counter`.


## Entry 4 / 2026-09-13 / 17:42
- Symptom: `curl -i http://127.0.0.1:8080/ready` returned `HTTP/1.1 503 SERVICE UNAVAILABLE` with `{"dependencies":{"postgres":"unavailable","redis":"unavailable"},"status":"degraded"}`.
- Hypothesis: Configuration in `config/app.env` contains invalid connection URLs (wrong ports and/or credentials) for PostgreSQL and Redis.
- Command or test: Inspected `config/app.env` and compared against database credentials in `docker-compose.yml`. Checked `DATABASE_URL` and `REDIS_URL`.
- Actual output: `DATABASE_URL` specified port 5433 (Postgres listens on 5432) and password ending in `7qN2vK8d` (while Compose sets `7qN2vK8c`). `REDIS_URL` specified port 6380 (while Redis listens on 6379).
- Failed attempt and what changed your thinking: None; direct cross-reference of `config/app.env` with service configurations in `docker-compose.yml` exposed the typos.
- Root cause: (1) Typo in database password (`7qN2vK8d` vs `7qN2vK8c`). (2) Postgres port mismatch (`5433` vs standard container port `5432`). (3) Redis port mismatch (`6380` vs standard container port `6379`) in `config/app.env`.
- Fix: Updated `config/app.env` with `DATABASE_URL=postgresql://barq_app:BarqLabOnly_7qN2vK8c@postgres:5432/barq_tasks` and `REDIS_URL=redis://redis:6379/0`.
- Retest evidence: Restarted app containers (`docker compose up -d app-01 app-02`). `curl -i http://127.0.0.1:8080/ready` returned `HTTP/1.1 200 OK` with both dependencies reported as `ready`. `curl -s http://127.0.0.1:8080/records` returned seeded records from PostgreSQL. `curl -s http://127.0.0.1:8080/counter` successfully incremented and returned Redis counter values.
- Related commit: fix(config): correct postgres and redis credentials and port configs
- Remaining uncertainty: Need to inspect network segregation, exposed host ports on database/redis, persistence configuration (volumes/tmpfs), and container hardening.
