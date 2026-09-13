#!/usr/bin/env python3
import json
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import urlopen

BASE_URL = "http://127.0.0.1:8080"
TARGET_SERVICE = "app-01"


def get_instance(timeout=3):
    try:
        with urlopen(f"{BASE_URL}/instance", timeout=timeout) as res:
            data = json.loads(res.read().decode("utf-8"))
            return res.status, data.get("instance_id")
    except HTTPError as e:
        return e.code, None
    except Exception:
        return 502, None


def docker_cmd(*args):
    return subprocess.run(["docker", *args], check=True, capture_output=True, text=True)


def main():
    # 1. Baseline check
    baseline_instances = set()
    for _ in range(10):
        status, inst = get_instance()
        if status == 200 and inst:
            baseline_instances.add(inst)
    print(f"Baseline backends: {', '.join(sorted(baseline_instances))}")
    if {"app-01", "app-02"} != baseline_instances:
        print("Error: baseline requires both app-01 and app-02 running", file=sys.stderr)
        sys.exit(1)

    try:
        # 2. Stop one backend
        print(f"Stopping {TARGET_SERVICE}...")
        docker_cmd("stop", TARGET_SERVICE)
        time.sleep(1)

        # 3. Measure traffic during downtime
        success_count = 0
        error_count = 0
        active_during_outage = set()

        for _ in range(10):
            status, inst = get_instance(timeout=3)
            if status == 200 and inst:
                success_count += 1
                active_during_outage.add(inst)
            else:
                error_count += 1
            time.sleep(0.1)

        print(f"Traffic during downtime (10 reqs): {success_count} ok, {error_count} errors (served by: {', '.join(active_during_outage)})")

        if success_count == 0 or TARGET_SERVICE in active_during_outage:
            print(f"Error: expected surviving backend to serve traffic without {TARGET_SERVICE}", file=sys.stderr)
            sys.exit(1)

    finally:
        # 4. Restore the stopped backend
        print(f"Starting {TARGET_SERVICE}...")
        docker_cmd("start", TARGET_SERVICE)

    # 5. Wait for recovery
    print(f"Waiting for {TARGET_SERVICE} to recover...")
    recovered_instances = set()
    timeout = 30
    start = time.time()

    while time.time() - start < timeout:
        status, inst = get_instance(timeout=3)
        if status == 200 and inst:
            recovered_instances.add(inst)
            if {"app-01", "app-02"}.issubset(recovered_instances):
                break
        time.sleep(1)

    print(f"Backends active: {', '.join(sorted(recovered_instances))}")
    if {"app-01", "app-02"}.issubset(recovered_instances):
        print("Failure test passed.")
        sys.exit(0)
    else:
        print(f"Error: {TARGET_SERVICE} did not recover in time", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
