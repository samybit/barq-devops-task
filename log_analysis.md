# Log analysis

Use all three supplied logs. Answer every question with commands/scripts and actual output.

1. What UTC interval is covered? How many valid, malformed and duplicate lines are in each file?

**Answer:**
- UTC Interval:
  - `access.log` & `application.log`: 2026-08-20 11:00:00 UTC to 11:29:57 UTC (~30 minutes)
  - `error.log`: 2026-08-20 11:05:02 UTC to 11:30:00 UTC (~25 minutes)
- Line Counts:
  - `access.log`: 726 total lines (725 valid, 1 malformed, 5 duplicates).
  - `application.log`: 730 total lines (729 valid, 1 malformed, 2 duplicates).
  - `error.log`: 68 total text lines (0 malformed, 0 duplicates).

**Commands used:**
```bash
head -n 1 logs/access.log | jq -r .timestamp && tail -n 1 logs/access.log | jq -r .timestamp
head -n 1 logs/error.log && tail -n 1 logs/error.log

wc -l logs/*.log

jq -c -R 'try fromjson catch "BAD"' logs/access.log | grep -n "BAD"
jq -c -R 'try fromjson catch "BAD"' logs/application.log | grep -n "BAD"

sort logs/access.log | uniq -d | wc -l
sort logs/application.log | uniq -d | wc -l
sort logs/error.log | uniq -d | wc -l
```

2. How many distinct client requests occurred? How did you deduplicate and avoid counting retries twice?

**Answer:**
- Distinct client requests: 720
- Deduplication method: Filtered valid JSON lines in `access.log` and counted unique `request_id` values (725 valid lines − 5 duplicate lines = 720 distinct requests).
- Avoiding counting retries twice: When NGINX retries an upstream, it logs a single client line with comma-separated upstreams (e.g. `upstream: "ip1, ip2"`). Deduplicating by `request_id` ensures each request is counted only once.

**Command used:**
```bash
jq -R 'fromjson? | select(. != null) | .request_id' logs/access.log | sort -u | wc -l
```

3. What are the final client status counts and error rate? State your denominator.

**Answer:**
- Denominator: 720 distinct client requests.
- Status counts:
  - 200 OK: 615
  - 404 Not Found: 10
  - 502 Bad Gateway: 40
  - 503 Service Unavailable: 47
  - 504 Gateway Timeout: 8
- Error rate:
  - Server errors (5xx): 95 / 720 (13.19%)
  - Total non-200: 105 / 720 (14.58%)

**Command used:**
```bash
jq -Rr 'fromjson? | select(. != null) | "\(.request_id) \(.status)"' logs/access.log | sort -u -k1,1 | awk '{print $2}' | sort | uniq -c
```

4. Which paths, time windows and backends account for the failures?

**Answer:**
- Paths:
  - / : 10 errors (502)
  - /health: 10 errors (502)
  - /ready: 23 errors (503)
  - /counter: 26 errors (10 of 502, 16 of 503)
  - /records: 26 errors (10 of 502, 8 of 503, 8 of 504)
  - /missing: 10 (404 route checks)
- Time windows:
  - 11:05 - 11:10 UTC: 40 errors of 502 (app-02 down)
  - 11:12 - 11:15 UTC: 23 errors of 503 (Redis timeouts)
  - 11:15 - 11:20 UTC: 8 errors of 503 (Redis timeouts)
  - 11:20 - 11:25 UTC: 16 errors of 503 (PostgreSQL password failure)
  - 11:25 - 11:30 UTC: 8 errors of 504 (upstream timeout on /records)
- Backends:
  - app-01 (172.23.0.11:8080): 27 errors (23 of 503, 4 of 504)
  - app-02 (172.23.0.12:8080): 68 errors (40 of 502, 24 of 503, 4 of 504)

**Commands used:**
```bash
jq -Rr 'fromjson? | select(. != null and .status >= 400) | "\(.path) \(.status)"' logs/access.log | sort | uniq -c

jq -Rr 'fromjson? | select(. != null and .status >= 400) | "\(.timestamp[11:16]) \(.status)"' logs/access.log | sort | uniq -c

jq -Rr 'fromjson? | select(. != null and .status >= 400) | "\(.upstream) \(.status)"' logs/access.log | sort | uniq -c
```

5. What are the median and p95 client latencies? State the percentile method and units.

**Answer:**
- Units: milliseconds
- Median: 54 ms
- p95: 2001 ms
- Percentile method: Nearest-rank method on 720 sorted latencies (median = row 360, p95 = row 684).

**Command used:**
```bash
jq -Rr 'fromjson? | select(. != null) | "\(.request_id) \(.request_time)"' logs/access.log | sort -u -k1,1 | awk '{print $2}' | sort -n | sed -n '360p;684p'
```

6. Which requests retried upstream? How many succeeded after retrying?

**Answer:**
- Requests that retried: 19 requests (lab-000124, lab-000130, lab-000136, lab-000142, lab-000148, lab-000154, lab-000160, lab-000166, lab-000172, lab-000178, lab-000184, lab-000190, lab-000196, lab-000202, lab-000208, lab-000214, lab-000220, lab-000226, lab-000232).
- How many succeeded: 19 / 19 (100% succeeded).

**Command used:**
```bash
jq -Rr 'fromjson? | select(. != null and (.upstream | contains(","))) | "\(.request_id) \(.upstream_status) -> \(.status)"' logs/access.log

jq -Rr 'fromjson? | select(. != null and (.upstream | contains(","))) | .request_id' logs/access.log | wc -l

jq -Rr 'fromjson? | select(. != null and (.upstream | contains(","))) | .status' logs/access.log | sort | uniq -c
```

7. Build an incident timeline using evidence from access, error AND application logs.

**Answer:**
- 11:00 - 11:05 UTC (Normal): Healthy baseline. Both app-01 and app-02 serve traffic with 200 OK.
- 11:05 - 11:10 UTC (app-02 down): NGINX error.log shows "connect() failed (111: Connection refused)" to app-02. 40 requests fail with 502, while 19 requests retry to app-01 and succeed.
- 11:12 - 11:15 UTC (Redis timeout): application.log shows 31 dependency_error events with Redis TimeoutError. /ready and /counter return 503.
- 11:20 - 11:22 UTC (Postgres password error): application.log shows 16 dependency_error events with Postgres InvalidPassword. /ready and /records return 503.
- 11:25 - 11:27 UTC (Upstream read timeout): error.log shows 8 "upstream timed out" errors. /records returns 504 Gateway Timeout.
- 11:30 UTC (Incident end): error.log records log rotation notice.

8. Show one correlated failed request and one successful request. Include IDs and timestamps.

**Answer:**
- Successful request: lab-000002 (Timestamp: 2026-08-20T11:00:02.532Z)
  - access.log: status 200, upstream 172.23.0.12:8080, request_time 0.032s.
  - application.log: event http_request, instance app-02, status 200, duration 32ms.
  - error.log: (no error).

- Failed request: lab-000122 (Timestamp: 2026-08-20T11:05:02.503Z)
  - access.log: status 502, upstream 172.23.0.12:8080.
  - error.log: connect() failed (111: Connection refused) while connecting to upstream 172.23.0.12:8080.
  - application.log: (no entry, because connection refused before reaching Python).

9. Which errors appear to be proxy/connectivity issues versus dependency/application issues? What proves it?

**Answer:**
- Proxy / connectivity issues:
  - 502 Bad Gateway: NGINX error.log shows "Connection refused" to app-02. It never reached application.log, proving it failed at the TCP connection level.
  - 504 Gateway Timeout: NGINX error.log shows "upstream timed out" after 3 seconds while waiting for response headers.
- Dependency / application issues:
  - 503 Service Unavailable: Requests successfully reached Flask (logged in both access.log and application.log). application.log shows the Python exceptions (TimeoutError for Redis, InvalidPassword for Postgres), proving Flask handled the error and returned 503.

**Command used:**
```bash
grep "lab-000122" logs/error.log
grep "lab-000122" logs/application.log

grep "dependency_error" logs/application.log | head -n 2
```

10. What do the logs not prove? What would you check next in a running environment?

**Answer:**
- What the logs do not prove:
  - Why app-02 stopped responding.
  - Whether PostgreSQL data survives after container restart.
  - CPU, RAM, or disk usage of the containers.
  - Network isolation between containers.
- What to check next in a running environment:
  - Container status and exit codes.
  - Container logs.
  - Resource usage.
  - Network and volume setup.

## Commands / scripts
Included under each question.

## Results
- Total distinct requests: 720
- Total server errors (5xx): 95 (13.19%)
- Retries: 19 (100% recovered)
- Median latency: 54 ms | P95: 2001 ms

## Timeline and correlated examples
Answers 7 and 8.

## Conclusions and limits
Answers 9 and 10.
