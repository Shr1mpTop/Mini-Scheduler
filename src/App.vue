<template>
  <main class="min-h-screen bg-slate-950 text-slate-100">
    <div class="mx-auto max-w-7xl space-y-6 px-4 py-8">
      <header class="rounded-2xl border border-cyan-700/40 bg-slate-900/70 p-6 shadow-2xl shadow-cyan-900/30">
        <h1 class="text-3xl font-bold tracking-wide text-cyan-300">Mini Scheduler</h1>
        <p class="mt-2 text-sm text-slate-400">轻量级分布式任务调度系统 · FastAPI + Vue3</p>

        <div class="mt-6 grid grid-cols-1 gap-3 md:grid-cols-4">
          <el-input v-model="form.command" placeholder="command: python job.py" class="md:col-span-2" />
          <el-input-number v-model="form.cpu_required" :min="0.1" :step="0.1" :precision="1" />
          <el-input-number v-model="form.mem_required" :min="0.1" :step="0.1" :precision="1" />
        </div>

        <div class="mt-4 flex gap-3">
          <el-button type="primary" @click="submitTask" :loading="submitting">提交任务</el-button>
          <el-tag v-if="lastTaskId" effect="dark" type="success">最近任务: {{ lastTaskId }}</el-tag>
        </div>
      </header>

      <Heatmap />

      <section class="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
        <div class="mb-3 flex items-center justify-between">
          <h2 class="text-lg font-semibold text-slate-100">任务列表</h2>
          <el-tag type="info" effect="dark">每 2 秒自动刷新</el-tag>
        </div>

        <el-table :data="tasks" stripe class="w-full" height="320">
          <el-table-column prop="id" label="Task ID" min-width="220" />
          <el-table-column prop="command" label="Command" min-width="180" />
          <el-table-column prop="assigned_worker_id" label="Worker" min-width="120" />
          <el-table-column label="Status" width="120">
            <template #default="scope">
              <el-tag :type="statusTagType(scope.row.status)" effect="dark">{{ scope.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="130" fixed="right">
            <template #default="scope">
              <el-button
                v-if="scope.row.status === 'RUNNING'"
                size="small"
                type="primary"
                @click="openLogs(scope.row.id)"
              >
                查看日志
              </el-button>
              <span v-else class="text-xs text-slate-500">--</span>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </div>

    <LiveLogModal v-model:visible="logVisible" :task-id="lastTaskId" />
  </main>
</template>

<script setup lang="ts">
import axios from 'axios'
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import Heatmap from './components/Heatmap.vue'
import LiveLogModal from './components/LiveLogModal.vue'

const form = reactive({
  command: 'python demo.py',
  cpu_required: 0.5,
  mem_required: 1.0
})

const submitting = ref(false)
const lastTaskId = ref('')
const logVisible = ref(false)
const tasks = ref<any[]>([])
let tasksPollTimer: number | null = null

function statusTagType(status: string) {
  if (status === 'RUNNING') return 'warning'
  if (status === 'SUCCESS') return 'success'
  if (status === 'FAILED') return 'danger'
  return 'info'
}

function openLogs(taskId: string) {
  lastTaskId.value = taskId
  logVisible.value = true
}

async function fetchTasks() {
  try {
    const { data } = await axios.get('http://127.0.0.1:8000/api/tasks')
    tasks.value = data.tasks ?? []
  } catch {
    tasks.value = []
  }
}

async function submitTask() {
  if (!form.command.trim()) {
    ElMessage.warning('请输入 command')
    return
  }

  submitting.value = true
  try {
    const { data } = await axios.post('http://127.0.0.1:8000/api/tasks', form)
    if (data.status === 'RUNNING') {
      lastTaskId.value = data.task_id
      logVisible.value = true
      ElMessage.success(`任务已分配到 Worker: ${data.assigned_worker_id}`)
      fetchTasks()
    } else {
      ElMessage.error(data.message || '任务提交失败')
    }
  } catch {
    ElMessage.error('后端不可用或请求失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  fetchTasks()
  tasksPollTimer = window.setInterval(fetchTasks, 2000)
})

onBeforeUnmount(() => {
  if (tasksPollTimer !== null) {
    clearInterval(tasksPollTimer)
    tasksPollTimer = null
  }
})
</script>