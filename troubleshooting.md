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


## Entry 5 / 2026-09-13 / 18:00
- Symptom: NGINX container had direct network access to internal database/cache containers (`ping postgres` succeeded), and internal ports 15432 and 16379 were bound to host interfaces in `docker-compose.yml`.
- Hypothesis: NGINX is attached to both `frontend` and `backend` networks, violating tier segregation; Postgres and Redis have unnecessary host port mappings.
- Command or test: Ran `docker compose exec nginx ping -c 1 postgres` (succeeded with 0% packet loss) and inspected `docker-compose.yml` service port definitions.
- Actual output: Verified NGINX could directly route packets to Postgres on the internal subnet, bypassing the application layer. Confirmed `ports` directives existed for `postgres` and `redis`.
- Failed attempt and what changed your thinking: None; architecture specifications in TASK.md and `scripts/video_challenge.py` preflight checks directly flag NGINX backend membership and published database ports as violations.
- Root cause: `docker-compose.yml` assigned `networks: [frontend, backend]` to `nginx` instead of `[frontend]` only, and published ports `15432:5432` and `16379:6379`.
- Fix: Removed `backend` from `nginx.networks` in `docker-compose.yml`, keeping only `frontend`. Removed `ports` mappings from both `postgres` and `redis` services.
- Retest evidence: Recreated services with `docker compose up -d nginx postgres redis`. Ran `docker compose exec nginx ping -c 1 postgres` and `ping -c 1 redis`—both failed with name resolution errors (`bad address`). Verified `curl http://127.0.0.1:8080/ready` still returns 200 OK.
- Related commit: fix(network): isolate nginx to frontend network and unpublish database ports
- Remaining uncertainty: Need to fix persistence traps in Postgres (tmpfs) and Redis (appendonly disabled).


## Entry 6 / 2026-09-13 / 18:45
- Symptom: Database records inserted via `POST /records` disappeared after container recreation (`docker compose up -d --force-recreate postgres`), resetting to only initial seed data.
- Hypothesis: PostgreSQL data directory `/var/lib/postgresql/data` is mounted in volatile RAM (`tmpfs`), and the persistent named volume `postgres-data` is mapped to an unused path. Redis persistence is also disabled via command flags.
- Command or test: Inserted record with `curl -X POST http://127.0.0.1:8080/records -H "Content-Type: application/json" -d '{"title": "Test Persistence Record"}'` (assigned id 3). Recreated container with `docker compose up -d --force-recreate postgres` and ran `curl -s http://127.0.0.1:8080/records`.
- Actual output: Only initial seed records (id 1 and 2) were returned; record 3 was completely wiped. Confirmed `tmpfs: [/var/lib/postgresql/data]` and dummy volume `- postgres-data:/var/lib/postgresql/backup` in `docker-compose.yml`. Confirmed Redis command `--save "" --appendonly no`.
- Failed attempt and what changed your thinking: None; the data loss was directly reproduced by container recreation, confirming volatile in-memory storage.
- Root cause: (1) `docker-compose.yml` mounted `/var/lib/postgresql/data` onto `tmpfs` instead of the named volume `postgres-data`. (2) Redis command explicitly disabled snapshots and AOF persistence without volume attachment.
- Fix: In `docker-compose.yml`, mapped `postgres-data:/var/lib/postgresql/data` and removed the `tmpfs` directive. Updated Redis command to `["redis-server", "--appendonly", "yes"]`, attached named volume `redis-data:/data`, and declared `redis-data` in top-level `volumes`.
- Retest evidence: Recreated services with `docker compose up -d --force-recreate postgres redis`. Inserted `"title": "Permanent Record"` (id 3). Force-recreated the `postgres` container again. Queried `curl -s http://127.0.0.1:8080/records`; record 3 was successfully preserved.
- Related commit: fix(compose): fix postgres and redis data persistence volumes
- Remaining uncertainty: Need to address container security hardening (running as unprivileged user), restart policies, and resource limits.


## Entry 7 / 2026-09-13 / 19:10
- Symptom: Flask app containers ran as privileged `root` user (`whoami` returned `root`), configuration file was baked into the container image, containers lacked restart resilience (`restart: "no"`), and no resource constraints were enforced on services.
- Hypothesis: `Dockerfile` ended with `USER root` and a redundant `COPY config/app.env`; `docker-compose.yml` had disabled auto-restart policies and omitted `deploy.resources.limits`.
- Command or test: Checked `docker compose exec app-01 whoami` (output: `root`). Inspected `Dockerfile` lines 8-9 and `docker-compose.yml` service definitions.
- Actual output: Confirmed app was executing as UID 0 inside the container. Confirmed absence of resource limits and persistence policies in Compose.
- Failed attempt and what changed your thinking: None; direct static analysis and container process inspection confirmed these security and operational gaps.
- Root cause: (1) `Dockerfile` switched to `USER root` instead of utilizing the created unprivileged `app` user (UID 10001), and copied `config/app.env` into the build layer. (2) `docker-compose.yml` set `restart: "no"` and lacked CPU/memory resource ceilings.
- Fix: In `Dockerfile`, removed `COPY config/app.env /srv/app.env` and changed `USER root` to `USER app`. In `docker-compose.yml`, updated all services to `restart: unless-stopped` and added `deploy.resources.limits` (CPU and memory limits) across app, postgres, redis, and nginx.
- Retest evidence: Rebuilt and restarted containers with `docker compose up --build -d`. Ran `docker compose exec app-01 whoami` which returned `app` (UID 10001). Confirmed all containers returned to healthy state and `curl http://127.0.0.1:8080/ready` returned HTTP 200 OK.
- Related commit: fix(security): run app as unprivileged user and add compose restart and resource limits
- Remaining uncertainty: Environment repair phase (Part 2) is now fully complete; ready to proceed to Part 3 (test automation scripts, backup/restore, and CI pipeline).
