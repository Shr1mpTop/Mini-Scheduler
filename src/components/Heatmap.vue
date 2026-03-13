<template>
  <section class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-xl font-semibold text-slate-100">Cluster Heatmap</h2>
      <el-tag type="info" effect="dark">每 2 秒自动刷新</el-tag>
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      <div
        v-for="node in workers"
        :key="node.id"
        :class="[
          'rounded-xl border border-slate-700 bg-slate-900/70 p-4 shadow-lg shadow-cyan-900/20 transition',
          node.status === 'OFFLINE' ? 'opacity-50 grayscale' : 'hover:border-cyan-400/60'
        ]"
      >
        <div class="mb-3 flex items-center justify-between">
          <div>
            <p class="text-sm text-slate-400">Worker</p>
            <p class="font-semibold text-slate-100">{{ node.id }}</p>
          </div>
          <el-tag :type="node.status === 'ONLINE' ? 'success' : 'danger'" effect="dark">
            {{ node.status }}
          </el-tag>
        </div>

        <div class="space-y-3">
          <div>
            <div class="mb-1 flex justify-between text-xs text-slate-400">
              <span>CPU</span>
              <span>{{ cpuPercent(node) }}%</span>
            </div>
            <el-progress
              :percentage="cpuPercent(node)"
              :stroke-width="10"
              :show-text="false"
              :color="usageColor(cpuPercent(node))"
            />
          </div>

          <div>
            <div class="mb-1 flex justify-between text-xs text-slate-400">
              <span>Memory</span>
              <span>{{ memPercent(node) }}%</span>
            </div>
            <el-progress
              :percentage="memPercent(node)"
              :stroke-width="10"
              :show-text="false"
              :color="usageColor(memPercent(node))"
            />
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

const workers = ref<Worker[]>([])
let timer: number | null = null

function usageColor(percent: number) {
  if (percent < 50) return '#22c55e'
  if (percent <= 80) return '#f59e0b'
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

async function fetchWorkers() {
  try {
    const { data } = await axios.get('http://127.0.0.1:8000/api/workers')
    workers.value = data.workers ?? []
  } catch {
    workers.value = []
  }
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