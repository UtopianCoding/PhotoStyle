// 任务轮询组合式函数：按间隔拉取任务状态，终态自动停止
import { onUnmounted, ref, watch } from 'vue'
import { getTaskStatus, getPublicTaskStatus } from '@/api/style'
import { useUserStore } from '@/stores/user'
import type { StyleTask } from '@/types'

/**
 * @param taskIdGetter 返回当前任务 ID 的函数（支持路由参数变化时自动重拉）
 * @param interval 轮询间隔（毫秒），默认 2000
 */
export function useTaskPolling(taskIdGetter: () => string, interval = 2000) {
  // 最新任务数据
  const task = ref<StyleTask | null>(null)
  // 是否加载中
  const loading = ref(false)

  let timer: number | null = null

  /** 拉取一次任务状态 */
  async function fetchOnce() {
    const id = taskIdGetter()
    if (!id) return
    loading.value = true
    try {
      const userStore = useUserStore()
      // 已登录用认证接口，未登录用公开接口（分享海报扫码场景）
      const data = userStore.isLoggedIn
        ? await getTaskStatus(id)
        : await getPublicTaskStatus(id)
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

  // 路由参数（任务 ID）变化时，清空并重新拉取（如「重新生成」跳转到新任务页）
  watch(taskIdGetter, () => {
    task.value = null
    start()
  })

  // 组件卸载时清理定时器
  onUnmounted(stop)

  return { task, loading, start, stop, fetchOnce }
}
