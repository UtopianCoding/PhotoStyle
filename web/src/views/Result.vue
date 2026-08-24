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
// 重新转换时选择的 Provider（空字符串=全部模型，非空=指定模型）
const regenProvider = ref('')

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
    provider: regenProvider.value,
  })
  if (newTask) {
    // 跳转到新的任务结果页（useTaskPolling 会在路由参数变化时自动重拉）
    router.push(`/result/${newTask.taskId}`)
    showRegenerate.value = false
    feedback.value = ''
    regenProvider.value = ''
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

// 仍在处理中的 Provider 列表
const pendingProviders = computed(() => task.value?.pendingProviders ?? [])
// 是否有 Provider 仍在处理中
const hasPending = computed(() => pendingProviders.value.length > 0)
// 是否有已完成的中间结果（running 状态下已有部分结果）
const hasPartialResults = computed(
  () => task.value?.status === 'running' && keptResults.value.length > 0,
)
// 部分结果预览列表（原图 + 已完成结果）
const partialPreviewList = computed(() => {
  const list: string[] = []
  if (originalUrl.value) list.push(originalUrl.value)
  keptResults.value.forEach(r => list.push(r.resultUrl))
  return list
})

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

    <!-- 失败 / 取消 -->
    <div v-if="isFailed">
      <EmptyState text="任务失败或已取消" />
    </div>

    <!-- 部分结果：已有 Provider 完成，其他仍在处理 -->
    <div v-else-if="hasPartialResults" class="partial-results">
      <!-- 进度条：朱砂描边进度 + 完成数 -->
      <div class="partial-results__progress-bar">
        <div class="partial-results__progress-track">
          <div
            class="partial-results__progress-fill"
            :style="{ width: `${Math.round(keptResults.length / (task?.providers ?? []).length * 100)}%` }"
          ></div>
        </div>
        <span class="partial-results__progress-label">
          {{ keptResults.length }} / {{ (task?.providers ?? []).length }} 完成
        </span>
      </div>

      <!-- 效果图画廊：原图 + 已完成结果 + 待处理占位 -->
      <div class="partial-results__gallery">
        <!-- 原图列 -->
        <div class="partial-results__frame partial-results__frame--source">
          <div class="partial-results__seal font-display">前</div>
          <div class="partial-results__label font-display">原图</div>
          <div class="partial-results__img-wrap">
            <el-image
              v-if="originalUrl"
              :src="originalUrl"
              fit="contain"
              class="partial-results__img"
              preview-teleported
              :preview-src-list="partialPreviewList"
              :initial-index="0"
            />
          </div>
        </div>

        <!-- 已完成的结果 -->
        <div
          v-for="(r, idx) in keptResults"
          :key="r.resultId"
          class="partial-results__frame partial-results__frame--done ink-fade"
        >
          <div class="partial-results__seal partial-results__seal--done font-display">后</div>
          <div class="partial-results__label font-display">
            {{ providerLabel(r.provider) }}
          </div>
          <div class="partial-results__img-wrap">
            <el-image
              :src="r.resultUrl"
              fit="contain"
              class="partial-results__img"
              preview-teleported
              :preview-src-list="partialPreviewList"
              :initial-index="originalUrl ? idx + 1 : idx"
            />
          </div>
        </div>

        <!-- 仍在处理中的 Provider 占位 -->
        <div
          v-for="pid in pendingProviders"
          :key="`pending-${pid}`"
          class="partial-results__frame partial-results__frame--pending"
        >
          <div class="partial-results__label font-display partial-results__label--pending">
            {{ providerLabel(pid) }}
          </div>
          <div class="partial-results__img-wrap partial-results__img-wrap--pending">
            <div class="partial-results__ink-anim">
              <span class="partial-results__ink-dot partial-results__ink-dot--1"></span>
              <span class="partial-results__ink-dot partial-results__ink-dot--2"></span>
              <span class="partial-results__ink-dot partial-results__ink-dot--3"></span>
            </div>
            <span class="partial-results__pending-hint font-display">绘制中</span>
          </div>
        </div>
      </div>

      <!-- 趣味话语 -->
      <p :key="funMsgIndex" class="progress-card__fun-msg" style="text-align:center; margin-top:20px;">{{ funMessage }}</p>
    </div>

    <!-- 进行中：动画 + 朱砂进度条（尚无结果时的等待页） -->
    <div v-else-if="!isDone" class="progress-card">
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

    <!-- 成功：根据结果数量选择布局 -->
    <div v-else class="result-reveal">
      <!-- 揭晓横幅：任务完成提示 -->
      <div class="reveal-banner">
        <div class="reveal-banner__icon">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="14" stroke="currentColor" stroke-width="1.5" opacity="0.3"/>
            <path d="M11 16.5L14.5 20L21 13" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <div class="reveal-banner__content">
          <h2 class="reveal-banner__title">转换完成</h2>
          <p class="reveal-banner__subtitle">你的照片已焕然一新</p>
        </div>
      </div>

      <!-- ===== 单模型：经典两列对比 ===== -->
      <div v-if="!hasMultiResults" class="comparison-stage">
        <div v-if="originalUrl || resultUrl" class="comparison-grid">
          <!-- 原图列 -->
          <div class="comparison-col comparison-col--before">
            <div class="comparison-label">
              <span class="comparison-label__seal comparison-label__seal--before">前</span>
              <span class="comparison-label__text">原图</span>
            </div>
            <div class="comparison-frame">
              <el-image
                v-if="originalUrl"
                :src="originalUrl"
                :preview-src-list="previewList"
                :initial-index="0"
                fit="contain"
                class="comparison-frame__img"
                preview-teleported
                hide-on-click-modal
              >
                <template #placeholder>
                  <div class="comparison-frame__placeholder">加载中…</div>
                </template>
              </el-image>
              <div v-else class="comparison-frame__placeholder">原图未加载</div>
            </div>
          </div>

          <!-- 转换箭头 -->
          <div class="comparison-arrow">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M5 12H19M19 12L13 6M19 12L13 18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>

          <!-- 效果图列 -->
          <div class="comparison-col comparison-col--after">
            <div class="comparison-label">
              <span class="comparison-label__seal comparison-label__seal--after">后</span>
              <span class="comparison-label__text">效果图</span>
              <el-tag v-if="firstProviderLabel" size="small" class="comparison-label__provider">
                {{ firstProviderLabel }}
              </el-tag>
              <span class="comparison-label__hint">点击预览</span>
            </div>
            <div class="comparison-frame comparison-frame--effect">
              <el-image
                v-if="resultUrl"
                :src="resultUrl"
                :preview-src-list="previewList"
                :initial-index="previewInitialIndex"
                fit="contain"
                class="comparison-frame__img"
                preview-teleported
                hide-on-click-modal
                @click="onPreviewResult"
              >
                <template #placeholder>
                  <div class="comparison-frame__placeholder">生成中…</div>
                </template>
              </el-image>
              <div v-else class="comparison-frame__placeholder">暂无效果图</div>
              <div v-if="resultUrl" class="comparison-frame__overlay">
                <el-icon><ZoomIn /></el-icon>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ===== 多模型：原图 + 全部效果图并排网格 ===== -->
      <div v-else class="multi-results-layout">
        <div class="multi-results__grid" :class="`multi-results__grid--${Math.min(keptResults.length, 2)}`">
          <!-- 原图列 -->
          <div v-if="originalUrl" class="multi-results__card multi-results__card--source">
            <div class="multi-results__card-head font-display">
              <span class="multi-results__card-seal multi-results__card-seal--source">前</span>
              <span>原图</span>
            </div>
            <div class="multi-results__card-body">
              <el-image
                :src="originalUrl"
                :preview-src-list="previewList"
                :initial-index="0"
                fit="contain"
                class="multi-results__card-img"
                preview-teleported
                hide-on-click-modal
              />
              <div class="multi-results__card-zoom">
                <el-icon><ZoomIn /></el-icon>
              </div>
            </div>
          </div>

          <!-- 效果图卡片 -->
          <div
            v-for="(r, idx) in keptResults"
            :key="r.resultId"
            class="multi-results__card"
          >
            <div class="multi-results__card-head font-display">
              <span class="multi-results__card-seal">后</span>
              <span>{{ providerLabel(r.provider) }}</span>
              <span class="multi-results__card-hint">点击预览大图</span>
            </div>
            <div class="multi-results__card-body">
              <el-image
                :src="r.resultUrl"
                :preview-src-list="previewList"
                :initial-index="originalUrl ? idx + 1 : idx"
                fit="contain"
                class="multi-results__card-img"
                preview-teleported
                hide-on-click-modal
              >
                <template #placeholder>
                  <div class="result-col__placeholder">加载中…</div>
                </template>
              </el-image>
              <div class="multi-results__card-zoom">
                <el-icon><ZoomIn /></el-icon>
              </div>
            </div>
            <!-- 删除按钮 -->
            <button
              v-if="keptResults.length > 1"
              class="multi-results__card-delete"
              :disabled="deletingResultId === r.resultId"
              @click.stop="onRemoveResult(r.resultId)"
            >
              <el-icon :size="14"><Close /></el-icon>
            </button>
          </div>
        </div>
      </div>

      <!-- 单结果时显示删除按钮 -->
      <div v-if="keptResults.length === 1 && keptResults[0] && !hasMultiResults" class="single-result-actions">
        <button
          class="single-result-delete"
          :disabled="deletingResultId === keptResults[0].resultId"
          @click="onRemoveResult(keptResults[0].resultId)"
        >
          <el-icon :size="12"><Close /></el-icon>
          <span>删除此结果</span>
        </button>
      </div>

      <!-- 操作按钮区域：编辑杂志风格的工具栏 -->
      <div class="action-toolbar">
        <!-- 主要操作组 -->
        <div class="action-group action-group--primary">
          <el-button :icon="Download" type="primary" size="large" @click="onDownload">
            下载
          </el-button>
          <el-button
            :icon="Star"
            size="large"
            :type="favorite ? 'warning' : 'default'"
            :loading="favoriting"
            @click="onFavorite"
          >
            {{ favorite ? (hasMultiResults ? '已收藏全部' : '已收藏') : (hasMultiResults ? '收藏全部' : '收藏') }}
          </el-button>
        </div>

        <!-- 次要操作组 -->
        <div class="action-group action-group--secondary">
          <el-button :icon="Share" text @click="onShare">
            分享
          </el-button>
          <el-button
            v-if="resultUrl"
            :icon="Picture"
            text
            :disabled="posterLoading"
            @click="onGeneratePoster"
          >
            生成海报
          </el-button>
          <el-button
            v-if="originalPrompt"
            :icon="Refresh"
            text
            :disabled="regenerating"
            @click="showRegenerate = !showRegenerate"
          >
            重新转换
          </el-button>
        </div>
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

          <!-- 多模型时：选择基于哪个模型重新转换 -->
          <div v-if="hasMultiResults" class="regen-provider-select">
            <div class="regen-provider-select__label font-display">选择模型</div>
            <div class="regen-provider-select__options">
              <button
                type="button"
                class="regen-provider-option"
                :class="{ 'regen-provider-option--active': regenProvider === '' }"
                @click="regenProvider = ''"
              >
                全部模型
              </button>
              <button
                v-for="r in keptResults"
                :key="r.resultId"
                type="button"
                class="regen-provider-option"
                :class="{ 'regen-provider-option--active': regenProvider === r.provider }"
                @click="regenProvider = r.provider"
              >
                {{ providerLabel(r.provider) }}
              </button>
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
      width="min(520px, 92vw)"
      align-center
      class="poster-dialog-wrap"
    >
      <div class="poster-dialog">
        <!-- 多模型时显示图片选择条 -->
        <div v-if="hasMultiResults" class="poster-picker-wrap">
          <div class="poster-picker__label-text font-display">选择效果图</div>
          <div class="poster-picker">
            <div
              v-for="r in keptResults"
              :key="r.resultId"
              class="poster-picker__item"
              :class="{ 'poster-picker__item--active': posterSelectedId === r.resultId }"
              @click="posterSelectedId = r.resultId; onPosterImageChange()"
            >
              <img :src="r.resultUrl" :alt="providerLabel(r.provider)" />
              <span class="poster-picker__item-label">{{ providerLabel(r.provider) }}</span>
              <span v-if="posterSelectedId === r.resultId" class="poster-picker__check">✓</span>
            </div>
          </div>
        </div>
        <div class="poster-preview">
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

/* ═══════════════════════════════════════════════════════════════════════
   新设计系统：编辑杂志风格的转换结果展示
   ═══════════════════════════════════════════════════════════════════════ */

/* 揭晓容器：入场动画 */
.result-reveal {
  animation: reveal-entrance 0.6s cubic-bezier(0.22, 1, 0.36, 1) both;
}

@keyframes reveal-entrance {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 揭晓横幅：任务完成的仪式感 */
.reveal-banner {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  margin-bottom: 32px;
  background: linear-gradient(135deg, var(--color-bg-card) 0%, rgba(200, 68, 43, 0.03) 100%);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  animation: banner-slide-in 0.5s cubic-bezier(0.22, 1, 0.36, 1) 0.2s both;
}

@keyframes banner-slide-in {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.reveal-banner__icon {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
  border-radius: 50%;
  color: #fff;
  box-shadow: 0 4px 12px rgba(200, 68, 43, 0.25);
}

.reveal-banner__content {
  flex: 1;
}

.reveal-banner__title {
  margin: 0 0 4px 0;
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.02em;
  line-height: 1.3;
}

.reveal-banner__subtitle {
  margin: 0;
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

/* 对比舞台：单模型布局 */
.comparison-stage {
  margin-bottom: 40px;
}

.comparison-grid {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 24px;
  align-items: stretch;
}

@media (max-width: 768px) {
  .comparison-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  .comparison-arrow {
    transform: rotate(90deg);
    justify-self: center;
  }
}

.comparison-col {
  display: flex;
  flex-direction: column;
}

/* 对比标签：编辑杂志风格 */
.comparison-label {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid var(--color-border);
}

.comparison-label__seal {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  border-radius: 4px;
  flex-shrink: 0;
  letter-spacing: 0.04em;
  font-family: var(--font-display);
}

/* 原图印章：温暖的石灰调，如墨石 */
.comparison-label__seal--before {
  background: #e8e4dc;
  color: #6b665e;
  border: 1px solid #d4cec5;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.04);
}

/* 效果图印章：朱砂红，精致而不过于刺眼 */
.comparison-label__seal--after {
  background: linear-gradient(135deg, #d65b3f 0%, #c8442b 100%);
  color: #fff;
  border: 1px solid rgba(168, 54, 31, 0.2);
  box-shadow: 0 2px 6px rgba(200, 68, 43, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.comparison-label__text {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: 0.02em;
  flex: 1;
}

.comparison-label__provider {
  font-size: 12px;
  padding: 4px 10px;
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  border-radius: 12px;
  font-weight: 500;
}

.comparison-label__hint {
  font-size: 12px;
  color: var(--color-text-secondary);
  opacity: 0.7;
}

/* 对比画框：精致的图片容器 */
.comparison-frame {
  position: relative;
  width: 100%;
  aspect-ratio: 3 / 4;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}

.comparison-frame--effect {
  cursor: zoom-in;
  border-color: rgba(200, 68, 43, 0.2);
}

.comparison-frame--effect:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(200, 68, 43, 0.15);
  border-color: rgba(200, 68, 43, 0.4);
}

.comparison-frame__img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
}

.comparison-frame__placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: var(--color-text-secondary);
  opacity: 0.6;
}

.comparison-frame__overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.4);
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.comparison-frame--effect:hover .comparison-frame__overlay {
  opacity: 1;
}

.comparison-frame__overlay svg {
  width: 32px;
  height: 32px;
  color: #fff;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
}

/* 转换箭头：视觉引导 */
.comparison-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary);
  animation: arrow-pulse 2s ease-in-out infinite;
}

@keyframes arrow-pulse {
  0%, 100% {
    opacity: 0.6;
    transform: translateX(0);
  }
  50% {
    opacity: 1;
    transform: translateX(4px);
  }
}

@media (max-width: 768px) {
  @keyframes arrow-pulse {
    0%, 100% {
      opacity: 0.6;
      transform: translateY(0) rotate(90deg);
    }
    50% {
      opacity: 1;
      transform: translateY(4px) rotate(90deg);
    }
  }
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

/* 重新转换：模型选择器 */
.regen-provider-select {
  margin-bottom: 14px;
}
.regen-provider-select__label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 8px;
  letter-spacing: 0.04em;
}
.regen-provider-select__options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.regen-provider-option {
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
.regen-provider-option:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.regen-provider-option--active {
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
  padding: 16px 20px;
}
.poster-dialog {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 16px;
}
.poster-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
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
  max-width: 400px;
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

/* ============ 多模型结果布局 ============ */
.multi-results-layout {
  margin-bottom: 8px;
}

/* 效果图网格：固定 3 列（1 原图 + 最多 2 效果图 / 行） */
.multi-results__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}
.multi-results__grid--2 {
  grid-template-columns: repeat(3, 1fr);
}

/* 效果图卡片 */
.multi-results__card {
  position: relative;
  border-radius: var(--radius-md);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  overflow: hidden;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.multi-results__card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
}
.multi-results__card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: 0.06em;
  border-bottom: 1px solid var(--color-border);
}
/* 多模型效果图印章：朱砂红渐变 */
.multi-results__card-seal {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 3px;
  background: linear-gradient(135deg, #d65b3f 0%, #c8442b 100%);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
  box-shadow: 0 1px 3px rgba(200, 68, 43, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.1);
  font-family: var(--font-display);
}
/* 原图印章：温暖石灰调 */
.multi-results__card-seal--source {
  background: #e8e4dc;
  color: #6b665e;
  border: 1px solid #d4cec5;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.04);
}
.multi-results__card-hint {
  margin-left: auto;
  font-size: 11px;
  font-weight: 400;
  color: var(--color-text-placeholder);
  letter-spacing: 0.03em;
}
.multi-results__card-body {
  position: relative;
  aspect-ratio: 3/4;
  background: var(--color-bg);
  overflow: hidden;
}
.multi-results__card-img {
  width: 100%;
  height: 100%;
  display: block;
  cursor: pointer;
}
.multi-results__card-zoom {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(28, 28, 26, 0.25);
  color: #fff;
  font-size: 28px;
  opacity: 0;
  transition: opacity 0.25s ease;
  pointer-events: none;
}
.multi-results__card:hover .multi-results__card-zoom {
  opacity: 1;
}

/* 卡片删除按钮 */
.multi-results__card-delete {
  position: absolute;
  top: 44px;
  right: 8px;
  z-index: 2;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: rgba(28, 28, 26, 0.55);
  color: #f5f2ec;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  backdrop-filter: blur(4px);
}
.multi-results__card-delete:hover:not(:disabled) {
  background: var(--color-primary);
  transform: scale(1.1);
}
.multi-results__card-delete:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .multi-results__grid {
    grid-template-columns: 1fr;
    max-width: 360px;
    margin: 0 auto;
  }
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
.poster-picker-wrap {
  width: 100%;
}
.poster-picker__label-text {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 10px;
  letter-spacing: 0.04em;
}
.poster-picker {
  display: flex;
  gap: 12px;
  padding: 10px 12px;
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
  flex: 0 0 88px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--color-bg-card);
}
.poster-picker__item:hover {
  border-color: var(--color-border);
  transform: translateY(-2px);
}
.poster-picker__item--active {
  border-color: var(--color-primary);
  box-shadow: 0 2px 8px rgba(200, 68, 43, 0.2);
}
.poster-picker__item img {
  width: 88px;
  height: 110px;
  object-fit: cover;
  display: block;
}
.poster-picker__item-label {
  display: block;
  padding: 4px 6px;
  font-size: 11px;
  font-family: var(--font-display);
  background: var(--color-bg-card);
  color: var(--color-text);
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: 0.02em;
}
.poster-picker__item--active .poster-picker__item-label {
  color: var(--color-primary);
  font-weight: 600;
}
.poster-picker__check {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

/* ============ 部分结果区域 ============ */
.partial-results {
  margin-top: 8px;
}

/* 进度条：朱砂填充 + 右侧数字 */
.partial-results__progress-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 24px;
}
.partial-results__progress-track {
  flex: 1;
  height: 4px;
  border-radius: 2px;
  background: var(--color-border);
  overflow: hidden;
}
.partial-results__progress-fill {
  height: 100%;
  border-radius: 2px;
  background: var(--color-primary);
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}
.partial-results__progress-label {
  flex-shrink: 0;
  font-family: var(--font-display);
  font-size: 13px;
  color: var(--color-text-secondary);
  letter-spacing: 0.06em;
  white-space: nowrap;
}

/* 画廊：固定 3 列（1 原图 + 最多 2 效果图 / 行） */
.partial-results__gallery {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

/* 画框：统一卡片，与成功区域的 result-col 风格一致 */
.partial-results__frame {
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-md);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  overflow: hidden;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.partial-results__frame:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
}

/* 画框顶部：朱印章 + 标签 */
.partial-results__seal {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  margin: 12px 0 0 12px;
  border-radius: 4px;
  background: var(--color-text);
  color: var(--color-bg);
  font-size: 13px;
  font-weight: 700;
  box-shadow: 0 1px 4px rgba(28, 28, 26, 0.2);
  flex-shrink: 0;
}
.partial-results__seal--done {
  background: var(--color-primary);
  color: #fff;
  box-shadow: var(--shadow-seal);
}
.partial-results__label {
  margin: 6px 12px 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: 0.06em;
}
.partial-results__label--pending {
  color: var(--color-text-secondary);
}

/* 图片区域 */
.partial-results__img-wrap {
  position: relative;
  aspect-ratio: 3/4;
  background: var(--color-bg);
  overflow: hidden;
}
.partial-results__img {
  width: 100%;
  height: 100%;
  display: block;
  cursor: pointer;
}

/* 待处理占位：水墨晕染动画 */
.partial-results__frame--pending {
  border-style: dashed;
  border-color: rgba(156, 150, 139, 0.35);
  opacity: 0.75;
}
.partial-results__frame--pending:hover {
  opacity: 0.85;
  transform: none;
  box-shadow: none;
}
.partial-results__img-wrap--pending {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
}
.partial-results__ink-anim {
  position: relative;
  width: 48px;
  height: 48px;
}
.partial-results__ink-dot {
  position: absolute;
  border-radius: 50%;
  background: var(--color-primary);
  opacity: 0.3;
  animation: ink-breathe 2.4s ease-in-out infinite;
}
.partial-results__ink-dot--1 {
  width: 12px;
  height: 12px;
  top: 6px;
  left: 8px;
  animation-delay: 0s;
}
.partial-results__ink-dot--2 {
  width: 16px;
  height: 16px;
  top: 18px;
  left: 20px;
  animation-delay: 0.6s;
}
.partial-results__ink-dot--3 {
  width: 10px;
  height: 10px;
  top: 28px;
  left: 6px;
  animation-delay: 1.2s;
}
@keyframes ink-breathe {
  0%, 100% { opacity: 0.15; transform: scale(0.8); }
  50% { opacity: 0.45; transform: scale(1.15); }
}
.partial-results__pending-hint {
  font-size: 13px;
  color: var(--color-text-secondary);
  letter-spacing: 0.08em;
}

@media (max-width: 640px) {
  .partial-results__gallery {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
}

@media (max-width: 420px) {
  .partial-results__gallery {
    grid-template-columns: 1fr;
    max-width: 280px;
    margin: 0 auto;
  }
}

/* ============ 操作工具栏 ============ */
.action-toolbar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  margin-top: 48px;
  padding-top: 36px;
  border-top: 1px solid var(--color-border);
}

.action-group {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  gap: 10px;
}

.action-group--primary {
  gap: 12px;
}

.action-group--secondary {
  gap: 4px;
  padding: 4px 8px;
  background: rgba(156, 150, 139, 0.06);
  border-radius: 24px;
}

/* 主要按钮样式：精致渐变 */
.action-group--primary :deep(.el-button) {
  min-width: 110px;
  height: 40px;
  font-weight: 500;
  font-size: 14px;
  letter-spacing: 0.03em;
  border-radius: 8px;
  transition: all 0.25s cubic-bezier(0.22, 1, 0.36, 1);
}

.action-group--primary :deep(.el-button--primary) {
  background: linear-gradient(135deg, #d65b3f 0%, #c8442b 100%);
  border: none;
  box-shadow: 0 2px 8px rgba(200, 68, 43, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.action-group--primary :deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #e06949 0%, #d65b3f 100%);
  box-shadow: 0 4px 14px rgba(200, 68, 43, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.15);
  transform: translateY(-1px);
}

.action-group--primary :deep(.el-button--warning) {
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
  border: none;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.15);
}

.action-group--primary :deep(.el-button--warning:hover) {
  background: linear-gradient(135deg, #fcd34d 0%, #fbbf24 100%);
  box-shadow: 0 4px 14px rgba(245, 158, 11, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.2);
  transform: translateY(-1px);
}

/* 次要按钮样式：轻盈文本按钮 */
.action-group--secondary :deep(.el-button) {
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 450;
  height: 34px;
  padding: 0 14px;
  border-radius: 17px;
  transition: all 0.2s ease;
}

.action-group--secondary :deep(.el-button:hover) {
  color: var(--color-text);
  background: rgba(156, 150, 139, 0.1);
}

.action-group--secondary :deep(.el-button .el-icon) {
  font-size: 15px;
  margin-right: 4px;
}

/* 按钮分隔符（次要操作组内） */
.action-group--secondary :deep(.el-button + .el-button)::before {
  content: '';
  display: inline-block;
  width: 1px;
  height: 14px;
  margin: 0 6px;
  background: var(--color-border);
  vertical-align: middle;
}

/* 响应式优化 */
@media (max-width: 640px) {
  .action-toolbar {
    gap: 16px;
    margin-top: 36px;
    padding-top: 28px;
  }

  .action-group--primary {
    width: 100%;
    gap: 10px;
  }

  .action-group--primary :deep(.el-button) {
    flex: 1;
    min-width: 0;
    height: 42px;
  }

  .action-group--secondary {
    width: 100%;
    justify-content: center;
    gap: 2px;
    padding: 6px 10px;
  }

  .action-group--secondary :deep(.el-button) {
    font-size: 12px;
    padding: 0 10px;
    height: 32px;
  }

  .action-group--secondary :deep(.el-button .el-icon) {
    font-size: 14px;
  }
}
</style>
