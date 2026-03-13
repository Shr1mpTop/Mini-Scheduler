<template>
  <section class="space-y-4">
    <div>
      <h2 class="text-xl font-semibold text-slate-100">Cluster Heatmap</h2>
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
      <div
        v-for="node in workers"
        :key="node.id"
        :class="[
          'worker-card group relative aspect-square overflow-hidden rounded-2xl border bg-slate-900/75 p-4 transition-all duration-500 ease-out',
          pressureStyle(node).borderClass,
          node.status === 'OFFLINE'
            ? 'opacity-45 grayscale saturate-0'
            : 'hover:-translate-y-1 hover:shadow-2xl hover:shadow-cyan-900/30'
        ]"
      >
        <div class="absolute inset-0 opacity-25" :class="pressureStyle(node).bgClass" />

        <div class="relative flex h-full flex-col">
          <div class="mb-6 flex items-start justify-between">
            <div>
              <p class="text-xs uppercase tracking-wider text-slate-400">Worker</p>
              <p class="max-w-[160px] truncate text-lg font-semibold text-slate-100">{{ node.id }}</p>
            </div>
            <el-tag :type="node.status === 'ONLINE' ? 'success' : 'danger'" effect="dark">
              {{ node.status }}
            </el-tag>
          </div>

          <div class="flex flex-1 flex-col">
            <div class="mt-auto space-y-2">
              <div class="grid grid-cols-2 gap-2">
                <div class="rounded-xl border border-slate-700/70 bg-slate-950/45 p-1.5 transition-all duration-300 group-hover:border-cyan-400/40">
                  <p class="mb-1 text-center text-xs font-medium text-slate-300">CPU</p>
                  <div class="flex justify-center">
                    <el-progress
                      type="circle"
                      :percentage="cpuPercent(node)"
                      :width="140"
                      :stroke-width="10"
                      :color="usageColor(cpuPercent(node))"
                    />
                  </div>
                </div>

                <div class="rounded-xl border border-slate-700/70 bg-slate-950/45 p-1.5 transition-all duration-300 group-hover:border-cyan-400/40">
                  <p class="mb-1 text-center text-xs font-medium text-slate-300">MEM</p>
                  <div class="flex justify-center">
                    <el-progress
                      type="circle"
                      :percentage="memPercent(node)"
                      :width="140"
                      :stroke-width="10"
                      :color="usageColor(memPercent(node))"
                    />
                  </div>
                </div>
              </div>

              <div class="grid h-[92px] grid-cols-2 gap-2">
                <div class="rounded-xl border border-slate-700/70 bg-slate-950/45 px-2 py-1.5">
                  <div
                    class="rounded-lg border px-2 py-1 text-xs"
                    :class="[pressureStyle(node).textClass, pressureStyle(node).borderClass]"
                  >
                    压力等级：{{ pressureStyle(node).label }}
                  </div>
                  <p class="mt-1 text-xs text-slate-400">CPU: {{ node.used_cpu }} / {{ node.total_cpu }}</p>
                  <p class="text-xs text-slate-400">MEM: {{ node.used_mem }} / {{ node.total_mem }}</p>
                </div>

                <div class="rounded-xl border border-slate-700/70 bg-slate-950/45 px-2 py-1.5">
                  <p class="mb-1 text-[11px] text-slate-400">执行任务</p>
                  <template v-if="workerRunningTasks(node.id).length">
                    <p
                      v-for="task in workerRunningTasks(node.id).slice(0, 2)"
                      :key="task.id"
                      class="truncate text-[11px] text-cyan-300"
                      :title="`${task.id} | ${task.command}`"
                    >
                      {{ task.command }}
                    </p>
                    <p
                      v-if="workerRunningTasks(node.id).length > 2"
                      class="mt-1 text-[11px] text-slate-500"
                    >
                      +{{ workerRunningTasks(node.id).length - 2 }} 个任务
                    </p>
                  </template>
                  <p v-else class="text-[11px] text-slate-500">暂无运行任务</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import axios from 'axios'
import { onBeforeUnmount, onMounted, ref } from 'vue'

type Worker = {
  id: string
  total_cpu: number
  total_mem: number
  used_cpu: number
  used_mem: number
  status: 'ONLINE' | 'OFFLINE'
  last_heartbeat: number
}

type TaskItem = {
  id: string
  command: string
  status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED'
  assigned_worker_id?: string
}

const workers = ref<Worker[]>([])
const tasks = ref<TaskItem[]>([])
let timer: number | null = null

function usageColor(percent: number) {
  if (percent === 0) return '#3b82f6'
  if (percent <= 30) return '#22c55e'
  if (percent <= 60) return '#eab308'
  if (percent <= 85) return '#f97316'
  return '#ef4444'
}

function cpuPercent(node: Worker) {
  if (node.total_cpu <= 0) return 0
  return Math.min(100, Math.round((node.used_cpu / node.total_cpu) * 100))
}

function memPercent(node: Worker) {
  if (node.total_mem <= 0) return 0
  return Math.min(100, Math.round((node.used_mem / node.total_mem) * 100))
}

function pressurePercent(node: Worker) {
  return Math.max(cpuPercent(node), memPercent(node))
}

function pressureStyle(node: Worker) {
  if (node.status === 'OFFLINE') {
    return {
      label: 'OFFLINE',
      textClass: 'text-slate-300',
      borderClass: 'border-slate-600/60',
      bgClass: 'bg-slate-700'
    }
  }

  const percent = pressurePercent(node)

  if (percent === 0) {
    return {
      label: '无使用',
      textClass: 'text-blue-300',
      borderClass: 'border-blue-500/60',
      bgClass: 'bg-blue-500/30'
    }
  }
  if (percent <= 30) {
    return {
      label: '轻量',
      textClass: 'text-green-300',
      borderClass: 'border-green-500/60',
      bgClass: 'bg-green-500/30'
    }
  }
  if (percent <= 60) {
    return {
      label: '中',
      textClass: 'text-yellow-300',
      borderClass: 'border-yellow-500/60',
      bgClass: 'bg-yellow-500/30'
    }
  }
  if (percent <= 85) {
    return {
      label: '较重',
      textClass: 'text-orange-300',
      borderClass: 'border-orange-500/60',
      bgClass: 'bg-orange-500/30'
    }
  }
  return {
    label: '即将占满',
    textClass: 'text-red-300',
    borderClass: 'border-red-500/60',
    bgClass: 'bg-red-500/30'
  }
}

async function fetchWorkers() {
  try {
    const [workersRes, tasksRes] = await Promise.all([
      axios.get('http://127.0.0.1:8000/api/workers'),
      axios.get('http://127.0.0.1:8000/api/tasks')
    ])

    workers.value = workersRes.data.workers ?? []
    tasks.value = tasksRes.data.tasks ?? []
  } catch {
    workers.value = []
    tasks.value = []
  }
}

function workerRunningTasks(workerId: string) {
  return tasks.value.filter((task) => task.assigned_worker_id === workerId && task.status === 'RUNNING')
}

onMounted(() => {
  fetchWorkers()
  timer = window.setInterval(fetchWorkers, 2000)
})

onBeforeUnmount(() => {
  if (timer !== null) {
    clearInterval(timer)
    timer = null
  }
})
</script>

<style scoped>
.worker-card {
  animation: breathe 3.2s ease-in-out infinite;
}

@keyframes breathe {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-2px);
  }
}
</style>