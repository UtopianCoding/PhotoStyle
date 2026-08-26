<template>
  <main
    :class="['flipbook-room', { 'is-turning': isTurning, 'has-opened': hasOpened }]"
    :style="roomStyle"
  >
    <header class="flipbook-header">
      <span>{{ kicker }}</span>
      <h1>{{ title }}</h1>
      <span>{{ orientation === 'portrait' ? 'Single leaf' : meta }}</span>
    </header>

    <section class="flipbook-stage" :aria-label="`${title} interactive photo book`">
      <div class="flipbook-ground-shadow" aria-hidden="true" />
      <div class="photo-book-rig">
        <div ref="bookContainer" class="photo-book">
          <article
            v-for="(page, index) in leaves"
            :key="page.id"
            :class="leafClasses(page, index)"
            :aria-label="page.alt || 'Blank back cover'"
            :data-density="index === 0 || index === leaves.length - 1 ? 'hard' : 'soft'"
            :data-page-id="page.id"
            :style="leafStyle(page)"
          >
            <!-- 独立封皮：雪山照片背景 + 大标题 + 朱印（不使用第一张照片） -->
            <div v-if="page.id === 'cover'" class="photo-leaf__cover">
              <img class="cover-art" :src="coverArt" alt="" draggable="false" />
              <span class="cover-art-shade" aria-hidden="true"></span>
              <div class="cover-frame">
                <div class="cover-body">
                  <h2 class="cover-title">{{ title }}</h2>
                </div>
                <div class="cover-footer">
                  <span class="cover-brand">PhotoStyle</span>
                  <span class="cover-seal">影</span>
                </div>
              </div>
            </div>
            <!-- 封底：朱印 -->
            <div v-else-if="page.id === 'back-cover'" class="photo-leaf__back">
              <span class="photo-leaf__back-seal">影</span>
              <span class="photo-leaf__back-mark">PhotoStyle</span>
            </div>
            <img
              v-else-if="page.image"
              :src="page.image"
              :alt="page.alt"
              draggable="false"
            />
            <div v-if="page.caption || page.text" class="photo-leaf__copy">
              <p v-if="page.caption" class="photo-leaf__caption">{{ page.caption }}</p>
              <p v-if="page.text">{{ page.text }}</p>
            </div>
          </article>
        </div>
      </div>
    </section>

    <footer class="flipbook-controls" aria-label="Book controls">
      <button
        type="button"
        :disabled="current === 0 || isTurning"
        aria-label="Previous page"
        @click="previous"
      >
        <span aria-hidden="true">&#8249;</span>
      </button>
      <div class="flipbook-status" aria-live="polite" aria-atomic="true">
        <span>{{ statusText }}</span>
        <small>拖拽、滑动或使用方向键翻页</small>
      </div>
      <button
        type="button"
        :disabled="current >= leaves.length - 1 || isTurning"
        aria-label="Next page"
        @click="next"
      >
        <span aria-hidden="true">&#8250;</span>
      </button>
      <button
        type="button"
        class="flipbook-music"
        :class="{ 'is-playing': music.playing }"
        :aria-label="music.playing ? '暂停背景音乐' : '播放背景音乐'"
        @click="onToggleMusic"
      >
        <span aria-hidden="true">
          <!-- 未播放：音符图标 -->
          <svg v-if="!music.playing" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 9l12-3" />
          </svg>
          <!-- 播放中：音符 + 声波 -->
          <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 9l12-3" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M4 10a5 5 0 000 4M2 7a9 9 0 000 10" />
          </svg>
        </span>
      </button>
      <!-- 音量调节 -->
      <input
        type="range"
        class="flipbook-volume"
        :value="music.volume"
        min="0"
        max="1"
        step="0.05"
        aria-label="背景音乐音量"
        @input="music.setVolume(Number(($event.target as HTMLInputElement).value))"
      />
    </footer>
  </main>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { PageFlip } from 'page-flip'
import type { FlipbookPage, BookLayout, FlipbookTheme } from '@/types/flipbook'
import { useAmbientMusic } from '@/composables/useAmbientMusic'
import coverArt from '@/fm/pexels-kaomhg-26926197.jpg'
import './photo-flipbook.css'

const props = withDefaults(defineProps<{
  pages: FlipbookPage[]
  title?: string
  kicker?: string
  meta?: string
  theme?: FlipbookTheme | null
  musicUrl?: string
}>(), {
  title: 'Photo Book',
  kicker: 'Folio',
  meta: 'Open spread',
  theme: null,
  musicUrl: ''
})

const emit = defineEmits<{
  (e: 'pageChange', page: number): void
}>()

// 背景音乐（优先远程 URL，浏览器需用户手势触发，因此只提供按钮）
// 传 getter 以便异步加载的 musicUrl 生效
const music = useAmbientMusic(() => props.musicUrl)
// 用户是否手动操作过音乐（操作后不再自动播放）
let userTouchedMusic = false

/** 音乐按钮：记录手动操作并切换 */
function onToggleMusic() {
  userTouchedMusic = true
  music.toggle()
}

// 打开画册自动播放：音乐 URL 就绪后自动开始（best-effort，被浏览器拦截则手动）
watch(
  () => props.musicUrl,
  (url) => {
    if (url && !userTouchedMusic) {
      music.start()
    }
  },
  { immediate: true }
)

const DEFAULT_PAGE = { width: 500, height: 680 }
const DEFAULT_PADDING = 24

const bookContainer = ref<HTMLElement | null>(null)
let pageFlip: PageFlip | null = null
// 开场翻页计时器
let openTimer: ReturnType<typeof setTimeout> | null = null

const current = ref(0)
const isTurning = ref(false)
const orientation = ref<'portrait' | 'landscape'>('landscape')
// 入场动画状态：初始化完成后触发"翻开相册"仪式
const hasOpened = ref(false)

/** 补全页面列表：独立封皮 + 用户照片 + 补页 + 封底 */
const leaves = computed<FlipbookPage[]>(() => {
  // 首页为独立封皮（不使用第一张照片）
  const result: FlipbookPage[] = [
    { id: 'cover', alt: 'Cover' },
    ...props.pages,
  ]
  if ((result.length + 1) % 2) {
    result.push({ id: 'inside-back-cover', alt: 'Blank inside back cover' })
  }
  result.push({ id: 'back-cover', alt: 'Solid-color back cover' })
  return result
})

/** 计算画册布局参数 */
const layout = computed<BookLayout>(() => {
  const pages = props.pages
  const imagePages = pages.filter(p => p.image)
  const first = imagePages[0]
  const measuredPages = imagePages.filter(
    p => p.width && p.height && p.width > 0 && p.height > 0
  )
  const uniformDimensions = Boolean(
    first?.width && first?.height &&
    imagePages.every(p => p.width === first.width && p.height === first.height)
  )
  const ratios = measuredPages
    .map(p => p.width! / p.height!)
    .sort((a, b) => a - b)

  const containedArea = (pageRatio: number) =>
    ratios.reduce(
      (total, imageRatio) =>
        total + Math.min(imageRatio / pageRatio, pageRatio / imageRatio),
      0
    )

  const representativeRatio = ratios.length
    ? ratios.reduce((best, candidate) =>
        containedArea(candidate) > containedArea(best) ? candidate : best
      )
    : DEFAULT_PAGE.width / DEFAULT_PAGE.height

  const source = { width: representativeRatio, height: 1 }
  const scale = Math.min(
    DEFAULT_PAGE.width / source.width,
    DEFAULT_PAGE.height / source.height
  )
  const width = Math.max(1, Math.round(source.width * scale))
  const height = Math.max(1, Math.round(source.height * scale))

  return {
    width,
    height,
    minWidth: Math.max(1, Math.round(width * 0.56)),
    minHeight: Math.max(1, Math.round(height * 0.56)),
    maxWidth: Math.round(width * 1.04),
    maxHeight: Math.round(height * 1.04),
    defaultFit: uniformDimensions ? 'fill' : 'contain',
    defaultPadding: uniformDimensions ? 0 : DEFAULT_PADDING
  }
})

const roomStyle = computed(() => {
  const base: Record<string, string> = {
    '--flipbook-page-ratio': String(layout.value.width / layout.value.height),
    '--flipbook-spread-ratio': String((layout.value.width * 2) / layout.value.height),
    '--flipbook-max-spread': `${layout.value.maxWidth * 2}px`
  }
  
  // 应用 AI 生成的主题色
  if (props.theme) {
    if (props.theme.pageColor) {
      base['--flipbook-page-color'] = props.theme.pageColor
    }
    if (props.theme.coverColor) {
      base['--flipbook-cover-color'] = props.theme.coverColor
    }
    if (props.theme.backCoverColor) {
      base['--flipbook-back-cover-color'] = props.theme.backCoverColor
    }
    // 根据纹理类型设置纹理
    if (props.theme.pageTexture === 'smooth') {
      base['--flipbook-page-texture'] = 'none'
    } else if (props.theme.pageTexture === 'grainy') {
      base['--flipbook-page-texture'] = 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noise\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noise)\' opacity=\'0.04\'/%3E%3C/svg%3E")'
    } else if (props.theme.pageTexture === 'fiber') {
      base['--flipbook-page-texture'] = 'repeating-linear-gradient(45deg, transparent 0 2px, rgba(72,62,44,.025) 3px)'
    }
    // 默认 paper 纹理保持 CSS 中的定义
  }
  
  return base
})

function leafClasses(page: FlipbookPage, index: number) {
  const fit = page.fit ?? layout.value.defaultFit
  // 空页判定：封皮不算空白页
  const blank = !page.image && !page.text && !page.caption && page.id !== 'cover'
  const isHard = index === 0 || index === leaves.value.length - 1
  return [
    'photo-leaf',
    `photo-leaf--fit-${fit}`,
    {
      'photo-leaf--cover': index === 0,
      'photo-leaf--back-cover': isHard && index > 0,
      'photo-leaf--blank': blank
    }
  ]
}

function leafStyle(page: FlipbookPage) {
  const padding = page.padding ?? layout.value.defaultPadding
  return {
    '--photo-padding': `${padding}px`,
    '--photo-inset': `${padding * 2}px`
  }
}

const statusText = computed(() => {
  const onBackCover = current.value === leaves.value.length - 1
  const onInsideBackCover = current.value >= props.pages.length && !onBackCover
  if (onBackCover) return '封底'
  if (onInsideBackCover) return '封底内侧'
  const visiblePage = Math.min(current.value + 1, props.pages.length)
  return `${String(visiblePage).padStart(2, '0')} / ${String(props.pages.length).padStart(2, '0')}`
})

function previous() {
  if (!isTurning.value) pageFlip?.flipPrev('bottom')
}

function next() {
  if (!isTurning.value) pageFlip?.flipNext('bottom')
}

function initFlipbook() {
  if (!bookContainer.value) return

  // 清理旧实例
  if (pageFlip) {
    pageFlip.destroy()
    pageFlip = null
  }

  const l = layout.value
  pageFlip = new PageFlip(bookContainer.value, {
    width: l.width,
    height: l.height,
    size: 'stretch',
    minWidth: l.minWidth,
    maxWidth: l.maxWidth,
    minHeight: l.minHeight,
    maxHeight: l.maxHeight,
    startPage: 0,
    drawShadow: true,
    flippingTime: 780,
    usePortrait: true,
    startZIndex: 10,
    autoSize: true,
    maxShadowOpacity: 0.42,
    showCover: true,
    mobileScrollSupport: false,
    clickEventForward: true,
    useMouseEvents: true,
    swipeDistance: 26,
    showPageCorners: true,
    disableFlipByClick: false
  })

  // 从 HTML 子元素加载页面
  pageFlip.loadFromHTML(bookContainer.value.querySelectorAll('article'))

  // 事件监听（data 类型为 string | number，统一转换）
  pageFlip.on('flip', (e) => {
    const page = Number(e.data)
    current.value = page
    emit('pageChange', page)
  })

  pageFlip.on('changeOrientation', (e) => {
    orientation.value = String(e.data) as 'portrait' | 'landscape'
  })

  pageFlip.on('changeState', (e) => {
    isTurning.value = String(e.data) !== 'read'
  })

  // 开场仪式：相册就绪后展示封面，短暂停留再自动翻开第一页
  pageFlip.on('init', () => {
    hasOpened.value = true
    openTimer = setTimeout(() => {
      if (pageFlip) {
        pageFlip.flipNext('bottom')
      }
    }, 1000)
    // 打开画册默认播放背景音乐（浏览器可能拦截，失败时用户可手动点击播放）
    music.start()
  })
}

// 键盘事件
function onKeyDown(event: KeyboardEvent) {
  if (event.altKey || event.ctrlKey || event.metaKey || isTurning.value) return
  if (event.key === 'ArrowLeft') {
    event.preventDefault()
    previous()
  }
  if (event.key === 'ArrowRight' || event.key === ' ') {
    event.preventDefault()
    next()
  }
  if (event.key === 'Home') pageFlip?.flip(0, 'bottom')
  if (event.key === 'End') pageFlip?.flip(leaves.value.length - 1, 'bottom')
}

// 页面数据变化时重新初始化
watch(() => props.pages, async () => {
  current.value = 0
  hasOpened.value = false
  await nextTick()
  initFlipbook()
}, { deep: true })

onMounted(async () => {
  await nextTick()
  initFlipbook()
  window.addEventListener('keydown', onKeyDown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown)
  if (openTimer) {
    clearTimeout(openTimer)
    openTimer = null
  }
  music.stop()
  if (pageFlip) {
    pageFlip.destroy()
    pageFlip = null
  }
})
</script>
