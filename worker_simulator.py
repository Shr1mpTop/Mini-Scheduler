import argparse
import asyncio

import httpx


async def register_worker(client: httpx.AsyncClient, master_url: str, worker_id: str, cpu: float, mem: float) -> None:
    resp = await client.post(
        f"{master_url}/api/workers/register",
        json={"id": worker_id, "cpu": cpu, "mem": mem},
        timeout=5,
    )
    resp.raise_for_status()


async def heartbeat_loop(
    client: httpx.AsyncClient,
    master_url: str,
    worker_id: str,
    cpu: float,
    mem: float,
    interval: float,
) -> None:
    while True:
        try:
            resp = await client.post(
                f"{master_url}/api/workers/heartbeat",
                json={"id": worker_id, "cpu": cpu, "mem": mem},
                timeout=5,
            )
            resp.raise_for_status()
            print(f"[heartbeat] worker={worker_id} ok")
        except Exception as exc:
            print(f"[heartbeat] worker={worker_id} failed: {exc}")
        await asyncio.sleep(interval)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Mini Scheduler Worker Simulator")
    parser.add_argument("--master", default="http://127.0.0.1:8000", help="Master base URL")
    parser.add_argument("--id", default="worker-1", help="Worker ID")
    parser.add_argument("--cpu", type=float, default=4.0, help="Worker total CPU")
    parser.add_argument("--mem", type=float, default=8.0, help="Worker total MEM")
    parser.add_argument("--interval", type=float, default=3.0, help="Heartbeat interval seconds")
    args = parser.parse_args()

    async with httpx.AsyncClient() as client:
        await register_worker(client, args.master, args.id, args.cpu, args.mem)
        print(f"[register] worker={args.id} cpu={args.cpu} mem={args.mem} -> {args.master}")
        await heartbeat_loop(client, args.master, args.id, args.cpu, args.mem, args.interval)


if __name__ == "__main__":
    asyncio.run(main())