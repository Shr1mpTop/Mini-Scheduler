import asyncio
import time
import uuid
from typing import Dict, Literal, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


app = FastAPI(title="Mini Scheduler", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


OFFLINE_TIMEOUT_SECONDS = 10


class WorkerRegisterRequest(BaseModel):
    id: str = Field(..., min_length=1)
    cpu: float = Field(..., gt=0)
    mem: float = Field(..., gt=0)


class WorkerHeartbeatRequest(BaseModel):
    id: str = Field(..., min_length=1)
    cpu: Optional[float] = Field(default=None, gt=0)
    mem: Optional[float] = Field(default=None, gt=0)


class TaskCreateRequest(BaseModel):
    command: str = Field(..., min_length=1)
    cpu_required: float = Field(..., gt=0)
    mem_required: float = Field(..., gt=0)


class WorkerState(BaseModel):
    id: str
    total_cpu: float
    total_mem: float
    used_cpu: float
    used_mem: float
    status: Literal["ONLINE", "OFFLINE"]
    last_heartbeat: float


class TaskState(BaseModel):
    id: str
    command: str
    cpu_required: float
    mem_required: float
    status: Literal["PENDING", "RUNNING", "FAILED", "SUCCESS"]
    assigned_worker_id: Optional[str] = None
    created_at: float


cluster_nodes: Dict[str, WorkerState] = {}
tasks_db: Dict[str, TaskState] = {}


def refresh_worker_statuses() -> None:
    now = time.time()
    for worker in cluster_nodes.values():
        if now - worker.last_heartbeat > OFFLINE_TIMEOUT_SECONDS:
            worker.status = "OFFLINE"
        else:
            worker.status = "ONLINE"


@app.on_event("startup")
async def startup_background_tasks() -> None:
    async def offline_sweeper() -> None:
        while True:
            refresh_worker_statuses()
            await asyncio.sleep(1)

    asyncio.create_task(offline_sweeper())


@app.post("/api/workers/register")
async def register_worker(payload: WorkerRegisterRequest):
    now = time.time()
    existing = cluster_nodes.get(payload.id)

    if existing:
        existing.total_cpu = payload.cpu
        existing.total_mem = payload.mem
        existing.last_heartbeat = now
        existing.status = "ONLINE"
    else:
        cluster_nodes[payload.id] = WorkerState(
            id=payload.id,
            total_cpu=payload.cpu,
            total_mem=payload.mem,
            used_cpu=0,
            used_mem=0,
            status="ONLINE",
            last_heartbeat=now,
        )

    return {
        "message": "worker registered",
        "worker": cluster_nodes[payload.id],
    }


@app.post("/api/workers/heartbeat")
async def heartbeat_worker(payload: WorkerHeartbeatRequest):
    worker = cluster_nodes.get(payload.id)
    if worker is None:
        raise HTTPException(status_code=404, detail="worker not found")

    worker.last_heartbeat = time.time()
    worker.status = "ONLINE"

    if payload.cpu is not None:
        worker.total_cpu = payload.cpu
    if payload.mem is not None:
        worker.total_mem = payload.mem

    return {
        "message": "heartbeat received",
        "worker": worker,
    }


@app.get("/api/workers")
async def list_workers():
    refresh_worker_statuses()
    return {"workers": list(cluster_nodes.values())}


@app.post("/api/tasks")
async def create_task(payload: TaskCreateRequest):
    refresh_worker_statuses()

    task_id = str(uuid.uuid4())
    task = TaskState(
        id=task_id,
        command=payload.command,
        cpu_required=payload.cpu_required,
        mem_required=payload.mem_required,
        status="PENDING",
        created_at=time.time(),
    )

    online_workers = [w for w in cluster_nodes.values() if w.status == "ONLINE"]

    # First-Fit Bin Packing:
    # 1. 按当前内存中的节点顺序遍历。
    # 2. 找到第一个同时满足 CPU 和内存余量的 ONLINE 节点即分配。
    # 3. 立即预扣资源（used_cpu / used_mem）。
    #
    # 真实并发环境下必须做原子化保护，避免多个请求同时读到“足够资源”导致超发。
    # 常见做法：
    # - 单进程：使用 asyncio.Lock / threading.Lock 包裹“检查+预扣”临界区。
    # - 多进程/多实例：使用分布式锁（如 Redis Redlock）或基于数据库事务/行锁实现。
    assigned_worker: Optional[WorkerState] = None
    for worker in online_workers:
        free_cpu = worker.total_cpu - worker.used_cpu
        free_mem = worker.total_mem - worker.used_mem
        if free_cpu >= payload.cpu_required and free_mem >= payload.mem_required:
            worker.used_cpu += payload.cpu_required
            worker.used_mem += payload.mem_required
            assigned_worker = worker
            break

    if assigned_worker is None:
        task.status = "FAILED"
        tasks_db[task.id] = task
        return {
            "task_id": task.id,
            "status": "FAILED",
            "message": "insufficient cluster resources",
        }

    task.status = "RUNNING"
    task.assigned_worker_id = assigned_worker.id
    tasks_db[task.id] = task

    return {
        "task_id": task.id,
        "status": "RUNNING",
        "assigned_worker_id": assigned_worker.id,
        "worker_remaining": {
            "cpu": assigned_worker.total_cpu - assigned_worker.used_cpu,
            "mem": assigned_worker.total_mem - assigned_worker.used_mem,
        },
    }


@app.websocket("/api/tasks/{task_id}/logs")
async def task_logs(task_id: str, websocket: WebSocket):
    await websocket.accept()

    task = tasks_db.get(task_id)
    if task is None:
        await websocket.send_text(f"[{task_id}] task not found")
        await websocket.close(code=1008)
        return

    try:
        for i in range(1, 1001):
            await websocket.send_text(f"[{task_id}] log line {i:04d}: running {task.command}")
            await asyncio.sleep(0.01)

        task.status = "SUCCESS"

        if task.assigned_worker_id:
            worker = cluster_nodes.get(task.assigned_worker_id)
            if worker is not None:
                worker.used_cpu = max(0, worker.used_cpu - task.cpu_required)
                worker.used_mem = max(0, worker.used_mem - task.mem_required)

        await websocket.send_text(f"[{task_id}] SUCCESS")
        await websocket.close(code=1000)
    except WebSocketDisconnect:
        return


@app.get("/api/tasks")
async def list_tasks():
    return {"tasks": list(tasks_db.values())}


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    task = tasks_db.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return {"task": task}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)