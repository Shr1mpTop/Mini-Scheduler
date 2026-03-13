# Mini-Scheduler

轻量级分布式任务调度系统（演示版），包含：
- 后端调度核心：FastAPI + 内存状态管理
- 前端可视化控制台：Vue 3 + Vite + Tailwind + Element Plus
- 一键集群活化：9 Worker 自动注册心跳 + 自动提交任务循环

---

## 1. 项目目标

这个项目用于模拟一个小型计算集群的任务调度过程，重点验证：
- Worker 注册与心跳保活
- 基于资源余量的 First-Fit Bin Packing 调度
- 任务状态追踪（PENDING / RUNNING / SUCCESS / FAILED）
- 前端实时热力图与高频日志流渲染性能

---

## 2. 技术栈

### Backend
- Python 3
- FastAPI
- Uvicorn
- 内存状态（无数据库）

### Frontend
- Vue 3（Composition API）
- Vite
- Tailwind CSS
- Element Plus

---

## 3. 核心能力概览

### 3.1 Worker 管理
- Worker 通过 `POST /api/workers/register` 注册（`id/cpu/mem`）
- Worker 通过 `POST /api/workers/heartbeat` 上报心跳
- 超过 10 秒无心跳，节点自动标记为 `OFFLINE`

### 3.2 任务调度
- 用户通过 `POST /api/tasks` 提交任务（`command/cpu_required/mem_required`）
- 调度器过滤离线节点后按 First-Fit 选择第一个可容纳节点
- 分配成功后立即预扣资源，避免虚假可用容量

### 3.3 任务状态追踪
- 状态流：`PENDING -> RUNNING -> SUCCESS/FAILED`
- 接口：
	- `GET /api/tasks`（任务列表）
	- `GET /api/tasks/{task_id}`（任务详情）

### 3.4 高频日志流
- `WS /api/tasks/{task_id}/logs`
- 每 10ms 推送 1 条日志，总计 1000 条
- 结束推送 `SUCCESS` 并关闭连接

### 3.5 前端性能优化（日志）
- WebSocket 消息先写入普通数组 buffer
- 每 100ms 批量刷入响应式数据
- `nextTick + requestAnimationFrame` 自动滚动到底部
- 用户手动上滚时暂停自动滚动，回到底部后恢复

### 3.6 可视化热力图
- Worker 卡片 1:1 正方形，3 列布局
- 双环形图展示 CPU/MEM 占用
- 压力等级颜色：蓝/绿/黄/橙/红
- OFFLINE 卡片灰化处理
- 卡片显示当前运行任务摘要

### 3.7 一键模拟集群（无需手动跑脚本）
- 前端按钮直接调用后端：
	- `POST /api/simulator/start`
	- `POST /api/simulator/stop`
	- `GET /api/simulator/status`
- 启动后会运行 `cluster_simulator.py`：
	- 自动创建 9 个 Worker
	- 周期性心跳
	- 随机任务提交
	- 持续循环，让页面实时“活起来”

---

## 4. 目录结构

```
Mini-Scheduler/
├── main.py
├── cluster_simulator.py
├── mock_worker.py
├── worker_simulator.py
├── package.json
├── index.html
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
└── src/
		├── main.ts
		├── style.css
		├── App.vue
		└── components/
				├── Heatmap.vue
				└── LiveLogModal.vue
```

---

## 5. 快速启动

### 5.1 启动后端

```bash
pip install fastapi uvicorn
python main.py
```

后端地址：`http://127.0.0.1:8000`  
接口文档：`http://127.0.0.1:8000/docs`

### 5.2 启动前端

```bash
npm install
npm run dev
```

前端地址：`http://127.0.0.1:5173`

---

## 6. 推荐演示流程（3 分钟）

1. 打开前端页面，点击“启动9节点模拟”
2. 观察热力图：节点上线、资源占用开始动态变化
3. 在“提交任务”区域手动提交任务
4. 在任务列表点击 `RUNNING` 任务“查看日志”
5. 观察日志高频滚动、任务最终成功、资源回收

---

## 7. 接口清单

### Worker
- `POST /api/workers/register`
- `POST /api/workers/heartbeat`
- `GET /api/workers`

### Task
- `POST /api/tasks`
- `GET /api/tasks`
- `GET /api/tasks/{task_id}`
- `WS /api/tasks/{task_id}/logs`

### Simulator
- `POST /api/simulator/start`
- `POST /api/simulator/stop`
- `GET /api/simulator/status`

---

## 8. 说明

- 当前为演示型实现，状态存储在内存中，服务重启会丢失。
- 生产场景建议引入：持久化存储、分布式锁、认证鉴权、任务重试与告警。