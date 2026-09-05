// 全局图片懒加载指令 v-lazy
// 用法：<img v-lazy="url" alt="" />
// 图片进入视口前使用 1x1 透明占位（配合 main.css 的占位底色），进入后替换为真实 src，
// 减少首屏并发大图请求。卸载时自动断开观察器。

import type { Directive } from 'vue'

// 1x1 透明 GIF（体积最小，作为占位避免浏览器默认 broken 图标）
const PLACEHOLDER =
  'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'

// 记录已加载的 URL，避免重复触发 onload
const loadedUrls = new WeakSet<HTMLElement>()

function applyLazy(el: HTMLImageElement, src: string) {
  const real = typeof src === 'string' ? src.trim() : ''
  if (!real) return
  if (loadedUrls.has(el) && el.dataset.lazySrc === real) return
  // 更新目标 URL
  el.dataset.lazySrc = real
  if (el.complete && el.naturalWidth > 0) {
    // 已加载过，直接替换（例如 v-for key 复用导致的值变化）
    loadedUrls.add(el)
  }
  el.src = real
}

let sharedObserver: IntersectionObserver | null = null

function getObserver(): IntersectionObserver {
  if (sharedObserver) return sharedObserver
  sharedObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue
        const el = entry.target as HTMLImageElement
        const src = el.dataset.lazySrc
        if (src) {
          el.src = src
          loadedUrls.add(el)
        }
        sharedObserver?.unobserve(el)
      }
    },
    { rootMargin: '200px 0px' }, // 提前 200px 开始加载
  )
  return sharedObserver
}

export const vLazy: Directive<HTMLImageElement, string> = {
  mounted(el, binding) {
    if (el.tagName !== 'IMG') return
    const target = binding.value
    if (!target) return
    // 占位：清空当前 src 并记录真实 URL；保持 el 高度/占位底色
    el.dataset.lazySrc = String(target)
    if (!el.src || el.src === location.href) {
      el.src = PLACEHOLDER
    }
    getObserver().observe(el)
  },
  updated(el, binding) {
    if (el.tagName !== 'IMG') return
    const old = binding.oldValue
    const next = binding.value
    if (old === next) return
    if (!next) {
      getObserver().unobserve(el)
      loadedUrls.delete(el)
      return
    }
    // 值变化（如图片替换/重选）：重新进入懒加载流程
    loadedUrls.delete(el)
    el.dataset.lazySrc = String(next)
    el.src = PLACEHOLDER
    getObserver().observe(el)
  },
  unmounted(el) {
    getObserver().unobserve(el)
    loadedUrls.delete(el)
  },
}
