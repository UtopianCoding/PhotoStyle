<script setup lang="ts">
// 结果页：展示任务进度 / 原图与效果图左右两列对比 / 下载 / 收藏 / 分享
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Download, Share, Star, ZoomIn, Refresh, Picture, Loading, Close } from '@element-plus/icons-vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { favoriteResult } from '@/api/history'
import { removeTaskResults } from '@/api/style'
import { useTaskPolling } from '@/composables/useTaskPolling'
import { useConvert } from '@/composables/useConvert'
import { generateSharePoster, downloadDataUrl } from '@/utils/poster'
import type { StyleResult } from '@/types'

const route = useRoute()
const router = useRouter()

// 任务 ID（来自路由参数）
const taskId = computed(() => String(route.params.id ?? ''))

// 使用轮询组合式函数获取任务状态（接口会返回 image_id + original_url，不再依赖上传态 store）
const { task, start, stop } = useTaskPolling(() => String(route.params.id ?? ''))
const { regenerate, converting: regenerating } = useConvert()
const favoriting = ref(false)

// 重新转换（带意见）面板状态
const showRegenerate = ref(false)
// 用户填写的修改意见
const feedback = ref('')

// 修改意见快捷建议：点击一键填入，降低表达门槛
const FEEDBACK_SUGGESTIONS = [
  '背景再亮一些',
  '整体色调偏暖',
  '主体（人物）更突出',
  '背景更简洁干净',
  '笔触更细腻一些',
  '冰箱贴稍微放大',
]
/** 点击快捷建议：追加到意见框（已包含则不重复） */
function appendFeedback(text: string) {
  const cur = feedback.value.trim()
  if (!cur) {
    feedback.value = text
    return
  }
  if (cur.includes(text)) return
  const sep = cur.endsWith('；') || cur.endsWith(';') ? ' ' : '；'
  feedback.value = `${cur}${sep}${text}`
}

// 原提示词（来自任务状态接口，成功时返回首个结果的完整提示词）
const originalPrompt = computed(() => task.value?.finalPrompt ?? '')

/** 提交重新生成：在原提示词基础上叠加修改意见交给模型 */
async function onRegenerate() {
  if (!task.value) return
  const newTask = await regenerate({
    imageId: task.value.imageId,
    skillId: task.value.skillId,
    finalPrompt: originalPrompt.value,
    feedback: feedback.value,
  })
  if (newTask) {
    // 跳转到新的任务结果页（useTaskPolling 会在路由参数变化时自动重拉）
    router.push(`/result/${newTask.taskId}`)
    showRegenerate.value = false
    feedback.value = ''
  }
}

// 是否完成 / 失败
const isDone = computed(() => task.value?.status === 'success')
const isFailed = computed(
  () => task.value?.status === 'failed' || task.value?.status === 'canceled',
)
// 当前阶段文案映射
const STAGE_LABEL: Record<string, string> = {
  analyzing: '正在分析图片内容…',
  generating: 'AI 正在绘制中…',
  uploading: '正在上传结果…',
}
const stageLabel = computed(() => {
  const stage = task.value?.stage ?? ''
  return STAGE_LABEL[stage] || '正在准备中…'
})

// 趣味话语库（按阶段分组，每 4 秒轮换）
const FUN_MESSAGES: Record<string, string[]> = {
  analyzing: [
    '正在用放大镜观察你的照片…',
    'AI 正在揣摩这张图的灵魂…',
    '让我看看这里面有什么有趣的故事…',
    '正在解析构图美学，请保持优雅的等待姿势…',
    '据说好照片都有自己的气场，正在感应中…',
    '正在数一数图片里有多少个像素点（开玩笑的）…',
    'AI 正在做眼保健操，准备大显身手…',
    '正在给这张照片做一次深度灵魂拷问…',
    '构图分析中，请想象自己是卢浮宫的策展人…',
    '正在用 AI 的第六感感受这张照片…',
    '图片内容识别中，目前还没发现外星人…',
    '正在为这张照片写一首小诗（AI 的文学梦）…',
    '据说每张照片都藏着摄影师的小心思…',
    '正在从 10 亿种风格里挑最适合你的那一种…',
    'AI 正在翻遍美术史寻找灵感，请稍候…',
    '正在分析光影关系，感觉像在看伦勃朗…',
    '图片扫描完毕…哦等等，让我再看一眼…',
    '正在计算这张照片的「好看指数」…',
    'AI 说：这张照片有故事，我得多看看…',
    '正在给照片做一次「美学体检」…',
  ],
  generating: [
    'AI 画师正在蘸墨，马上就好…',
    '正在为你施展魔法，请勿眨眼…',
    '每一笔都是精心计算的艺术，不是随便画画的…',
    '正在将平凡变为非凡，魔法进行中…',
    'AI 正在燃烧它的 GPU 小脑瓜…',
    '艺术创作中，请勿打扰大师的灵感…',
    '如果 AI 有手的话，它现在一定画得很认真…',
    '据说等待的时候摸摸屏幕会更快（并不会）…',
    'GPU 正在疯狂运转，建议给它扇扇风…',
    'AI 正在参考毕加索、梵高、莫奈的作品（大误）…',
    '正在把你的照片变成朋友圈的点赞收割机…',
    '据说多看几眼进度条，它就会跑得更快（玄学）…',
    'AI 正在一边画画一边哼小曲（你听不到而已）…',
    '这张图生成完后，AI 想请你给它打个五星好评…',
    '正在调用全宇宙的算力，只为这张图（夸张了）…',
    '艺术就是爆炸！——来自正在画画的 AI…',
    '正在把「还行」变成「绝了」，请耐心等待…',
    '据说盯着屏幕看会让 AI 紧张，建议去倒杯水…',
    'AI 画师表示：这张图我很有感觉！',
    '正在用神经网络为你编织一场视觉梦境…',
    '正在说服 AI 不要把事情搞砸…',
    '别想紫色的河马…啊不，别想别的，专注看进度条…',
    '服务器由一颗柠檬和两根电极供电（大概）…',
    '我发誓马上就好了…大概…可能…',
    '正在确保所有的 i 都加了点，所有的 t 都加了横…',
    '另一台服务器画得比这台快（开玩笑的）…',
    '正在从无穷大开始倒数，别急…',
    '不要慌…慌张只会让 GPU 更紧张…',
    '独角兽就在这条路的尽头，我保证…',
    '正在给蛋糕加上最后一层奶油，蛋糕不是谎言…',
    '至少你没有在打客服电话排队…',
    '正在转仓鼠轮发电中，请保持耐心…',
    '好咖啡需要慢慢泡，好 AI 需要慢慢算…',
    '正在施展「化腐朽为神奇」之术…',
    'AI 说它需要一杯咖啡才能继续（它没有嘴）…',
    '正在把像素重新排列成更好看的样子…',
    '据说深呼吸三次，图就画好了（没有科学依据）…',
    'AI 正在和灵感女神讨价还价…',
    '别急，好东西从来不会准时出现，它们总是姗姗来迟…',
    '正在为你创造一个让隔壁小孩都馋哭的效果…',
    'GPU 正在画画，CPU 在旁边喊加油…',
    'AI 刚刚偷偷打了个哈欠，现在精神多了…',
    '正在用 0 和 1 编织一幅浮世绘…',
    '据说等图的时候原地转三圈会更快（不要试）…',
    'AI 正在翻字典找一个形容词来形容你的照片：绝！',
    '正在把「普通」这个词从字典里删掉…',
    '别催了别催了，AI 画师说再给它一分钟…',
    '你的照片正在 undergoing 一场华丽的蜕变…',
    'AI 正在给这张图注入灵魂，请准备接收…',
    '据说在等的时候许个愿，出图会更好看（心理暗示）…',
    '正在施展七十二变中的第八变：照片美颜术…',
    'AI 正在用 4090 的算力思考人生，顺便帮你画图…',
    '别急，AI 正在跟你的照片谈恋爱呢…',
    '据说每个像素都在排队做造型，不要插队…',
    'AI 画师说：这单我用心了，包你满意…',
    '正在把滤镜调到你妈都认不出的程度（开玩笑的）…',
    'GPU 温度已达 80°C，AI 表示：小意思…',
    'AI 正在用毕加索的立体主义分析你的自拍…',
    '据说看到这条消息的人，运气会变好一点点…',
    '正在把「将就」升级为「讲究」，请稍候…',
    'AI 正在给你的照片加一层「高级感」滤镜…',
    '据说等图的时候吃点零食，时间会过得更快…',
    '正在用神经网络模拟莫奈的笔触…',
    'AI 说这张图的构图可以打 99 分，留 1 分怕你骄傲…',
    '正在把「路人甲」变成「主角光环」…',
    'GPU 正在全力运转，电费正在疯狂燃烧…',
    'AI 正在用蒙德里安的几何美学重新构图…',
    '据说看到进度条动了的人，今天会有好事发生…',
    '正在给照片做一次「美学整容」，保证自然…',
    'AI 画师正在调色调到手软，只为给你最完美的效果…',
    '别急，正在把你的照片从「还行」升级到「惊艳」…',
    '正在用达芬奇的黄金比例重新设计构图…',
    'AI 说它正在用「心」画，不是用「芯」画（虽然确实是芯片）…',
    '据说在等图的时候喝口水，出图会更水润…',
    '正在把「随手一拍」变成「大片既视感」…',
    'AI 正在用 100 层神经网络为你精雕细琢…',
    '正在给照片加一点「氛围感」，马上就好…',
    '据说等图的时候笑一笑，出图会更好看（玄学+1）…',
    'AI 正在用「像素级」的耐心为你打磨每一个细节…',
    '正在把「普普通通」变成「与众不同」，马上就好…',
  ],
  uploading: [
    '正在将杰作送到云端保险箱…',
    'AI 正在给你的作品盖上"完成"的印章…',
    '正在为你的艺术品找一个永久的家…',
    '最后的打包工作，马上就能拆快递了…',
    '正在把这幅画小心翼翼地放进画框…',
    'AI 画师正在做最后的签名…',
    '正在为你的作品系上蝴蝶结…',
    '上传中，每一比特都承载着艺术的重量…',
    '正在把这幅画送到你的专属画廊…',
    'AI 正在给作品贴上"易碎品，轻拿轻放"的标签…',
    '正在为这幅杰作办理入住手续…',
    'AI 画师正在擦拭画框上的最后一粒灰尘…',
    '正在给你的作品办理"出生证明"…',
    '最后一公里冲刺，马上到达终点…',
    '正在把这幅画装进时光胶囊，永久保存…',
    'AI 正在给你的作品喷上保护漆…',
    '正在为你的艺术品安排一个C位…',
    '上传进度条正在努力奔跑，不要催它…',
    '正在把这幅画送到你的个人美术馆…',
    'AI 画师正在做最后的质检：完美！',
  ],
  default: [
    '好的作品值得等待，就像好酒需要陈酿…',
    '正在努力中，请稍安勿躁…',
    'AI 正在加班加点，只为给你惊喜…',
    '等待是为了更好的相遇，比如遇见你的新头像…',
    '正在后台默默耕耘，前台马上开花结果…',
    '别着急，让子弹飞一会儿…',
    'AI 正在用洪荒之力为你创作…',
    '正在把"普通"变成"特别"，这需要一点时间…',
    '据说等待的时候做几个深呼吸，时间会过得更快…',
    'AI 正在用魔法棒点石成金，请稍等片刻…',
    '耐心等待是一种美德，而你正在践行它…',
    '正在为你准备一份视觉大餐，马上上菜…',
    'AI 说：好东西不怕等，我怕你等太久…',
    '正在把"随便拍拍"变成"精心制作"…',
    '据说看到这条的人，今天会有好事发生…',
    'AI 正在全力以赴，不辜负你的等待…',
    '正在为你的照片注入灵魂，请稍等…',
    '别急，AI 正在和灵感女神开会讨论…',
    '正在把平凡变成非凡，这需要一点魔法时间…',
    'AI 画师说：慢工出细活，我在用心画…',
  ],
}

const funMsgIndex = ref(0)
let funMsgTimer: ReturnType<typeof setInterval> | null = null
const currentStage = computed(() => task.value?.stage ?? '')
const funMessages = computed(() => FUN_MESSAGES[currentStage.value] ?? FUN_MESSAGES.default)
const funMessage = computed(() => funMessages.value[funMsgIndex.value % funMessages.value.length])

function startFunMsgRotation() {
  funMsgIndex.value = Math.floor(Math.random() * funMessages.value.length)
  funMsgTimer = setInterval(() => {
    funMsgIndex.value = (funMsgIndex.value + 1) % funMessages.value.length
  }, 4000)
}

function stopFunMsgRotation() {
  if (funMsgTimer) {
    clearInterval(funMsgTimer)
    funMsgTimer = null
  }
}

// 阶段切换时重置趣味话语
watch(currentStage, () => {
  stopFunMsgRotation()
  startFunMsgRotation()
})
// 原图地址（从任务状态接口读取，不依赖首页上传态）
const originalUrl = computed(() => task.value?.originalUrl ?? '')

// 当前保留的结果列表（动态，删除后实时更新）
const keptResults = computed<StyleResult[]>(() => task.value?.results ?? [])
// 主展示图 = keptResults[0]
const firstResult = computed(() => keptResults.value[0] ?? null)
const resultUrl = computed(() => firstResult.value?.resultUrl ?? '')
// 是否已收藏（取第一张的收藏状态）
const favorite = computed(() => firstResult.value?.favorite ?? false)

// Provider 显示名称映射
const PROVIDER_LABELS: Record<string, string> = {
  qianwen: '千问',
  dalle: 'DALL-E',
  minimax: 'MiniMax',
  volcengine: '火山引擎',
  doubao: '豆包',
}
/** 获取 Provider 显示名称 */
function providerLabel(providerId: string): string {
  return PROVIDER_LABELS[providerId] ?? providerId
}
// 当前主展示图的 Provider 标签
const firstProviderLabel = computed(() => {
  const pid = firstResult.value?.provider ?? ''
  return pid ? providerLabel(pid) : ''
})
// 是否有多模型结果
const hasMultiResults = computed(() => keptResults.value.length > 1)

// 预览图列表：原图 + 所有保留的效果图
const previewList = computed(() => {
  const list: string[] = []
  if (originalUrl.value) list.push(originalUrl.value)
  keptResults.value.forEach(r => list.push(r.resultUrl))
  return list
})
// 预览初始位置
const previewInitialIndex = ref(0)

onMounted(() => {
  start()
  startFunMsgRotation()
})

onUnmounted(() => {
  stop()
  stopFunMsgRotation()
})

/** 点击效果图预览 */
function onPreviewResult() {
  if (!resultUrl.value) return
  // 效果图在 previewList 中的索引（原图在前，效果图在后）
  previewInitialIndex.value = originalUrl.value ? 1 : 0
}

/** 切换主展示图：点击网格中的某张图 */
function switchMainResult(idx: number) {
  if (idx < 0 || idx >= keptResults.value.length) return
  // 计算该图在 previewList 中的索引
  const offset = originalUrl.value ? 1 : 0
  previewInitialIndex.value = offset + idx
}

/** 删除状态 */
const deletingResultId = ref('')

/** 删除指定结果 */
async function onRemoveResult(resultId: string) {
  const result = keptResults.value.find(r => r.resultId === resultId)
  if (!result) return
  const label = providerLabel(result.provider) || '该模型'
  try {
    await ElMessageBox.confirm(
      `确定删除${label}的结果吗？删除后无法恢复。`,
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return // 用户取消
  }
  deletingResultId.value = resultId
  try {
    const remaining = await removeTaskResults(taskId.value, [resultId])
    // 更新本地数据
    if (task.value) {
      task.value.results = remaining
    }
    ElMessage.success('已删除')
  } catch {
    ElMessage.error('删除失败')
  } finally {
    deletingResultId.value = ''
  }
}

/** 切换收藏 */
async function onFavorite() {
  if (!firstResult.value) return
  favoriting.value = true
  try {
    if (hasMultiResults.value) {
      // 多张时收藏全部
      for (const r of keptResults.value) {
        await favoriteResult(r.resultId, !favorite.value)
      }
      // 更新本地数据
      for (const r of keptResults.value) {
        r.favorite = !favorite.value
      }
      ElMessage.success(!favorite.value ? '已全部收藏' : '已取消全部收藏')
    } else {
      // 单张时切换收藏状态
      const updated = await favoriteResult(firstResult.value.resultId, !favorite.value)
      if (task.value?.results && task.value.results[0]) {
        task.value.results[0].favorite = updated.favorite
      }
      ElMessage.success(updated.favorite ? '已收藏' : '已取消收藏')
    }
  } catch {
    ElMessage.error('操作失败')
  } finally {
    favoriting.value = false
  }
}

/** 下载结果图（支持跨域图片下载） */
async function onDownload() {
  if (!resultUrl.value) return
  try {
    if (hasMultiResults.value) {
      // 多张时逐张下载
      for (let i = 0; i < keptResults.value.length; i++) {
        const r = keptResults.value[i]
        const label = providerLabel(r.provider) || `img-${i + 1}`
        await downloadSingleImage(r.resultUrl, `photo-style-${taskId.value}-${label}.png`)
        if (i < keptResults.value.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 200))
        }
      }
      ElMessage.success(`已下载 ${keptResults.value.length} 张图片`)
    } else {
      // 单张时直接下载
      await downloadSingleImage(resultUrl.value, `photo-style-${taskId.value}.png`)
    }
  } catch {
    window.open(resultUrl.value, '_blank')
    ElMessage.warning('浏览器阻止了下载，请右键图片另存为')
  }
}

/** 下载单张图片 */
async function downloadSingleImage(url: string, filename: string) {
  const response = await fetch(url, { mode: 'cors' })
  if (!response.ok) throw new Error('下载失败')
  const blob = await response.blob()
  const blobUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(blobUrl)
}

/** 复制分享链接 */
function onShare() {
  if (!resultUrl.value) return
  const urls = keptResults.value.map(r => r.resultUrl).join('\n')
  navigator.clipboard
    ?.writeText(urls)
    .then(() => ElMessage.success(hasMultiResults.value ? `已复制 ${keptResults.value.length} 张图片链接` : '链接已复制'))
    .catch(() => ElMessage.warning('复制失败，请手动复制'))
}

// 分享海报弹窗状态
const posterDialog = ref(false)
const posterLoading = ref(false)
const posterDataUrl = ref('')
// 海报图片选择（多模型时）
const posterSelectedId = ref('')

/** 生成分享海报：效果图 + 二维码（扫码跳本站该作品） */
async function onGeneratePoster() {
  if (!resultUrl.value) return
  posterDialog.value = true
  posterLoading.value = true
  posterDataUrl.value = ''
  // 默认选择第一张
  if (!posterSelectedId.value && keptResults.value.length > 0) {
    posterSelectedId.value = keptResults.value[0].resultId
  }
  try {
    const shareUrl = `${window.location.origin}/share/${taskId.value}`
    // 获取选中的图片 URL
    const selectedResult = keptResults.value.find(r => r.resultId === posterSelectedId.value)
    const imageUrl = selectedResult?.resultUrl || resultUrl.value
    posterDataUrl.value = await generateSharePoster({
      imageUrl,
      shareUrl,
    })
  } catch {
    ElMessage.error('海报生成失败，请重试')
  } finally {
    posterLoading.value = false
  }
}

/** 切换海报图片选择 */
function onPosterImageChange() {
  // 重新生成海报
  if (posterDialog.value && posterSelectedId.value) {
    onGeneratePoster()
  }
}

/** 下载生成的分享海报 */
function onDownloadPoster() {
  if (!posterDataUrl.value) return
  downloadDataUrl(posterDataUrl.value, `photo-style-poster-${taskId.value}.png`)
}

/** 返回上一页（历史记录进来则回列表，首页进来则回首页）；无历史栈时回首页兜底 */
function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/')
  }
}
</script>

<template>
  <div class="mx-auto max-w-5xl px-4 py-8">
    <!-- 顶部栏：温暖底，任务 ID 用等宽字体 -->
    <div class="result-topbar ink-fade">
      <el-button :icon="ArrowLeft" class="result-topbar__back" @click="goBack">返回</el-button>
      <h1 class="result-topbar__title font-display">转换结果</h1>
      <span class="result-topbar__task font-mono-label">任务 #{{ taskId }}</span>
    </div>

    <!-- 进行中：动画 + 朱砂进度条 -->
    <div v-if="!isDone && !isFailed" class="progress-card">
      <!-- 动画区域 -->
      <div class="progress-anim">
        <!-- 水墨圆环动画 -->
        <div class="ink-ring">
          <svg viewBox="0 0 120 120" class="ink-ring__svg">
            <circle cx="60" cy="60" r="50" class="ink-ring__track" />
            <circle cx="60" cy="60" r="50" class="ink-ring__fill" />
          </svg>
          <span class="ink-ring__seal font-display">绘</span>
        </div>
        <!-- 漂浮墨点 -->
        <span class="ink-dot ink-dot--1"></span>
        <span class="ink-dot ink-dot--2"></span>
        <span class="ink-dot ink-dot--3"></span>
        <span class="ink-dot ink-dot--4"></span>
        <span class="ink-dot ink-dot--5"></span>
      </div>
      <el-progress
        :percentage="task?.progress ?? 0"
        :status="task?.status === 'running' ? undefined : 'warning'"
        :stroke-width="6"
        class="progress-card__bar"
      />
      <p class="progress-card__stage">{{ stageLabel }}</p>
      <p :key="funMsgIndex" class="progress-card__fun-msg">{{ funMessage }}</p>
      <p class="progress-card__hint">预计需要 30~60 秒，请耐心等待</p>
    </div>

    <!-- 失败 / 取消 -->
    <EmptyState v-else-if="isFailed" text="任务失败或已取消" />

    <!-- 成功：原图与效果图两列对比，点击可预览 -->
    <div v-else>
      <div class="paper-frame">
        <div v-if="originalUrl || resultUrl" class="result-grid">
          <!-- 原图列 -->
          <div class="result-col">
            <div class="result-col__label font-display">
              <span class="ink-stamp">前</span>
              <span>原图</span>
            </div>
            <div class="result-col__img-wrap">
              <el-image
                v-if="originalUrl"
                :src="originalUrl"
                :preview-src-list="previewList"
                :initial-index="0"
                fit="contain"
                class="result-col__img"
                preview-teleported
                hide-on-click-modal
              >
                <template #placeholder>
                  <div class="result-col__placeholder">加载中…</div>
                </template>
              </el-image>
              <div v-else class="result-col__placeholder">原图未加载</div>
            </div>
          </div>

          <!-- 效果图列 -->
          <div class="result-col">
            <div class="result-col__label font-display">
              <span class="ink-stamp">后</span>
              <span>效果图</span>
              <el-tag v-if="firstProviderLabel" size="small" class="result-col__provider-tag">
                {{ firstProviderLabel }}
              </el-tag>
              <span class="result-col__label-hint">点击预览大图</span>
            </div>
            <div class="result-col__img-wrap result-col__img-wrap--effect">
              <el-image
                v-if="resultUrl"
                :src="resultUrl"
                :preview-src-list="previewList"
                :initial-index="previewInitialIndex"
                fit="contain"
                class="result-col__img"
                preview-teleported
                hide-on-click-modal
                @click="onPreviewResult"
              >
                <template #placeholder>
                  <div class="result-col__placeholder">生成中…</div>
                </template>
              </el-image>
              <div v-else class="result-col__placeholder">暂无效果图</div>
              <!-- 悬停放大提示 -->
              <div v-if="resultUrl" class="result-col__zoom-hint">
                <el-icon><ZoomIn /></el-icon>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 多模型结果：展示所有保留的结果，可删除不想要的 -->
      <div v-if="hasMultiResults" class="multi-results-grid">
        <div
          v-for="(r, idx) in keptResults"
          :key="r.resultId"
          class="multi-results-item"
          :class="{ 'multi-results-item--active': idx === 0 }"
        >
          <span class="multi-results-item__tag">
            {{ providerLabel(r.provider) }}
          </span>
          <!-- 删除按钮：至少保留 1 张 -->
          <button
            v-if="keptResults.length > 1"
            class="multi-results-item__delete"
            :disabled="deletingResultId === r.resultId"
            @click.stop="onRemoveResult(r.resultId)"
          >
            <el-icon :size="14"><Close /></el-icon>
          </button>
          <el-image
            :src="r.resultUrl"
            :preview-src-list="previewList"
            :initial-index="originalUrl ? idx + 1 : idx"
            fit="cover"
            class="multi-results-item__img"
            preview-teleported
            @click="switchMainResult(idx)"
          />
        </div>
      </div>
      <!-- 单结果时显示删除按钮 -->
      <div v-else-if="keptResults.length === 1 && keptResults[0]" class="single-result-actions">
        <button
          class="single-result-delete"
          :disabled="deletingResultId === keptResults[0].resultId"
          @click="onRemoveResult(keptResults[0].resultId)"
        >
          <el-icon :size="12"><Close /></el-icon>
          <span>删除此结果</span>
        </button>
      </div>

      <div class="mt-5 flex flex-wrap justify-center gap-3">
        <el-button :icon="Download" type="primary" @click="onDownload">下载</el-button>
        <el-button
          :icon="Star"
          :type="favorite ? 'warning' : 'default'"
          :loading="favoriting"
          @click="onFavorite"
        >
          {{ favorite ? (hasMultiResults ? '已收藏全部' : '已收藏') : (hasMultiResults ? '收藏全部' : '收藏') }}
        </el-button>
        <el-button :icon="Share" class="result-secondary-btn" @click="onShare">分享</el-button>
        <el-button
          v-if="resultUrl"
          :icon="Picture"
          class="result-secondary-btn"
          :disabled="posterLoading"
          @click="onGeneratePoster"
        >
          生成分享海报
        </el-button>
        <el-button
          v-if="originalPrompt"
          :icon="Refresh"
          class="result-secondary-btn"
          :disabled="regenerating"
          @click="showRegenerate = !showRegenerate"
        >
          重新转换
        </el-button>
      </div>

      <!-- 重新转换（带意见）面板：基于上一次提示词叠加意见重新生成 -->
      <transition name="el-fade-in">
        <div v-if="showRegenerate && originalPrompt" class="regen-panel">
          <div class="regen-panel__head">
            <span class="regen-panel__dot" aria-hidden="true"></span>
            <div>
              <div class="regen-panel__title font-display">修改意见 · 重新转换</div>
              <p class="regen-panel__hint">
                将基于上一次生成所用的完整提示词，叠加你的意见后重新生成，无需重新分析图片。
              </p>
            </div>
          </div>

          <!-- 快捷建议：点击一键填入，降低写意见的门槛 -->
          <div class="regen-chips">
            <button
              v-for="s in FEEDBACK_SUGGESTIONS"
              :key="s"
              type="button"
              class="regen-chip"
              :class="{ 'regen-chip--on': feedback.includes(s) }"
              @click="appendFeedback(s)"
            >
              {{ s }}
            </button>
          </div>

          <el-input
            v-model="feedback"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            resize="none"
            placeholder="也可自行输入，例如：背景再亮一些；冰箱贴稍微放大；文字位置再往下一点…"
          />
          <div class="regen-panel__actions">
            <el-button
              type="primary"
              :loading="regenerating"
              :disabled="!feedback.trim()"
              @click="onRegenerate"
            >
              重新生成
            </el-button>
            <el-button :disabled="regenerating" @click="showRegenerate = false">取消</el-button>
          </div>
        </div>
      </transition>
    </div>

    <!-- 分享海报弹窗：预览 + 下载 -->
    <el-dialog
      v-model="posterDialog"
      title="分享海报"
      width="min(480px, 92vw)"
      align-center
      class="poster-dialog-wrap"
    >
      <div class="poster-dialog">
        <!-- 多模型时显示图片选择条 -->
        <div v-if="hasMultiResults" class="poster-picker">
          <div
            v-for="r in keptResults"
            :key="r.resultId"
            class="poster-picker__item"
            :class="{ 'poster-picker__item--active': posterSelectedId === r.resultId }"
            @click="posterSelectedId = r.resultId; onPosterImageChange()"
          >
            <img :src="r.resultUrl" :alt="providerLabel(r.provider)" />
            <span class="poster-picker__label">{{ providerLabel(r.provider) }}</span>
          </div>
        </div>
        <div v-if="posterLoading" class="poster-dialog__loading">
          <el-icon class="is-loading" :size="22"><Loading /></el-icon>
          <span>海报生成中…</span>
        </div>
        <img
          v-else-if="posterDataUrl"
          :src="posterDataUrl"
          class="poster-dialog__img"
          alt="分享海报"
        />
      </div>
      <template #footer>
        <el-button :disabled="posterLoading" @click="posterDialog = false">关闭</el-button>
        <el-button
          type="primary"
          :disabled="!posterDataUrl"
          @click="onDownloadPoster"
        >
          下载海报
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* 顶部栏：下边框分隔，标题居中，任务号等宽 */
.result-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 20px;
  margin-bottom: 28px;
  border-bottom: 1px solid rgba(156, 150, 139, 0.2);
}
.result-topbar__back {
  --el-button-text-color: var(--color-text-secondary);
  --el-button-hover-text-color: var(--color-primary);
  --el-button-bg-color: transparent;
  --el-button-border-color: var(--color-border);
  --el-button-hover-bg-color: transparent;
  --el-button-hover-border-color: var(--color-primary);
}
.result-topbar__title {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.06em;
}
.result-topbar__task {
  font-size: 12px;
  color: var(--color-text-secondary);
}

/* 进度卡片：纸面卡片，无重阴影 */
.progress-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 48px 24px 40px;
  text-align: center;
}
.progress-card__bar {
  max-width: 360px;
  margin: 0 auto;
}
.progress-card__stage {
  margin-top: 20px;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: 0.06em;
  animation: stage-pulse 2.4s ease-in-out infinite;
}
.progress-card__hint {
  margin-top: 8px;
  font-size: 13px;
  color: var(--color-text-secondary);
  letter-spacing: 0.04em;
}
.progress-card__fun-msg {
  margin-top: 12px;
  font-size: 14px;
  color: var(--color-primary);
  font-style: italic;
  letter-spacing: 0.03em;
  min-height: 1.5em;
  animation: fun-msg-fade 0.6s ease-in-out;
}

@keyframes fun-msg-fade {
  0% { opacity: 0; transform: translateY(4px); }
  100% { opacity: 1; transform: translateY(0); }
}

/* ====== 转换动画区域 ====== */
.progress-anim {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 140px;
  height: 140px;
  margin: 0 auto 28px;
}

/* 水墨旋转环 */
.ink-ring {
  position: relative;
  width: 120px;
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.ink-ring__svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
  animation: ring-rotate 3s linear infinite;
}
.ink-ring__track {
  fill: none;
  stroke: var(--color-border);
  stroke-width: 3;
}
.ink-ring__fill {
  fill: none;
  stroke: var(--color-primary);
  stroke-width: 3;
  stroke-linecap: round;
  stroke-dasharray: 314;
  stroke-dashoffset: 80;
  animation: ring-dash 2s ease-in-out infinite alternate;
}

/* 中心朱印章 */
.ink-ring__seal {
  position: relative;
  z-index: 1;
  width: 52px;
  height: 52px;
  border-radius: 6px;
  background: var(--color-primary);
  color: #fff;
  font-size: 26px;
  font-weight: 700;
  line-height: 52px;
  text-align: center;
  box-shadow: var(--shadow-seal);
  animation: seal-breathe 2.8s ease-in-out infinite;
}
.ink-ring__seal::after {
  content: "";
  position: absolute;
  right: 3px;
  bottom: 3px;
  width: 7px;
  height: 7px;
  background: rgba(255, 255, 255, 0.18);
  border-radius: 50%;
}

/* 漂浮墨点 */
.ink-dot {
  position: absolute;
  border-radius: 50%;
  background: var(--color-primary);
  opacity: 0;
  animation: dot-float 3s ease-in-out infinite;
}
.ink-dot--1 { width: 6px; height: 6px; top: 8px; left: 20px; animation-delay: 0s; }
.ink-dot--2 { width: 4px; height: 4px; top: 20px; right: 12px; animation-delay: 0.6s; }
.ink-dot--3 { width: 5px; height: 5px; bottom: 16px; left: 10px; animation-delay: 1.2s; }
.ink-dot--4 { width: 3px; height: 3px; bottom: 8px; right: 24px; animation-delay: 1.8s; }
.ink-dot--5 { width: 5px; height: 5px; top: 50%; left: 4px; animation-delay: 2.4s; }

/* ====== 动画关键帧 ====== */
@keyframes ring-rotate {
  to { transform: rotate(270deg); }
}
@keyframes ring-dash {
  0%   { stroke-dashoffset: 240; }
  100% { stroke-dashoffset: 40; }
}
@keyframes seal-breathe {
  0%, 100% { transform: scale(1); opacity: 1; }
  50%      { transform: scale(1.08); opacity: 0.88; }
}
@keyframes dot-float {
  0%        { opacity: 0; transform: scale(0.5) translateY(0); }
  30%       { opacity: 0.6; }
  70%       { opacity: 0.4; }
  100%      { opacity: 0; transform: scale(1.2) translateY(-18px); }
}
@keyframes stage-pulse {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.55; }
}

/* 纸面相框：温暖边框 + 极淡内衬 + 纸张纹理 */
.paper-frame {
  position: relative;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
  overflow: hidden;
  animation: card-fade-in 0.5s ease-out;
}
.paper-frame::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.02;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  border-radius: inherit;
}

/* 两列对比布局：原图 / 效果图 */
.result-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.result-col {
  display: flex;
  flex-direction: column;
}
.result-col__label {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 12px;
  letter-spacing: 0.06em;
  display: flex;
  align-items: center;
  gap: 10px;
}
.result-col__label-hint {
  font-size: 11px;
  font-weight: 400;
  color: var(--color-text-secondary);
  opacity: 0.7;
  letter-spacing: 0.02em;
  margin-left: auto;
}
.result-col__img-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 3 / 4;
  background: #fff;
  border: 1px solid rgba(156, 150, 139, 0.18);
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.25s ease;
}
.result-col__img-wrap--effect {
  cursor: zoom-in;
}
.result-col__img-wrap--effect:hover {
  box-shadow: var(--shadow-md);
}
.result-col__img {
  width: 100%;
  height: 100%;
  display: block;
}
.result-col__placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--color-text-secondary);
  opacity: 0.6;
}
/* 悬停放大提示：右下角朱砂小标 */
.result-col__zoom-hint {
  position: absolute;
  right: 10px;
  bottom: 10px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.85);
  color: var(--color-primary);
  border-radius: 50%;
  border: 1px solid rgba(200, 68, 43, 0.25);
  font-size: 16px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.2s ease;
}
.result-col__img-wrap--effect:hover .result-col__zoom-hint {
  opacity: 1;
}

/* 移动端：两列改单列 */
@media (max-width: 640px) {
  .result-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}

/* 次级按钮：温暖石灰描边，去除冷蓝默认 */
.result-secondary-btn {
  --el-button-text-color: var(--color-text-secondary);
  --el-button-bg-color: transparent;
  --el-button-border-color: var(--color-border);
  --el-button-hover-text-color: var(--color-text);
  --el-button-hover-bg-color: var(--color-accent-bg);
  --el-button-hover-border-color: var(--stone-dark, #7a7468);
}

/* 重新转换面板：纸面卡片，与原图/效果图相框呼应 */
.regen-panel {
  margin: 24px auto 0;
  max-width: 680px;
  padding: 22px 22px 20px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}
/* 面板头部：朱砂小点 + 标题/说明 */
.regen-panel__head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 14px;
}
.regen-panel__dot {
  flex-shrink: 0;
  width: 10px;
  height: 10px;
  margin-top: 6px;
  border-radius: 50%;
  background: var(--color-primary);
  box-shadow: var(--shadow-seal);
}
.regen-panel__title {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.06em;
}
.regen-panel__hint {
  font-size: 12px;
  line-height: 1.6;
  color: var(--color-text-secondary);
  opacity: 0.75;
  margin-top: 4px;
  letter-spacing: 0.02em;
}
/* 快捷建议 chips：点击填入意见 */
.regen-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}
.regen-chip {
  appearance: none;
  cursor: pointer;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  padding: 5px 14px;
  font-size: 13px;
  color: var(--color-text-secondary);
  font-family: var(--font-body);
  transition: all 0.18s ease;
}
.regen-chip:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.regen-chip--on {
  background: rgba(200, 68, 43, 0.1);
  border-color: var(--color-primary);
  color: var(--color-primary);
  font-weight: 500;
}
.regen-panel__actions {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
/* 重新生成主按钮：复用朱砂强调色 */
.regen-panel__actions .el-button--primary {
  --el-button-bg-color: var(--color-primary);
  --el-button-border-color: var(--color-primary);
  --el-button-hover-bg-color: var(--color-primary-dark, #a8361f);
  --el-button-hover-border-color: var(--color-primary-dark, #a8361f);
}

/* 分享海报弹窗 */
/* 分享海报弹窗：长海报允许弹窗内滚动查看 */
.poster-dialog-wrap :deep(.el-dialog__body) {
  max-height: 72vh;
  overflow: auto;
}
.poster-dialog {
  min-height: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.poster-dialog__loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: var(--color-text-secondary);
  font-size: 14px;
  letter-spacing: 0.04em;
}
.poster-dialog__img {
  width: 100%;
  display: block;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  background: var(--color-bg-card);
  /* 朱砂描边与结果页相框呼应 */
  border: 1px solid var(--color-border);
}

/* 朱砂进度条覆盖：替换 Element Plus 默认蓝 */
:deep(.el-progress-bar__inner) {
  background-color: var(--color-primary);
}
:deep(.el-progress-bar__outer) {
  background-color: rgba(156, 150, 139, 0.2);
}

@media (max-width: 640px) {
  .result-topbar__title {
    font-size: 17px;
  }
  .result-topbar__task {
    font-size: 11px;
  }
}

/* 卡片入场动画 */
@keyframes card-fade-in {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Provider 标签：效果图标题行内显示 —— 朱砂小印风格 */
.result-col__provider-tag {
  margin-left: 8px;
  vertical-align: middle;
  --el-tag-bg-color: rgba(200, 68, 43, 0.08);
  --el-tag-border-color: rgba(200, 68, 43, 0.2);
  --el-tag-text-color: var(--color-primary-dark);
  font-family: var(--font-display);
  letter-spacing: 0.04em;
}

/* 多模型结果网格 —— 宣纸卷轴式横滑 */
.multi-results-grid {
  display: flex;
  gap: 18px;
  margin-top: 24px;
  padding: 4px 2px 12px;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  scrollbar-width: thin;
  scrollbar-color: var(--color-border) transparent;
}
.multi-results-grid::-webkit-scrollbar {
  height: 4px;
}
.multi-results-grid::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 2px;
}
.multi-results-item {
  position: relative;
  flex: 0 0 180px;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1.5px solid var(--color-border);
  background: var(--color-bg-card);
  box-shadow: var(--shadow-sm);
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
  scroll-snap-align: start;
}
.multi-results-item:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
}
.multi-results-item--active {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px rgba(200, 68, 43, 0.12), var(--shadow-sm);
}
.multi-results-item__tag {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 1;
  font-size: 10px;
  font-family: var(--font-display);
  letter-spacing: 0.06em;
  padding: 2px 7px;
  border-radius: 2px;
  background: rgba(28, 28, 26, 0.6);
  color: #f5f2ec;
  backdrop-filter: blur(4px);
  white-space: nowrap;
  pointer-events: none;
}
.multi-results-item__img {
  width: 180px;
  height: 240px;
  display: block;
  cursor: pointer;
}

@media (max-width: 640px) {
  .multi-results-item {
    flex: 0 0 140px;
  }
  .multi-results-item__img {
    width: 140px;
    height: 187px;
  }
}

/* 删除按钮：右上角墨底半透明圆形 */
.multi-results-item__delete {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(28, 28, 26, 0.6);
  color: #f5f2ec;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  backdrop-filter: blur(4px);
}
.multi-results-item__delete:hover:not(:disabled) {
  background: var(--color-primary);
  transform: scale(1.1);
}
.multi-results-item__delete:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 单结果时的删除按钮 */
.single-result-actions {
  display: flex;
  justify-content: center;
  margin-top: 12px;
}
.single-result-delete {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.single-result-delete:hover:not(:disabled) {
  color: var(--color-primary);
  border-color: var(--color-primary);
}
.single-result-delete:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 海报图片选择条 */
.poster-picker {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--color-bg);
  border-radius: var(--radius-md);
  overflow-x: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--color-border) transparent;
}
.poster-picker::-webkit-scrollbar {
  height: 4px;
}
.poster-picker::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 2px;
}
.poster-picker__item {
  position: relative;
  flex: 0 0 80px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 2px solid transparent;
  cursor: pointer;
  transition: border-color 0.2s ease;
}
.poster-picker__item:hover {
  border-color: var(--color-border);
}
.poster-picker__item--active {
  border-color: var(--color-primary);
}
.poster-picker__item img {
  width: 80px;
  height: 100px;
  object-fit: cover;
  display: block;
}
.poster-picker__label {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 2px 4px;
  font-size: 10px;
  font-family: var(--font-display);
  background: rgba(28, 28, 26, 0.7);
  color: #f5f2ec;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
