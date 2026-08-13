// 任务轮询组合式函数：按间隔拉取任务状态，终态自动停止
import { onUnmounted, ref } from 'vue'
import { getTaskStatus } from '@/api/style'
import type { StyleTask } from '@/types'

/**
 * @param taskId 任务 ID
 * @param interval 轮询间隔（毫秒），默认 2000
 */
export function useTaskPolling(taskId: string, interval = 2000) {
  // 最新任务数据
  const task = ref<StyleTask | null>(null)
  // 是否加载中
  const loading = ref(false)

  let timer: number | null = null

  /** 拉取一次任务状态 */
  async function fetchOnce() {
    if (!taskId) return
    loading.value = true
    try {
      const data = await getTaskStatus(taskId)
      task.value = data
      // 终态停止轮询
      if (data.status === 'success' || data.status === 'failed' || data.status === 'canceled') {
        stop()
      }
    } finally {
      loading.value = false
    }
  }

  /** 开始轮询 */
  function start() {
    stop()
    fetchOnce()
    timer = window.setInterval(fetchOnce, interval)
  }

  /** 停止轮询 */
  function stop() {
    if (timer !== null) {
      clearInterval(timer)
      timer = null
    }
  }

  // 组件卸载时清理定时器
  onUnmounted(stop)

  return { task, loading, start, stop, fetchOnce }
}
