import argparse
import json
import random
import time
import urllib.error
import urllib.request


WORKER_PROFILES = [
    {"id": "sim-01", "cpu": 4.0, "mem": 8.0},
    {"id": "sim-02", "cpu": 4.0, "mem": 8.0},
    {"id": "sim-03", "cpu": 8.0, "mem": 16.0},
    {"id": "sim-04", "cpu": 8.0, "mem": 16.0},
    {"id": "sim-05", "cpu": 2.0, "mem": 4.0},
    {"id": "sim-06", "cpu": 2.0, "mem": 4.0},
    {"id": "sim-07", "cpu": 6.0, "mem": 12.0},
    {"id": "sim-08", "cpu": 6.0, "mem": 12.0},
    {"id": "sim-09", "cpu": 3.0, "mem": 6.0},
]


TASK_LIBRARY = [
    {"command": "python etl.py", "cpu_required": 0.5, "mem_required": 1.0},
    {"command": "python feature_job.py", "cpu_required": 1.0, "mem_required": 2.0},
    {"command": "python train_small.py", "cpu_required": 2.0, "mem_required": 4.0},
    {"command": "python report_task.py", "cpu_required": 0.8, "mem_required": 1.5},
    {"command": "python stream_consumer.py", "cpu_required": 1.2, "mem_required": 2.5},
]


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


def register_workers(master: str) -> None:
    url = f"{master}/api/workers/register"
    for worker in WORKER_PROFILES:
        try:
            post_json(url, worker)
            print(f"[register] {worker['id']} cpu={worker['cpu']} mem={worker['mem']}")
        except Exception as exc:
            print(f"[register] {worker['id']} failed: {exc}")


def heartbeat_workers(master: str) -> None:
    url = f"{master}/api/workers/heartbeat"
    for worker in WORKER_PROFILES:
        payload = {"id": worker["id"], "cpu": worker["cpu"], "mem": worker["mem"]}
        try:
            post_json(url, payload)
        except Exception as exc:
            print(f"[heartbeat] {worker['id']} failed: {exc}")


def submit_random_tasks(master: str, submit_count: int) -> None:
    url = f"{master}/api/tasks"
    for _ in range(submit_count):
        payload = random.choice(TASK_LIBRARY)
        try:
            result = post_json(url, payload)
            print(
                f"[task] {payload['command']} cpu={payload['cpu_required']} mem={payload['mem_required']} -> {result.get('status')}"
            )
        except urllib.error.HTTPError as exc:
            print(f"[task] submit http_error={exc.code}")
        except Exception as exc:
            print(f"[task] submit failed: {exc}")


def run(master: str, step_interval: float) -> None:
    print(f"cluster simulator start -> {master}")
    register_workers(master)
    cycle = 0

    while True:
        cycle += 1
        print(f"\n==== cycle {cycle} start ====")
        register_workers(master)

        for _ in range(10):
            heartbeat_workers(master)
            submit_random_tasks(master, submit_count=random.randint(1, 3))
            time.sleep(step_interval)

        print(f"==== cycle {cycle} done, restart next cycle ====\n")
        time.sleep(1.0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Mini Scheduler 9-Worker Cluster Simulator")
    parser.add_argument("--master", default="http://127.0.0.1:8000", help="Master base url")
    parser.add_argument("--step-interval", type=float, default=1.2, help="Seconds between simulation steps")
    args = parser.parse_args()

    run(args.master, args.step_interval)


if __name__ == "__main__":
    main()