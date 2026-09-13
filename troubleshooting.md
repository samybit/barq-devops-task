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
