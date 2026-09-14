# Security and production-readiness review

## 1. Secrets Baked into Docker Image Layers (Secrets)
- Risk and evidence: The starter Dockerfile had `COPY config/app.env /srv/app.env`, embedding database credentials directly into the image layers.
- Impact: Anyone with access to the built image (via `docker history` or container registries) could extract the database password.
- Implemented fix / commit: Removed `COPY config/app.env` from `Dockerfile` in commit `bff7071`. Credentials are now injected at runtime via Docker Compose `env_file`.
- Production follow-up: In production, inject secrets using secure secret managers (like AWS Secrets Manager, HashiCorp Vault, or Docker Secrets) rather than plaintext files.
- How to verify: Run `docker history barq-assessment-app-01:latest` and confirm `app.env` is never copied into any layer.

## 2. Containers Running as Root (Container User)
- Risk and evidence: The starter Dockerfile ended with `USER root`, running the Flask process with full root privileges.
- Impact: If an attacker exploited a web vulnerability in Flask or an imported library, they would gain root privileges inside the container.
- Implemented fix / commit: Changed `USER root` to `USER app` (UID 10001) in `Dockerfile` (commit `bff7071`).
- Production follow-up: Add a Dockerfile linter (like Hadolint) to CI to automatically block Dockerfiles that run as root.
- How to verify: Run `docker compose exec app-01 whoami` (returns `app`).

## 3. Database and Cache Ports Exposed to Host (Ports)
- Risk and evidence: `docker-compose.yml` published ports `15432:5432` and `16379:6379` to the host interfaces.
- Impact: Any user or process on the host machine could bypass NGINX and connect directly to PostgreSQL or Redis.
- Implemented fix / commit: Removed the `ports` directives from `postgres` and `redis` services in `docker-compose.yml` (commit `9389d54`).
- Production follow-up: Configure cloud firewall rules (Security Groups) to prevent external ingress to database subnets.
- How to verify: Run `python3 validate.py`, which asserts ports 5432, 15432, 6379, and 16379 are closed on the host.

## 4. Ingress Proxy Attached to Internal Database Network (Networks)
- Risk and evidence: NGINX was attached to both `frontend` and `backend` networks in `docker-compose.yml`.
- Impact: If NGINX were compromised, an attacker would have direct network access to the database and cache.
- Implemented fix / commit: Restricted NGINX to `networks: [frontend]` in `docker-compose.yml` (commit `9389d54`).
- Production follow-up: In cloud environments, place NGINX in a public DMZ subnet and the databases in a strictly isolated private subnet.
- How to verify: Run `docker compose exec nginx ping -c 1 postgres` and verify the host cannot be reached or resolved.

## 5. Volatile In-Memory Database Mount (Persistence & Backup)
- Risk and evidence: PostgreSQL had `tmpfs: [/var/lib/postgresql/data]`, and Redis had persistence disabled with `--save ""` and `--appendonly no`.
- Impact: Any container restart completely wiped all new database records and counter increments.
- Implemented fix / commit: Mapped named volume `postgres-data` to `/var/lib/postgresql/data` (commit `c98ddab`), enabled Redis AOF with `redis-data`, and created automated `backup.sh` and `restore.sh` scripts (commit `47dec6d`).
- Production follow-up: Configure automated daily database dumps to encrypted cloud object storage (e.g. AWS S3).
- How to verify: Insert a record via `POST /records`, run `docker compose up -d --force-recreate postgres`, and confirm the record still exists with `GET /records`.

## 6. Container Image Vulnerabilities (Image Scanning)
- Risk and evidence: Base OS packages and Python dependencies can contain known CVE security vulnerabilities.
- Impact: Outdated packages could allow remote attackers to exploit known security flaws.
- Implemented fix / commit: Pinned base images with sha256 digests and added automated Trivy vulnerability scanning in `.github/workflows/ci.yml`.
- Production follow-up: Set up an automated dependency bot (like Dependabot or Renovate) to automatically open pull requests when security patches are released.
- How to verify: Check the GitHub Actions CI log under the step "Scan container image for vulnerabilities (Trivy)".

## 7. Lack of Container Resource Limits (Resource Limits)
- Risk and evidence: The starter Compose file defined no CPU or memory boundaries for any service.
- Impact: A memory leak or traffic surge in Flask could consume 100% of host RAM, freezing the host or crashing other services.
- Implemented fix / commit: Added `deploy.resources.limits` (0.25–0.50 CPU, 128MB–256MB RAM) for all services in `docker-compose.yml` (commit `bff7071`).
- Production follow-up: Set up Prometheus and Grafana alerts to notify engineers when a container reaches 80% of its memory limit.
- How to verify: Run `docker inspect app-01 --format '{{.HostConfig.Memory}}'` and verify it returns `268435456` (256MB).

## 8. Missing Container Auto-Recovery (Availability & Health)
- Risk and evidence: The starter Compose file had `restart: "no"`, and healthchecks queried a non-existent `/healthz` route.
- Impact: Containers remained marked unhealthy, and if a process crashed, it stayed dead until manual intervention.
- Implemented fix / commit: Corrected healthcheck to `/health` (commit `3a0df8b`), updated restart policy to `restart: unless-stopped` (commit `bff7071`), and verified high-availability failover in `failure_test.py` (commit `2e9469a`).
- Production follow-up: Deploy across multiple availability zones behind a load balancer with auto-scaling groups.
- How to verify: Run `python3 failure_test.py` to stop `app-01`, confirm `app-02` keeps serving requests, and verify `app-01` automatically recovers.
