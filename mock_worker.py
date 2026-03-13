import argparse
import json
import random
import threading
import time
import urllib.error
import urllib.request


def post_json(url: str, payload: dict, timeout: float = 5.0) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def run_worker(
    master: str,
    worker_id: str,
    cpu: float,
    mem: float,
    interval: float,
    jitter: float,
) -> None:
    register_url = f"{master}/api/workers/register"
    heartbeat_url = f"{master}/api/workers/heartbeat"

    try:
        post_json(register_url, {"id": worker_id, "cpu": cpu, "mem": mem})
        print(f"[register] {worker_id} cpu={cpu} mem={mem}")
    except Exception as exc:
        print(f"[register] {worker_id} failed: {exc}")

    while True:
        try:
            post_json(heartbeat_url, {"id": worker_id, "cpu": cpu, "mem": mem})
            print(f"[heartbeat] {worker_id} ok")
        except urllib.error.HTTPError as exc:
            print(f"[heartbeat] {worker_id} http_error={exc.code}")
        except Exception as exc:
            print(f"[heartbeat] {worker_id} failed: {exc}")

        next_interval = interval + random.uniform(-jitter, jitter)
        next_interval = max(0.5, next_interval)
        time.sleep(next_interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Mock one or many workers for Mini-Scheduler")
    parser.add_argument("--master", default="http://127.0.0.1:8000", help="Master base URL")
    parser.add_argument("--id", default="worker-1", help="Worker ID when count=1")
    parser.add_argument("--prefix", default="worker", help="Worker ID prefix when count>1")
    parser.add_argument("--count", type=int, default=1, help="How many workers to simulate")
    parser.add_argument("--cpu", type=float, default=4.0, help="Worker CPU cores")
    parser.add_argument("--mem", type=float, default=8.0, help="Worker memory (GB)")
    parser.add_argument("--interval", type=float, default=3.0, help="Heartbeat interval seconds")
    parser.add_argument("--jitter", type=float, default=0.3, help="Heartbeat jitter seconds")
    args = parser.parse_args()

    if args.count <= 1:
        run_worker(args.master, args.id, args.cpu, args.mem, args.interval, args.jitter)
        return

    threads = []
    for i in range(1, args.count + 1):
        worker_id = f"{args.prefix}-{i}"
        thread = threading.Thread(
            target=run_worker,
            args=(args.master, worker_id, args.cpu, args.mem, args.interval, args.jitter),
            daemon=True,
        )
        thread.start()
        threads.append(thread)

    print(f"started {args.count} mock workers -> {args.master}")
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()