# AI usage disclosure

## 1. Incident Log Analysis
- Tool/model: Google Antigravity (Gemini Agent)
- Purpose: Reviewing historical incident logs (`access.log`, `error.log`, `app.log`) to correlate timestamps and error patterns.
- Files or decisions affected: `log_analysis.md`
- What you changed or rejected: Rejected complex Python helper scripts that hid the analysis logic. Decided to write transparent, reproducible native Linux commands (`grep`, `awk`, `jq`, `sort`, `uniq`) instead.
- How you independently verified it: Executed each shell one-liner manually in the terminal, verified the exact counts against raw log files, and cross-referenced timestamps.
- Related commit: `48aacf4`

## 2. Environment Debugging & Configuration
- Tool/model: Google Antigravity (Gemini Agent)
- Purpose: Assisting with diagnosing root causes for NGINX upstream errors, Flask loopback binding, healthcheck routes, and database connectivity.
- Files or decisions affected: `docker-compose.yml`, `nginx/nginx.conf`, `config/app.env`, `Dockerfile`, `troubleshooting.md`
- What you changed or rejected: Rejected making bulk multi-file edits; enforced one-by-one atomic bug fixes with isolated verification before each commit.
- How you independently verified it: Tested each fix locally (`docker compose up`, `curl http://127.0.0.1:8080/ready`, `whoami` inside container, checking persistence by restarting Postgres and querying records).
- Related commit: `91fb634`, `c92c9cb`, `3a0df8b`, `6672c1b`, `9389d54`, `c98ddab`, `bff7071`

## 3. Automation Scripts & CI Pipeline
- Tool/model: Google Antigravity (Gemini Agent)
- Purpose: Scaffolding test scripts (`validate.py`, `failure_test.py`, `backup.sh`, `restore.sh`) and GitHub Actions workflow (`ci.yml`).
- Files or decisions affected: `validate.py`, `failure_test.py`, `backup.sh`, `restore.sh`, `.github/workflows/ci.yml`
- What you changed or rejected: Rejected an initial 190-line verbose version of `validate.py` containing AI docstrings and robotic banners, rewriting it into a clean, concise 80-line version. Fixed a socket `TimeoutError` in `failure_test.py` caught during live testing. Explicitly pinned `ubuntu-24.04` in GitHub Actions to match my local WSL environment.
- How you independently verified it: Ran `python3 validate.py`, `python3 failure_test.py`, `./backup.sh`, and `./restore.sh` manually; pushed to GitHub and confirmed all steps passed in GitHub Actions with green status.
- Related commit: `970a932`, `2e9469a`, `47dec6d`, `94e2f5c`

## 4. Documentation & Architectural Decisions
- Tool/model: Google Antigravity (Gemini Agent)
- Purpose: Structuring technical decisions and security review templates according to task guidelines.
- Files or decisions affected: `decisions.md`, `security_review.md`
- What you changed or rejected: Rejected initial drafts containing artificial words; rewrote all bullet points into direct, simple sentences that reflect my actual understanding.
- How you independently verified it: Read through every decision and security finding, verifying that every commit hash and command corresponds to our actual repository history.
- Related commit: `556067f`, `edadd0b`
