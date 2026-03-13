<template>
  <el-dialog
    :model-value="visible"
    title="Live Task Logs"
    width="80%"
    destroy-on-close
    @close="handleClose"
  >
    <div class="rounded-lg border border-slate-700 bg-black p-3">
      <div
        ref="logContainerRef"
        class="h-[420px] overflow-y-auto rounded bg-black/80 p-3 font-mono text-sm leading-6 text-emerald-400"
        @scroll="onScroll"
      >
        <div v-if="logs.length === 0" class="text-slate-500">等待日志流连接...</div>
        <div v-for="(line, idx) in logs" :key="idx">{{ line }}</div>
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-between text-xs text-slate-400">
        <span>日志条数: {{ logs.length }}</span>
        <span>{{ autoScroll ? '自动滚动: 开' : '自动滚动: 关（已检测用户查看历史）' }}</span>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps<{
  visible: boolean
  taskId: string
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
}>()

const logs = ref<string[]>([])
const logContainerRef = ref<HTMLElement | null>(null)
const autoScroll = ref(true)

let ws: WebSocket | null = null
let flushTimer: number | null = null

const buffer: string[] = []
const FLUSH_INTERVAL = 100
const BOTTOM_THRESHOLD = 20
const MAX_LOG_LINES = 8000

function isAtBottom(el: HTMLElement): boolean {
  return el.scrollHeight - el.scrollTop - el.clientHeight <= BOTTOM_THRESHOLD
}

function onScroll() {
  const el = logContainerRef.value
  if (!el) return
  autoScroll.value = isAtBottom(el)
}

function flushBufferToReactiveLogs() {
  if (buffer.length === 0) return

  const incoming = buffer.splice(0, buffer.length)
  logs.value.push(...incoming)

  if (logs.value.length > MAX_LOG_LINES) {
    logs.value.splice(0, logs.value.length - MAX_LOG_LINES)
  }

  if (autoScroll.value) {
    nextTick(() => {
      requestAnimationFrame(() => {
        const el = logContainerRef.value
        if (!el) return
        el.scrollTop = el.scrollHeight
      })
    })
  }
}

function startFlushLoop() {
  stopFlushLoop()
  flushTimer = window.setInterval(flushBufferToReactiveLogs, FLUSH_INTERVAL)
}

function stopFlushLoop() {
  if (flushTimer !== null) {
    window.clearInterval(flushTimer)
    flushTimer = null
  }
}

function closeSocket() {
  if (ws) {
    ws.close()
    ws = null
  }
}

function connect() {
  if (!props.taskId) return

  logs.value = []
  buffer.length = 0
  autoScroll.value = true

  const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${protocol}://${location.hostname}:8000/api/tasks/${props.taskId}/logs`)

  ws.onmessage = (event) => {
    buffer.push(String(event.data))
  }

  ws.onerror = () => {
    buffer.push('[SYSTEM] WebSocket error')
  }

  ws.onclose = () => {
    buffer.push('[SYSTEM] Log stream closed')
    flushBufferToReactiveLogs()
  }

  startFlushLoop()
}

function disconnect() {
  closeSocket()
  stopFlushLoop()
  flushBufferToReactiveLogs()
}

function handleClose() {
  emit('update:visible', false)
}

watch(
  () => props.visible,
  (visible) => {
    if (visible) connect()
    else disconnect()
  }
)

onBeforeUnmount(() => {
  disconnect()
})
</script>