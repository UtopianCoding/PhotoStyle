// 任务状态管理：任务 ID、状态、进度、结果及轮询逻辑
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { StyleResult, TaskStatus } from '@/types'
import { getTaskStatus } from '@/api/style'

export const useTaskStore = defineStore('task', () => {
  // 任务 ID
  const taskId = ref<string>('')
  // 任务状态
  const status = ref<TaskStatus | string>('pending')
  // 任务进度（0-100）
  const progress = ref<number>(0)
  // 任务结果列表
  const results = ref<StyleResult[]>([])

  // 轮询定时器
  let timer: number | null = null

  /** 设置当前任务 */
  function setTask(task: { taskId: string; status: string; progress: number; results?: StyleResult[] }) {
    taskId.value = task.taskId
    status.value = task.status
    progress.value = task.progress
    results.value = task.results ?? []
  }

  /** 开始轮询任务状态 */
  function poll(interval = 2000) {
    if (!taskId.value) return
    stop()
    timer = window.setInterval(async () => {
      try {
        const task = await getTaskStatus(taskId.value)
        setTask(task)
        // 终态停止轮询
        if (task.status === 'success' || task.status === 'failed' || task.status === 'canceled') {
          stop()
        }
      } catch {
        stop()
      }
    }, interval)
  }

  /** 停止轮询 */
  function stop() {
    if (timer !== null) {
      clearInterval(timer)
      timer = null
    }
  }

  /** 重置任务状态 */
  function reset() {
    stop()
    taskId.value = ''
    status.value = 'pending'
    progress.value = 0
    results.value = []
  }

  return { taskId, status, progress, results, setTask, poll, stop, reset }
})
