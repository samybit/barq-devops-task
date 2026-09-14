# Evidence and submission index

- Repository URL: https://github.com/samybit/barq-devops-task
- Final commit: b9d37b0 (Final implementation commit from live video)
- Matching CI run: https://github.com/samybit/barq-devops-task/actions/runs/34885395404
- Continuous 12-18 minute video URL: https://drive.google.com/drive/folders/1EbS3azIYRPR2HnRUiPlfx3yglW5e3602?usp=sharing
- Challenge receipt ID: 3b3c4652078e440990cbe69afa17c02d
- Starting video commit: bf16cb8
- Later documentation-only commits, if any: Single post-video commit completing evidence index, video timestamps, and CI alignment for port 8090


---

## Requirement to Evidence Traceability Matrix

| Requirement | Primary File / Artifact | Git Commit | Video Timestamp | Description / Verification |
| :--- | :--- | :--- | :--- | :--- |
| **Clean Git Status & Baseline** | [`README.md`](../README.md), `docker-compose.yml` | `bf16cb8` | `00:08` | Demonstrated clean git working tree, starting commit `bf16cb8`, and all 5 healthy services (`app-01`, `app-02`, `nginx`, `postgres`, `redis`). |
| **Endpoint Contracts & Load Balancing** | [`nginx/nginx.conf`](../nginx/nginx.conf), [`app/server.py`](../app/server.py) | `bf16cb8` | `00:59` | Tested all required endpoints (`/`, `/health`, `/ready`, `/counter`, `/records`). Proved round-robin distribution between backends via `/instance`. |
| **High Availability & Fault Recovery** | [`failure_test.py`](../failure_test.py) | `2e9469a` | `03:24` | Stopped `app-01` to demonstrate zero full outage (`app-02` serving traffic); restarted `app-01` and proved self-healing return to the pool. |
| **Data Persistence Proof** | [`docker-compose.yml`](../docker-compose.yml) | `c98ddab` | `04:32` | Inserted a new record via POST `/records`, forced recreation of PostgreSQL container (`--force-recreate`), and verified record survived on disk (`postgres-data`). |
| **Automated Tests & Incident Analysis** | [`validate.py`](../validate.py), [`log_analysis.md`](../log_analysis.md) | `970a932`, `48aacf4` | `05:55` | Executed 11-step validation suite; ran failure resilience test; demonstrated incident log finding (HTTP 502 upstream connection errors). |
| **Recorded Lab Challenge** | [`video_challenge.sh`](../video_challenge.sh), [`.assessment/challenge.json`](../.assessment/challenge.json) | `bf16cb8` | `07:30` | Executed `./video_challenge.sh` live on screen (`Receipt: 3b3c4652078e440990cbe69afa17c02d`). Diagnosed runtime fault and restored service without `docker compose down`. |
| **Live Port Switch & 3rd Instance** | [`.env`](../.env), [`docker-compose.yml`](../docker-compose.yml), [`nginx/nginx.conf`](../nginx/nginx.conf) | `b9d37b0` | `09:14` | Switched public port to `8090`, added `app-03` service, and reconfigured NGINX upstream live. Demonstrated requests balanced across `app-01`, `app-02`, and `app-03`. |
| **On-Screen Git Commit & Push** | Git history, `origin/main` | `b9d37b0` | `13:05` | Showed `git diff`, performed commit `b9d37b0` directly on screen, pushed to remote repository, and displayed final on-screen commit hash. |
| **Architecture Diagram & Specs** | [`architecture.png`](../architecture.png), [`README.md`](../README.md) | `a08cd3a` | Docs Artifact | Complete architectural schematic representing 3-instance setup, dual network isolation (`frontend` / `backend` internal), volumes, and port 8090 ingress. |
| **Security Review & Hardening** | [`security_review.md`](../security_review.md), [`Dockerfile`](../Dockerfile) | `edadd0b`, `bff7071` | Docs Artifact | Documented 8 security findings and mitigations; non-root user `app` (UID 10001); removed embedded secrets; CPU/RAM limits; isolated DB networks. |
| **Architectural Decisions Log** | [`decisions.md`](../decisions.md) | `556067f` | Docs Artifact | Documented 5 architectural design decisions, trade-offs, rationale, and operational limits. |
| **Database Backup & Restore** | [`backup.sh`](../backup.sh), [`restore.sh`](../restore.sh) | `47dec6d` | Repository | Automated PostgreSQL snapshot and restore scripts verifying table data integrity and non-zero record count. |
| **AI Transparency Disclosure** | [`AI_USAGE.md`](../AI_USAGE.md) | `ed70d79` | Docs Artifact | Comprehensive disclosure of AI-assisted tasks, code review methodology, and independent human verifications. |
