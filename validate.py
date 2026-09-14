#!/usr/bin/env python3
import argparse
import json
import socket
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request(url, method="GET", data=None):
    body = json.dumps(data).encode("utf-8") if data else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = Request(url, data=body, headers=headers, method=method)
    with urlopen(req, timeout=5) as res:
        content = res.read().decode("utf-8")
        return res.status, json.loads(content) if content else {}


def wait_for_ready(base_url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            status, body = request(f"{base_url}/ready")
            if status == 200 and body.get("status") == "ready":
                return True
        except (URLError, ConnectionError, HTTPError):
            pass
        time.sleep(2)
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8090")
    args = parser.parse_args()
    base_url = args.url.rstrip("/")

    # 1. Bounded readiness wait
    if not wait_for_ready(base_url):
        print("[FAIL] Stack did not become ready in time")
        sys.exit(1)

    errors = []

    # 2. Endpoint checks
    try:
        assert request(f"{base_url}/")[0] == 200
        print("[PASS] GET /")
    except Exception as e:
        errors.append(f"GET / failed: {e}")

    try:
        assert request(f"{base_url}/health")[1].get("status") == "alive"
        print("[PASS] GET /health")
    except Exception as e:
        errors.append(f"GET /health failed: {e}")

    try:
        deps = request(f"{base_url}/ready")[1].get("dependencies", {})
        assert deps.get("postgres") == "ready" and deps.get("redis") == "ready"
        print("[PASS] GET /ready (postgres & redis ready)")
    except Exception as e:
        errors.append(f"GET /ready failed: {e}")

    # 3. Backend load balancing
    instances = set()
    for _ in range(16):
        try:
            instances.add(request(f"{base_url}/instance")[1].get("instance_id"))
        except Exception:
            pass
    if {"app-01", "app-02"}.issubset(instances):
        print(f"[PASS] Load balancing verified: {instances}")
    else:
        errors.append(f"Missing expected backends: {instances}")

    # 4. Database write & read
    title = f"Task-{int(time.time())}"
    try:
        post_status, post_body = request(f"{base_url}/records", method="POST", data={"title": title})
        assert post_status == 201 and post_body.get("record", {}).get("title") == title
        get_status, get_body = request(f"{base_url}/records")
        assert any(r.get("title") == title for r in get_body.get("records", []))
        print("[PASS] POST & GET /records")
    except Exception as e:
        errors.append(f"Database records check failed: {e}")

    # 5. Redis counter increment
    try:
        c1 = request(f"{base_url}/counter")[1].get("counter", 0)
        c2 = request(f"{base_url}/counter")[1].get("counter", 0)
        assert c2 > c1
        print(f"[PASS] GET /counter ({c1} -> {c2})")
    except Exception as e:
        errors.append(f"Redis counter check failed: {e}")

    # 6. Prohibited host ports check
    for port in (5432, 15432, 6379, 16379):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                errors.append(f"Port {port} is unexpectedly open on host!")
            else:
                print(f"[PASS] Port {port} blocked")

    if errors:
        print("\nValidation failures:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    print("\nAll validation checks passed successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()
