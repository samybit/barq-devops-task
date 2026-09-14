# Technical decisions

## Decision 1: Base Image and Non-Root User
- Choice: Kept the provided `python:3.12-slim-bookworm` base image and changed `USER root` to `USER app` in the Dockerfile.
- Why: Running as root is a security risk; if the app is compromised, an attacker would have root access inside the container.
- Alternative: Using an Alpine image. Alpine is smaller, but often breaks when compiling C packages like `psycopg`.
- Trade-off: Debian slim is larger (~230MB vs ~50MB), but it runs reliably without build issues.
- Evidence / commit: `bff7071`
- Production improvement: Use multi-stage Docker builds to keep the final production image as small as possible.

## Decision 2: Separating Frontend and Backend Networks
- Choice: Separated containers into two Docker networks: `frontend` (NGINX and apps) and `backend` (apps, Postgres, and Redis).
- Why: NGINX only needs to route web traffic to the Flask apps; it should never have direct network access to the database or cache.
- Alternative: Putting all containers on a single default network.
- Trade-off: Requires declaring two networks in Compose and attaching the Flask containers to both.
- Evidence / commit: `9389d54`
- Production improvement: In cloud production (like AWS), place NGINX in a public subnet and databases in private subnets with security group rules.

## Decision 3: Postgres and Redis Data Persistence
- Choice: Mounted the named volume `postgres-data` to `/var/lib/postgresql/data` (removed `tmpfs`), and enabled Redis persistence (`--appendonly yes`) with `redis-data`.
- Why: The starter setup stored database files in RAM (`tmpfs`), so any container restart wiped all new records.
- Alternative: Keeping data purely in RAM or using host folder bind mounts.
- Trade-off: Writing changes to disk is slightly slower than pure RAM, but prevents data loss.
- Evidence / commit: `c98ddab`
- Production improvement: Use managed cloud services (like AWS RDS and ElastiCache) with automated daily backups.

## Decision 4: Separate Health and Readiness Endpoints
- Choice: Kept `/health` for Docker Compose process checks, and `/ready` for verifying database and Redis connections.
- Why: If the database is temporarily slow or restarting, we do not want Docker to restart the Flask apps in a reboot loop.
- Alternative: Combining everything into a single `/health` endpoint that checks all databases.
- Trade-off: Requires maintaining two different endpoints for different purposes.
- Evidence / commit: `3a0df8b` and `6672c1b`
- Production improvement: Add database query latency alerts to notify engineers if queries become slow.

## Decision 5: Restart Policies and Resource Limits
- Choice: Changed `restart: "no"` to `restart: unless-stopped`, and added CPU and memory limits to each service in Compose.
- Why: Ensures containers automatically recover after crashes or reboots, and prevents any single container from freezing the host machine.
- Alternative: Leaving restart disabled and container resources unconstrained.
- Trade-off: If traffic spikes unexpectedly, a container could be killed if it exceeds its 256MB memory limit.
- Evidence / commit: `bff7071`
- Production improvement: Set up monitoring (Prometheus and Grafana) to track container resource usage and alert before memory limits are reached.
