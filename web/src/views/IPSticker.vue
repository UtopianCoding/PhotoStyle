<!-- IP 表情包制作页：左侧会话列表 + 右侧聊天区 -->
<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { ElMessage, ElImageViewer, ElMessageBox } from 'element-plus'
import {
  Picture as PictureIcon,
  Check,
  EditPen,
  Refresh,
  Star,
  ArrowUp,
  Connection,
  Plus,
  ChatDotRound,
  Delete,
} from '@element-plus/icons-vue'
import { useIPStickerChat } from '@/composables/useIPStickerChat'
import { useImageStore } from '@/stores/image'
import { useUserStore } from '@/stores/user'
import { uploadImage } from '@/api/image'
import { listIPSessions, deleteIPSession } from '@/api/ipSticker'
import type { ChatImage, ChatAction, SessionItem } from '@/types/ipSticker'

const chat = useIPStickerChat()
const imageStore = useImageStore()
const userStore = useUserStore()

const inputText = ref('')
const uploading = ref(false)

// 图片预览
const previewVisible = ref(false)
const previewUrl = ref('')

// 修改意见弹窗
const modifyVisible = ref(false)
const modifyText = ref('')

// 重绘弹窗
const redrawVisible = ref(false)
const redrawStickerId = ref('')
const redrawLabel = ref('')
const redrawText = ref('')

const isLoggedIn = computed(() => userStore.isLoggedIn)

// ─── 会话列表 ───
const sessions = ref<SessionItem[]>([])
const sessionsLoading = ref(false)
const activeSessionId = computed(() => chat.sessionId)

async function loadSessions() {
  sessionsLoading.value = true
  try {
    const res = await listIPSessions()
    sessions.value = res.sessions
  } catch { /* ignore */ }
  sessionsLoading.value = false
}

function getSessionTitle(s: SessionItem): string {
  const stepMap: Record<string, string> = {
    awaiting_photo: '新对话',
    generating_base: '生成母版中',
    reviewing_base: '确认母版',
    generating_test: '生成测试中',
    reviewing_test: '确认测试',
    generating_batch: '生成表情中',
    previewing: '预览表情',
    selecting: '筛选表情',
    completed: '已完成',
    abandoned: '已放弃',
  }
  return stepMap[s.status] || '对话'
}

function getSessionIcon(s: SessionItem): string {
  if (s.status === 'completed') return '✓'
  if (s.status.startsWith('generating')) return '⏳'
  return '💬'
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin}分钟前`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour}小时前`
  const diffDay = Math.floor(diffHour / 24)
  if (diffDay < 7) return `${diffDay}天前`
  return `${d.getMonth() + 1}/${d.getDate()}`
}

// 切换会话
function selectSession(s: SessionItem) {
  chat.switchSession(s.session_id)
}

// 新建对话
function handleNewSession() {
  chat.newSession()
}

// 删除对话
async function handleDeleteSession(e: Event, s: SessionItem) {
  e.stopPropagation()
  try {
    await ElMessageBox.confirm('确定要删除这个对话吗？删除后无法恢复。', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteIPSession(s.session_id)
    ElMessage.success('删除成功')
    // 如果删除的是当前对话，新建一个
    if (s.session_id === activeSessionId.value) {
      chat.newSession()
    }
    await loadSessions()
  } catch {
    // 用户取消
  }
}

// ─── 步骤 ───
const steps = [
  { key: 'photo', label: '上传' },
  { key: 'base', label: '母版' },
  { key: 'test', label: '测试' },
  { key: 'full', label: '表情' },
  { key: 'done', label: '完成' },
]
function stepIndex(status: string): number {
  const map: Record<string, number> = {
    awaiting_photo: 0,
    generating_base: 1, reviewing_base: 1,
    generating_test: 2, reviewing_test: 2,
    generating_batch: 3, previewing: 3,
    selecting: 4, completed: 4,
  }
  return map[status] ?? 0
}
const currentStepIdx = computed(() => stepIndex(chat.sessionStatus))

// 会话列表自动刷新：每当 sessionId 变化时重新拉取
watch(() => chat.sessionId, () => {
  loadSessions()
})

onMounted(() => {
  if (isLoggedIn.value) {
    loadSessions()
    chat.connect()
  }
})

// ─── 上传照片 ───
async function handleUpload(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  input.value = ''

  uploading.value = true
  try {
    const image = await uploadImage(file)
    imageStore.setImage(image)
    chat.sendPhoto(image.imageId, image.thumbnailUrl || image.originalUrl)
  } catch (err: any) {
    ElMessage.error(err?.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

// ─── 发送文本 ───
function handleSend() {
  const text = inputText.value.trim()
  if (!text) return
  chat.sendText(text)
  inputText.value = ''
}

// ─── 操作按钮 ───
function handleAction(action: ChatAction) {
  if (action.action === 'modify_base') {
    modifyText.value = ''
    modifyVisible.value = true
    return
  }
  if (action.action === 'redraw_sticker') {
    redrawStickerId.value = action.payload?.sticker_id as string || ''
    redrawLabel.value = action.payload?.label as string || ''
    redrawText.value = ''
    redrawVisible.value = true
    return
  }
  chat.sendAction(action.action, { _label: action.label, ...(action.payload || {}) })
}

function submitModify() {
  if (!modifyText.value.trim()) return
  chat.sendAction('modify_base', { text: modifyText.value.trim(), _label: `修改意见：${modifyText.value.trim()}` })
  modifyVisible.value = false
}

function submitRedraw() {
  const payload: Record<string, unknown> = { sticker_id: redrawStickerId.value }
  if (redrawText.value.trim()) payload.text = redrawText.value.trim()
  chat.sendAction('redraw_sticker', { ...payload, _label: `重绘「${redrawLabel.value}」` })
  redrawVisible.value = false
}

// ─── 图片预览 ───
function openPreview(url: string) {
  previewUrl.value = url
  previewVisible.value = true
}

// ─── 收藏 ───
function toggleFavorite(img: ChatImage, _f: boolean) {
  if (!img.sticker_id) return
  chat.sendAction('toggle_favorite', {
    sticker_id: img.sticker_id, is_favorite: true, _label: '收藏',
  })
}
</script>

<template>
  <div class="ip-page">
    <!-- 左侧：会话列表 -->
    <aside class="sidebar">
      <div class="sidebar__header">
        <span class="sidebar__seal">坊</span>
        <span class="sidebar__title">贴纸工坊</span>
      </div>

      <button class="sidebar__new" @click="handleNewSession" :disabled="!isLoggedIn">
        <Plus style="width:16px;height:16px" />
        <span>新建对话</span>
      </button>

      <div class="sidebar__list">
        <div v-if="sessionsLoading && sessions.length === 0" class="sidebar__loading">
          加载中...
        </div>
        <div v-else-if="sessions.length === 0" class="sidebar__empty">
          <ChatDotRound style="width:32px;height:32px;opacity:0.2" />
          <p>还没有对话记录</p>
        </div>
        <div
          v-for="s in sessions" :key="s.session_id"
          class="sidebar__item"
          :class="{ 'sidebar__item--active': s.session_id === activeSessionId }"
          @click="selectSession(s)"
        >
          <div class="sidebar__item-top">
            <span class="sidebar__item-icon">{{ getSessionIcon(s) }}</span>
            <span class="sidebar__item-title">{{ getSessionTitle(s) }}</span>
            <button class="sidebar__item-delete" @click="handleDeleteSession($event, s)" title="删除对话">
              <Delete style="width:14px;height:14px" />
            </button>
          </div>
          <div class="sidebar__item-time">{{ formatTime(s.updated_at || s.created_at) }}</div>
        </div>
      </div>
    </aside>

    <!-- 右侧：聊天区 -->
    <main class="chat-area">
      <!-- 未登录提示 -->
      <div v-if="!isLoggedIn" class="chat-login">
        <div class="chat-login__icon">🎨</div>
        <h2>贴纸工坊</h2>
        <p>上传照片，AI 帮你设计专属 Q 版表情包</p>
        <RouterLink to="/login" class="chat-login__btn">登录后开始</RouterLink>
      </div>

      <!-- 已登录 -->
      <template v-else>
        <!-- 顶部工具栏 -->
        <div class="chat-toolbar">
          <!-- 步骤进度 -->
          <div class="chat-toolbar__steps" v-if="chat.connected">
            <div
              v-for="(step, i) in steps" :key="step.key"
              class="step-dot"
              :class="{
                'step-dot--active': i === currentStepIdx,
                'step-dot--done': i < currentStepIdx,
              }"
            >
              <span class="step-dot__circle">{{ i < currentStepIdx ? '✓' : i + 1 }}</span>
              <span class="step-dot__label">{{ step.label }}</span>
              <span v-if="i < steps.length - 1" class="step-dot__line"></span>
            </div>
          </div>

          <!-- 连接状态 -->
          <div v-if="!chat.connected" class="chat-toolbar__status">
            <Connection style="width:14px;height:14px" />
            <span>连接中</span>
            <button class="chat-toolbar__reconnect" @click="chat.connect()">重连</button>
          </div>
        </div>

        <!-- 聊天窗口 -->
        <div class="chat-window">
          <!-- 空状态（无消息但已连接） -->
          <div v-if="chat.messages.length === 0 && chat.connected" class="chat-empty">
            <div class="chat-empty__art">
              <span class="chat-empty__block">待</span>
              <span class="chat-empty__block chat-empty__block--accent">开</span>
              <span class="chat-empty__block">工</span>
            </div>
            <h3 class="chat-empty__title">开始创建你的专属表情包</h3>
            <p class="chat-empty__hint">点击下方图片按钮上传一张照片<br/>AI 将为你设计 Q 版 IP 形象并生成整套表情包</p>
          </div>

          <!-- 消息列表 -->
          <div v-for="msg in chat.messages" :key="msg.id"
               class="msg" :class="`msg--${msg.role}`">

            <!-- 用户消息 -->
            <div v-if="msg.role === 'user'" class="msg__bubble msg__bubble--user">
              <template v-if="msg.type === 'image_single' && msg.images?.length">
                <div class="msg__photo"
                     v-for="(img, i) in msg.images" :key="i"
                     @click="openPreview(img.url)">
                  <img v-lazy="img.thumbnail_url || img.url" :alt="img.label || '照片'" />
                </div>
              </template>
              <template v-else>
                {{ msg.content }}
              </template>
            </div>

            <!-- AI 文本 -->
            <div v-else-if="msg.type === 'text'" class="msg__bubble msg__bubble--ai">
              <span class="msg__accent-bar"></span>
              <p class="msg__text" v-html="(msg.content || '').replace(/\n/g, '<br/>')"></p>
            </div>

            <!-- AI 单图（母版） -->
            <div v-else-if="msg.type === 'image_single'" class="msg__card">
              <div class="msg__card-tape"></div>
              <div class="msg__card-img"
                   v-for="(img, i) in (msg.images || [])" :key="i">
                <img :src="img.thumbnail_url || img.url"
                     @click="openPreview(img.url)"
                     :alt="img.label || '生成图'" />
                <span v-if="img.label" class="msg__card-tag">{{ img.label }}</span>
              </div>
              <div v-if="msg.actions?.length" class="msg__card-actions">
                <button v-for="act in msg.actions" :key="act.action"
                  class="craft-btn"
                  :class="{ 'craft-btn--primary': act.type === 'primary' }"
                  @click="handleAction(act)" :disabled="chat.generating">
                  <Check v-if="act.action.includes('confirm')" class="craft-btn__ico" />
                  <EditPen v-else-if="act.action.includes('modify')" class="craft-btn__ico" />
                  <Refresh v-else-if="act.action.includes('regenerate') || act.action.includes('redraw')" class="craft-btn__ico" />
                  {{ act.label }}
                </button>
              </div>
            </div>

            <!-- AI 多图网格 -->
            <div v-else-if="msg.type === 'image_grid'" class="msg__sheet">
              <div class="msg__sheet-cut"></div>
              <div class="msg__sheet-grid"
                   :class="msg.images && msg.images.length > 8 ? 'msg__sheet--full' : 'msg__sheet--test'">
                <div v-for="(img, i) in (msg.images || [])" :key="i"
                     class="sticker-cell"
                     :class="{ 'sticker-cell--failed': img.status === 'failed' }">
                  <img v-if="img.status !== 'failed'"
                       v-lazy="img.thumbnail_url || img.url"
                       @click="openPreview(img.url)" :alt="img.label" />
                  <div v-else class="sticker-cell__fail"><span>✗</span></div>
                  <span class="sticker-cell__label">{{ img.label }}</span>
                  <div v-if="img.sticker_id && img.status !== 'failed'" class="sticker-cell__ops">
                    <button class="sticker-cell__op" @click.stop="toggleFavorite(img, false)" title="收藏">
                      <Star style="width:14px;height:14px" />
                    </button>
                    <button class="sticker-cell__op" @click.stop="() => {
                      redrawStickerId = img.sticker_id!; redrawLabel = img.label!
                      redrawText = ''; redrawVisible = true
                    }" title="重绘">
                      <Refresh style="width:14px;height:14px" />
                    </button>
                  </div>
                </div>
              </div>
              <div v-if="msg.actions?.length" class="msg__sheet-actions">
                <button v-for="act in msg.actions" :key="act.action"
                  class="craft-btn"
                  :class="{ 'craft-btn--primary': act.type === 'primary' }"
                  @click="handleAction(act)" :disabled="chat.generating">
                  {{ act.label }}
                </button>
              </div>
            </div>

            <!-- 导出列表 -->
            <div v-else-if="msg.type === 'export_list'" class="msg__bubble msg__bubble--ai">
              <span class="msg__accent-bar"></span>
              <p class="msg__text">{{ msg.content }}</p>
              <div class="msg__export-grid">
                <a v-for="(img, i) in (msg.images || [])" :key="i"
                   :href="img.url"
                   :download="img.label + '.png'"
                   class="export-cell"
                   :title="'点击保存：' + img.label">
                  <img :src="img.thumbnail_url || img.url" :alt="img.label" />
                  <span class="export-cell__label">{{ img.label }}</span>
                </a>
              </div>
            </div>

            <!-- 生成中 -->
            <div v-else-if="msg.type === 'image_generating'" class="msg__generating">
              <div class="msg__dots"><span></span><span></span><span></span></div>
              <span>{{ msg.content }}</span>
            </div>

            <!-- 错误 -->
            <div v-else-if="msg.type === 'error'" class="msg__error">
              <span class="msg__error-icon">!</span>
              {{ msg.content }}
            </div>

            <!-- 独立操作按钮 -->
            <div v-else-if="msg.type === 'actions' && msg.actions?.length" class="msg__actions">
              <button v-for="act in msg.actions" :key="act.action"
                class="craft-btn"
                :class="{ 'craft-btn--primary': act.type === 'primary' }"
                @click="handleAction(act)" :disabled="chat.generating">
                {{ act.label }}
              </button>
            </div>
          </div>
        </div>

        <!-- 输入区 -->
        <div class="chat-input">
          <div class="chat-input__row">
            <label class="chat-input__upload" :class="{ disabled: chat.generating }">
              <input type="file" accept="image/*" @change="handleUpload"
                     :disabled="chat.generating" hidden />
              <PictureIcon />
              <span>上传</span>
            </label>
            <div class="chat-input__field">
              <input
                v-model="inputText"
                :placeholder="chat.generating ? '生成中，请稍后...' : '输入消息或修改意见...'"
                :disabled="chat.generating"
                @keyup.enter="handleSend"
                class="chat-input__native"
              />
            </div>
            <button class="chat-input__send"
                    :disabled="!inputText.trim() || chat.generating"
                    @click="handleSend">
              <ArrowUp />
            </button>
          </div>
        </div>
      </template>
    </main>

    <!-- 修改意见弹窗 -->
    <el-dialog v-model="modifyVisible" title="修改 IP 母版" width="420px">
      <p class="dlg__hint">请描述你想修改的内容：</p>
      <el-input v-model="modifyText" type="textarea" :rows="3"
                placeholder="例如：发型换成短发 / 不要眼镜 / 脸型瘦一点" />
      <template #footer>
        <el-button @click="modifyVisible = false">取消</el-button>
        <el-button type="primary" @click="submitModify" :disabled="!modifyText.trim()">确认修改</el-button>
      </template>
    </el-dialog>

    <!-- 重绘弹窗 -->
    <el-dialog v-model="redrawVisible" :title="`重绘「${redrawLabel}」`" width="420px">
      <p class="dlg__hint">可选：描述你想调整的内容</p>
      <el-input v-model="redrawText" type="textarea" :rows="2"
                placeholder="例如：表情更夸张一点 / 加上爱心" />
      <template #footer>
        <el-button @click="redrawVisible = false">取消</el-button>
        <el-button type="primary" @click="submitRedraw">确认重绘</el-button>
      </template>
    </el-dialog>

    <!-- 图片预览 -->
    <el-image-viewer v-if="previewVisible" :url-list="[previewUrl]" @close="previewVisible = false" />
  </div>
</template>

<style scoped>
/* ================================================================
   贴纸工坊 — 豆包式左右布局
   左侧：会话列表 | 右侧：聊天区
   ================================================================ */

.ip-page {
  display: flex;
  height: calc(100vh - 64px);
  max-width: 1200px;
  margin: 0 auto;
  padding: 0;
}

/* ─── 左侧边栏 ─── */
.sidebar {
  width: 260px;
  min-width: 260px;
  background: var(--color-bg-card);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.sidebar__header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 16px 12px;
  border-bottom: 1px solid var(--color-border);
}
.sidebar__seal {
  width: 30px; height: 30px;
  background: var(--color-primary);
  color: #fff;
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 3px;
  box-shadow: var(--shadow-seal);
}
.sidebar__title {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.03em;
}
.sidebar__new {
  margin: 12px 12px 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 9px 0;
  border: 1.5px dashed var(--color-primary);
  border-radius: 8px;
  background: transparent;
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 0.03em;
}
.sidebar__new:hover {
  background: rgba(200, 68, 43, 0.06);
}
.sidebar__new:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.sidebar__list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px 8px;
}
.sidebar__loading,
.sidebar__empty {
  text-align: center;
  padding: 40px 12px;
  color: var(--color-text-secondary);
  font-size: 13px;
}
.sidebar__empty p { margin: 8px 0 0; }

.sidebar__item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  margin-bottom: 2px;
}
.sidebar__item:hover {
  background: rgba(200, 68, 43, 0.05);
}
.sidebar__item--active {
  background: rgba(200, 68, 43, 0.08);
  border-left: 3px solid var(--color-primary);
  padding-left: 9px;
}
.sidebar__item-top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.sidebar__item-icon {
  font-size: 14px;
  flex-shrink: 0;
}
.sidebar__item-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}
.sidebar__item-delete {
  display: none;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--color-text-placeholder);
  border-radius: 4px;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.2s;
}
.sidebar__item-delete:hover {
  background: rgba(245, 108, 108, 0.1);
  color: #f56c6c;
}
.sidebar__item:hover .sidebar__item-delete {
  display: flex;
}
.sidebar__item-time {
  font-size: 11px;
  color: var(--color-text-placeholder);
  margin-top: 3px;
  padding-left: 22px;
}

/* ─── 右侧聊天区 ─── */
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--color-bg);
}

/* 登录提示 */
.chat-login {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px;
}
.chat-login__icon { font-size: 48px; margin-bottom: 16px; }
.chat-login h2 {
  font-family: var(--font-display);
  font-size: 22px;
  margin: 0 0 8px;
}
.chat-login p {
  color: var(--color-text-secondary);
  font-size: 14px;
  margin: 0 0 24px;
}
.chat-login__btn {
  padding: 10px 28px;
  background: var(--color-primary);
  color: #fff;
  border-radius: 8px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.2s;
}
.chat-login__btn:hover { background: var(--color-primary-dark); }

/* 顶部工具栏 */
.chat-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
  background: rgba(245, 242, 236, 0.6);
}
.chat-toolbar__steps {
  display: flex;
  align-items: center;
  gap: 0;
}
.step-dot {
  display: flex;
  align-items: center;
  gap: 4px;
}
.step-dot__circle {
  width: 20px; height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 600;
  border: 1.5px solid #d4cfc6;
  color: #b5afa3;
  background: #fff;
  flex-shrink: 0;
  transition: all 0.3s;
}
.step-dot--done .step-dot__circle {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}
.step-dot--active .step-dot__circle {
  border-color: var(--color-primary);
  color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(200, 68, 43, 0.12);
}
.step-dot__label {
  font-size: 11px;
  color: #b5afa3;
  letter-spacing: 0.02em;
}
.step-dot--done .step-dot__label,
.step-dot--active .step-dot__label {
  color: var(--color-text);
  font-weight: 500;
}
.step-dot__line {
  width: 16px; height: 1.5px;
  background: #d4cfc6;
  margin: 0 3px;
  flex-shrink: 0;
}
.step-dot--done .step-dot__line { background: var(--color-primary); }

.chat-toolbar__status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #a08060;
}
.chat-toolbar__reconnect {
  padding: 2px 8px;
  border: 1px solid #c8a87a;
  border-radius: 4px;
  background: transparent;
  color: #a08060;
  font-size: 11px;
  cursor: pointer;
}
.chat-toolbar__reconnect:hover { background: #a08060; color: #fff; }

/* ─── 聊天窗口 ─── */
.chat-window {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  background-image:
    repeating-linear-gradient(
      0deg, transparent, transparent 31px,
      rgba(200, 68, 43, 0.03) 31px, rgba(200, 68, 43, 0.03) 32px
    );
}

/* 空状态 */
.chat-empty {
  text-align: center;
  padding: 80px 20px 40px;
}
.chat-empty__art {
  display: inline-flex;
  gap: 8px;
  margin-bottom: 24px;
}
.chat-empty__block {
  width: 44px; height: 44px;
  border: 2px solid #d4cfc6;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 700;
  color: #d4cfc6;
}
.chat-empty__block--accent {
  border-color: var(--color-primary);
  color: var(--color-primary);
  transform: rotate(-3deg);
  box-shadow: var(--shadow-seal);
}
.chat-empty__title {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 8px;
}
.chat-empty__hint {
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.8;
  margin: 0;
}

/* ─── 消息 ─── */
.msg { margin-bottom: 16px; animation: msg-in 0.25s ease-out; }
@keyframes msg-in {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
.msg--user { display: flex; justify-content: flex-end; }
.msg--assistant, .msg--system { display: flex; justify-content: flex-start; }

/* 气泡 */
.msg__bubble {
  max-width: 70%;
  padding: 10px 16px;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}
.msg__bubble--user {
  background: var(--color-primary);
  color: #fff;
  border-radius: 16px 16px 4px 16px;
  box-shadow: 0 2px 8px rgba(200, 68, 43, 0.18);
}
.msg__bubble--ai {
  background: var(--color-bg-card);
  color: var(--color-text);
  border-radius: 4px 16px 16px 16px;
  border: 1px solid var(--color-border);
  position: relative;
  padding-left: 20px;
}
.msg__accent-bar {
  position: absolute;
  left: 0; top: 6px; bottom: 6px;
  width: 3px;
  border-radius: 2px;
  background: linear-gradient(to bottom, var(--color-primary), rgba(200,68,43,0.12));
}
.msg__text { margin: 0; }

/* 用户上传的照片 */
.msg__photo {
  width: 180px;
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid rgba(255,255,255,0.3);
}
.msg__photo img {
  width: 100%;
  display: block;
  max-height: 240px;
  object-fit: cover;
}

/* 图片卡片 */
.msg__card {
  max-width: 75%;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  overflow: hidden;
  position: relative;
}
.msg__card-tape {
  position: absolute;
  top: -1px; left: 20px;
  width: 56px; height: 12px;
  background: rgba(200, 68, 43, 0.1);
  border-radius: 0 0 4px 4px;
  z-index: 1;
}
.msg__card-img {
  position: relative;
  cursor: pointer;
  padding: 18px 14px 10px;
}
.msg__card-img img {
  width: 100%;
  display: block;
  max-height: 360px;
  object-fit: contain;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  background: #faf8f3;
}
.msg__card-tag {
  position: absolute;
  bottom: 18px; left: 22px;
  background: var(--color-primary);
  color: #fff;
  font-size: 10px;
  padding: 2px 10px;
  border-radius: 3px;
  font-weight: 500;
  letter-spacing: 0.04em;
}
.msg__card-actions {
  display: flex;
  gap: 8px;
  padding: 0 14px 12px;
}

/* 贴纸网格 */
.msg__sheet {
  max-width: 95%;
  background: #e6ddd0;
  border-radius: 10px;
  padding: 12px;
  border: 1px solid rgba(156, 150, 139, 0.25);
  position: relative;
}
.msg__sheet-cut {
  position: absolute;
  top: 6px; left: 12px; right: 12px;
  border-top: 1px dashed rgba(156, 150, 139, 0.35);
}
.msg__sheet-grid {
  display: grid;
  gap: 6px;
  margin-top: 4px;
}
.msg__sheet--test { grid-template-columns: repeat(2, 1fr); max-width: 340px; }
.msg__sheet--full { grid-template-columns: repeat(4, 1fr); }
.msg__sheet-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed rgba(156, 150, 139, 0.25);
}

.sticker-cell {
  position: relative;
  aspect-ratio: 1;
  border-radius: 6px;
  overflow: hidden;
  background: #fff;
  border: 1px solid #ddd;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}
.sticker-cell:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
.sticker-cell img { width: 100%; height: 100%; object-fit: cover; }
.sticker-cell--failed {
  display: flex; align-items: center; justify-content: center;
  background: #fef0f0;
}
.sticker-cell__fail { color: #f56c6c; font-size: 18px; }
.sticker-cell__label {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  background: linear-gradient(transparent, rgba(0,0,0,0.55));
  color: #fff;
  font-size: 10px;
  padding: 10px 4px 3px;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sticker-cell__ops {
  position: absolute;
  top: 4px; right: 4px;
  display: flex; gap: 3px;
  opacity: 0;
  transition: opacity 0.2s;
}
.sticker-cell:hover .sticker-cell__ops { opacity: 1; }
.sticker-cell__op {
  width: 24px; height: 24px;
  border-radius: 50%;
  background: rgba(255,255,255,0.92);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #888;
  padding: 0;
}
.sticker-cell__op:hover { color: var(--color-primary); }

/* 生成中 */
.msg__generating {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  background: var(--color-bg-card);
  border-radius: 10px;
  border: 1px dashed var(--color-border);
  font-size: 13px;
  color: var(--color-text-secondary);
  max-width: 70%;
}
.msg__dots { display: flex; gap: 4px; }
.msg__dots span {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--color-primary);
  opacity: 0.25;
  animation: dot-p 1.2s ease-in-out infinite;
}
.msg__dots span:nth-child(2) { animation-delay: 0.2s; }
.msg__dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes dot-p {
  0%, 100% { opacity: 0.2; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.1); }
}

/* 错误 */
.msg__error {
  background: #fdf5f5;
  border: 1px solid #f5d5d5;
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 13px;
  color: #c44;
  max-width: 70%;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.msg__error-icon {
  width: 18px; height: 18px;
  border-radius: 50%;
  background: #c44;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.msg__actions { display: flex; gap: 8px; flex-wrap: wrap; }

/* ─── 工坊按钮 ─── */
.craft-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 16px;
  border-radius: 6px;
  border: 1.5px solid var(--color-border);
  background: #fff;
  color: var(--color-text);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.craft-btn:hover { border-color: var(--color-primary); color: var(--color-primary); }
.craft-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.craft-btn--primary {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}
.craft-btn--primary:hover {
  background: var(--color-primary-dark);
  border-color: var(--color-primary-dark);
  color: #fff;
}
.craft-btn__ico { width: 14px; height: 14px; }

/* ─── 输入区 ─── */
.chat-input {
  padding: 12px 24px 16px;
  flex-shrink: 0;
  border-top: 1px solid var(--color-border);
  background: var(--color-bg);
}
.chat-input__row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}
.chat-input__upload {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 6px 10px;
  border-radius: 8px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  cursor: pointer;
  color: var(--color-text-secondary);
  font-size: 10px;
  flex-shrink: 0;
  transition: all 0.2s;
}
.chat-input__upload:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.chat-input__upload.disabled { opacity: 0.3; cursor: not-allowed; }
.chat-input__field { flex: 1; }
.chat-input__native {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-card);
  font-size: 14px;
  color: var(--color-text);
  font-family: var(--font-body);
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}
.chat-input__native::placeholder { color: var(--color-text-placeholder); }
.chat-input__native:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(200, 68, 43, 0.06);
}
.chat-input__native:disabled { opacity: 0.5; }
.chat-input__send {
  width: 38px; height: 38px;
  border-radius: 50%;
  background: var(--color-primary);
  border: none;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.2s;
  box-shadow: 0 2px 6px rgba(200, 68, 43, 0.2);
}
.chat-input__send:hover { background: var(--color-primary-dark); transform: scale(1.05); }
.chat-input__send:disabled { background: #d4cfc6; box-shadow: none; cursor: not-allowed; transform: none; }

.dlg__hint { font-size: 13px; color: var(--color-text-secondary); margin: 0 0 12px; }

/* ─── 移动端响应式 ─── */
@media (max-width: 768px) {
  .ip-page { flex-direction: column; height: auto; min-height: calc(100vh - 64px); }
  .sidebar {
    width: 100%;
    min-width: unset;
    max-height: 180px;
    border-right: none;
    border-bottom: 1px solid var(--color-border);
  }
  .sidebar__list { max-height: 100px; }
  .chat-window { padding: 16px 12px; min-height: 400px; max-height: calc(100vh - 360px); }
  .chat-input { padding: 10px 12px 14px; }
  .msg__bubble { max-width: 85%; }
  .msg__card { max-width: 90%; }
  .msg__sheet { max-width: 100%; }
}

/* ─── 导出列表 ─── */
.msg__export-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-top: 12px;
}
.export-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 6px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 8px;
  text-decoration: none;
  color: inherit;
  transition: all 0.2s;
  cursor: pointer;
}
.export-cell:hover {
  background: rgba(200, 68, 43, 0.08);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
.export-cell img {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid var(--color-border);
}
.export-cell__label {
  font-size: 11px;
  color: var(--color-text-secondary);
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}
@media (max-width: 768px) {
  .msg__export-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
