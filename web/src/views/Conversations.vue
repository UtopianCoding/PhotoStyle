<script setup lang="ts">
// 模型交互记录页：记录每次与 AI 模型交互的输入（原图 + 提示词）与输出（结果图）
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Clock, Picture, Warning } from '@element-plus/icons-vue'
import {
  getConversationDetail,
  listConversations,
} from '@/api/conversation'
import { listSkills } from '@/api/skill'
import type { ConversationDetail, ConversationItem, Skill } from '@/types'

// -------------------- 状态 --------------------
const loading = ref(false)
const items = ref<ConversationItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)

// 筛选
const skillId = ref<string | null>(null)
const status = ref<string | null>(null)
const skillOptions = ref<Skill[]>([])

// 详情弹窗
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref<ConversationDetail | null>(null)

// 技能ID → 名称 映射，用于展示
const skillNameMap = computed(() => {
  const map: Record<string, string> = {}
  skillOptions.value.forEach((s) => { map[s.id] = s.name })
  return map
})
function skillName(id: string): string {
  return skillNameMap.value[id] || id
}

// 状态标签
function statusType(s: string): 'success' | 'danger' | 'info' {
  if (s === 'success') return 'success'
  if (s === 'failed') return 'danger'
  return 'info'
}

// 提示词截断预览
function promptPreview(p: string, n = 80): string {
  if (!p) return '（无）'
  return p.length > n ? p.slice(0, n) + '…' : p
}

// 耗时格式化
function fmtDuration(ms?: number | null): string {
  if (ms == null) return '—'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

// 时间格式化
function fmtTime(t: string): string {
  return (t || '').replace('T', ' ').slice(0, 19)
}

// 请求体快照格式化展示
function formatProviderRequest(raw?: string | null): string {
  if (!raw) return '（无）'
  try {
    const obj = JSON.parse(raw)
    return JSON.stringify(obj, null, 2)
  } catch {
    return raw
  }
}

// Provider 显示名称映射
const PROVIDER_LABELS: Record<string, string> = {
  qianwen: '千问',
  dalle: 'GPT Image 2',
  minimax: 'MiniMax',
  volcengine: '火山引擎',
  doubao: '豆包',
}
function providerLabel(pid: string): string {
  return PROVIDER_LABELS[pid] ?? pid
}

// -------------------- 数据加载 --------------------
async function load() {
  loading.value = true
  try {
    const res = await listConversations({
      page: page.value,
      pageSize: pageSize.value,
      skillId: skillId.value,
      status: status.value,
    })
    items.value = res.items
    total.value = res.total
  } catch {
    ElMessage.error('加载交互记录失败')
  } finally {
    loading.value = false
  }
}

async function loadSkills() {
  try {
    skillOptions.value = await listSkills()
  } catch {
    /* 技能列表加载失败不影响主功能 */
  }
}

// 打开详情
async function openDetail(item: ConversationItem) {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await getConversationDetail(item.interactionId)
  } catch {
    ElMessage.error('加载详情失败')
  } finally {
    detailLoading.value = false
  }
}

function onFilterChange() {
  page.value = 1
  load()
}

function onPageChange(p: number) {
  page.value = p
  load()
}

onMounted(() => {
  loadSkills()
  load()
})

watch([skillId, status], onFilterChange)
</script>

<template>
  <div class="mx-auto max-w-5xl px-4 py-8">
    <!-- 标题区（与首页/后台一致的水墨呼吸） -->
    <section class="hero ink-fade">
      <div class="hero__seal-wrap">
        <span class="hero__seal">迹</span>
      </div>
      <h1 class="hero__title font-display">交互记录</h1>
      <p class="hero__subtitle">每一次创作的来路、提示词与成果</p>
    </section>

    <!-- 工具条：筛选 -->
    <div class="conv-toolbar">
      <span class="conv-toolbar__label font-display">创作手账</span>
      <div class="conv-topbar__filters">
        <el-select
          v-model="skillId"
          placeholder="全部技能"
          clearable
          class="conv-filter"
        >
          <el-option label="全部技能" value="" />
          <el-option
            v-for="s in skillOptions"
            :key="s.id"
            :label="s.name"
            :value="s.id"
          />
        </el-select>
        <el-select
          v-model="status"
          placeholder="全部状态"
          clearable
          class="conv-filter"
        >
          <el-option label="全部状态" value="" />
          <el-option label="成功" value="success" />
          <el-option label="失败" value="failed" />
        </el-select>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="!loading && items.length === 0" class="conv-empty">
      <span class="conv-empty__seal">空</span>
      <p class="font-display">暂无交互记录</p>
    </div>

    <!-- 列表 -->
    <div v-else class="conv-list ink-fade">
      <div
        v-for="item in items"
        :key="item.interactionId"
        class="conv-card"
        @click="openDetail(item)"
      >
        <!-- 输入原图 -->
        <div class="conv-card__input">
          <img :src="item.inputImageUrl" :alt="skillName(item.skillId)" />
        </div>
        <!-- 原图 → 成果 的转化意象 -->
        <span class="conv-card__arrow" aria-hidden="true">→</span>

        <!-- 中间信息 -->
        <div class="conv-card__body">
          <div class="conv-card__meta">
            <el-tag size="small" effect="plain">{{ skillName(item.skillId) }}</el-tag>
            <el-tag size="small" :type="statusType(item.status)" effect="light">
              {{ item.status === 'success' ? '成功' : '失败' }}
            </el-tag>
            <span class="conv-card__time">
              <el-icon><Clock /></el-icon>{{ fmtTime(item.createdAt) }}
            </span>
            <span class="conv-card__dur">
              <el-icon><Picture /></el-icon>{{ fmtDuration(item.durationMs) }}
            </span>
          </div>
          <div class="conv-card__prompt">{{ promptPreview(item.promptSent) }}</div>
        </div>

        <!-- 输出缩略图 -->
        <div class="conv-card__outputs">
          <template v-if="item.outputImageUrls.length">
            <div
              v-for="(u, i) in item.outputImageUrls.slice(0, 2)"
              :key="i"
              class="conv-card__output-cell"
            >
              <img :src="u" alt="输出结果" />
              <span v-if="item.provider" class="conv-card__provider-tag">
                {{ providerLabel(item.provider) }}
              </span>
            </div>
            <span v-if="item.outputImageUrls.length > 2" class="conv-card__more">
              +{{ item.outputImageUrls.length - 2 }}
            </span>
          </template>
          <span v-else class="conv-card__noout">
            <el-icon><Warning /></el-icon> 无输出
          </span>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <el-pagination
      v-if="total > pageSize"
      class="conv-pager"
      layout="prev, pager, next"
      :total="total"
      :page-size="pageSize"
      :current-page="page"
      @current-change="onPageChange"
    />

    <!-- 详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      title="交互详情"
      width="720px"
      class="conv-dialog"
      append-to-body
    >
      <div v-if="detailLoading" class="conv-detail__loading">加载中…</div>
      <div v-else-if="detail" class="conv-detail">
        <!-- 元信息 -->
        <div class="conv-detail__meta">
          <el-tag size="small" effect="plain">{{ skillName(detail.skillId) }}</el-tag>
          <el-tag size="small" :type="statusType(detail.status)" effect="light">
            {{ detail.status === 'success' ? '成功' : '失败' }}
          </el-tag>
          <span class="conv-detail__kv">提供商：{{ detail.provider }}</span>
          <span class="conv-detail__kv">耗时：{{ fmtDuration(detail.durationMs) }}</span>
          <span class="conv-detail__kv">{{ fmtTime(detail.createdAt) }}</span>
        </div>

        <!-- 输入 / 输出 对照 -->
        <div class="conv-detail__io">
          <div class="conv-detail__col">
            <div class="conv-detail__label">输入原图</div>
            <el-image
              :src="detail.inputImageUrl"
              fit="cover"
              class="conv-detail__img"
              :preview-src-list="[detail.inputImageUrl]"
            />
          </div>
          <div class="conv-detail__col">
            <div class="conv-detail__label">
              输出结果（{{ detail.outputImageUrls.length }}）
            </div>
            <div v-if="detail.outputImageUrls.length" class="conv-detail__outputs">
              <div
                v-for="(u, i) in detail.outputImageUrls"
                :key="i"
                class="conv-detail__output-cell"
              >
                <el-image
                  :src="u"
                  fit="cover"
                  class="conv-detail__img"
                  :preview-src-list="detail.outputImageUrls"
                  :initial-index="i"
                />
                <span class="conv-detail__provider-tag">{{ providerLabel(detail.provider) }}</span>
              </div>
            </div>
            <div v-else class="conv-detail__noout">
              <el-icon><Warning /></el-icon> 本次交互无输出（生成失败）
            </div>
          </div>
        </div>

        <!-- 提示词 -->
        <div class="conv-detail__section">
          <div class="conv-detail__label">发送给模型的提示词</div>
          <pre class="conv-detail__prompt">{{ detail.promptSent }}</pre>
        </div>

        <!-- 额外信息 -->
        <div v-if="detail.extraPrompt || detail.feedback || detail.location" class="conv-detail__section">
          <div class="conv-detail__label">附加信息</div>
          <div class="conv-detail__kvblock">
            <div v-if="detail.extraPrompt"><b>额外要求：</b>{{ detail.extraPrompt }}</div>
            <div v-if="detail.feedback"><b>重新生成意见：</b>{{ detail.feedback }}</div>
            <div v-if="detail.location"><b>拍摄地点：</b>{{ detail.location }}</div>
          </div>
        </div>

        <!-- 错误信息 -->
        <div v-if="detail.status === 'failed' && detail.errorMessage" class="conv-detail__section">
          <div class="conv-detail__label conv-detail__label--err">错误信息</div>
          <pre class="conv-detail__error">{{ detail.errorMessage }}</pre>
        </div>

        <!-- 服务商原始响应 -->
        <div v-if="detail.providerResponse" class="conv-detail__section">
          <div class="conv-detail__label">服务商原始响应</div>
          <pre class="conv-detail__resp">{{ detail.providerResponse }}</pre>
        </div>

        <!-- 实际请求体快照 -->
        <div v-if="detail.providerRequest" class="conv-detail__section">
          <div class="conv-detail__label">实际请求体快照</div>
          <pre class="conv-detail__resp">{{ formatProviderRequest(detail.providerRequest) }}</pre>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
/* ============ 标题区（与首页/后台一致） ============ */
.hero {
  text-align: center;
  margin-bottom: 24px;
}
.hero__seal-wrap {
  display: flex;
  justify-content: center;
  margin-bottom: 14px;
}
.hero__seal {
  width: 48px;
  height: 48px;
  border-radius: 4px;
  background: var(--color-primary);
  color: #fff;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 28px;
  line-height: 48px;
  text-align: center;
  box-shadow: var(--shadow-seal);
  position: relative;
}
.hero__seal::after {
  content: "";
  position: absolute;
  right: 3px;
  bottom: 3px;
  width: 7px;
  height: 7px;
  background: rgba(255, 255, 255, 0.18);
  border-radius: 50%;
}
.hero__title {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.1em;
  margin-bottom: 6px;
}
.hero__subtitle {
  font-size: 13px;
  color: var(--color-text-secondary);
  letter-spacing: 0.04em;
}

/* ============ 工具条 ============ */
.conv-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 20px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--color-border);
}
.conv-toolbar__label {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.08em;
}
.conv-topbar__filters {
  display: flex;
  gap: 10px;
}
.conv-filter {
  width: 140px;
}

/* ============ 空状态 ============ */
.conv-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding: 72px 0;
  color: var(--color-text-secondary);
}
.conv-empty__seal {
  width: 56px;
  height: 56px;
  border: 1px solid rgba(200, 68, 43, 0.4);
  border-radius: 6px;
  background: rgba(200, 68, 43, 0.04);
  color: var(--color-primary);
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 26px;
  line-height: 56px;
  text-align: center;
}
.conv-empty p {
  font-size: 15px;
  letter-spacing: 0.12em;
}

/* ============ 列表 ============ */
.conv-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.conv-card {
  position: relative;
  display: flex;
  gap: 16px;
  align-items: center;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 14px 18px 14px 22px;
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
/* 朱砂封条：每条记录如一份缄封的纸笺 */
.conv-card::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--color-primary);
  opacity: 0.85;
  transition: width 0.2s ease, opacity 0.2s ease;
}
.conv-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: rgba(200, 68, 43, 0.35);
}
.conv-card:hover::before {
  width: 5px;
  opacity: 1;
}
.conv-card__input {
  width: 64px;
  height: 64px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
}
.conv-card__input img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
/* 原图 → 成果 的转化意象 */
.conv-card__arrow {
  flex-shrink: 0;
  color: var(--color-primary);
  font-family: var(--font-display);
  font-size: 18px;
  opacity: 0.65;
}
.conv-card__body {
  flex: 1;
  min-width: 0;
}
.conv-card__meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--color-text-secondary);
}
.conv-card__time,
.conv-card__dur {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}
.conv-card__prompt {
  font-size: 13px;
  color: var(--color-text);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.conv-card__outputs {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.conv-card__output-cell {
  position: relative;
}
.conv-card__output-cell img {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-sm);
  object-fit: cover;
  display: block;
  border: 1px solid var(--color-border);
}
.conv-card__provider-tag {
  position: absolute;
  bottom: 2px;
  left: 2px;
  font-size: 8px;
  font-family: var(--font-display);
  letter-spacing: 0.03em;
  line-height: 1;
  padding: 1px 4px;
  border-radius: 2px;
  background: rgba(28, 28, 26, 0.6);
  color: #f5f2ec;
  backdrop-filter: blur(3px);
  white-space: nowrap;
  pointer-events: none;
}
.conv-card__more {
  font-size: 12px;
  color: var(--color-text-secondary);
}
.conv-card__noout {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--color-primary-dark);
}

.conv-pager {
  margin-top: 24px;
  justify-content: center;
}

/* ============ 详情弹窗 ============ */
.conv-detail__loading {
  text-align: center;
  color: var(--color-text-secondary);
  padding: 40px 0;
}
.conv-detail__meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}
.conv-detail__kv {
  font-size: 12px;
  color: var(--color-text-secondary);
}
.conv-detail__io {
  display: flex;
  gap: 18px;
  margin-bottom: 18px;
}
.conv-detail__col {
  flex: 1;
  min-width: 0;
}
/* 章节标签：朱砂小印 */
.conv-detail__label {
  position: relative;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 8px;
  letter-spacing: 0.04em;
  padding-left: 12px;
}
.conv-detail__label::before {
  content: "";
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 5px;
  height: 5px;
  background: var(--color-primary);
  border-radius: 1px;
}
.conv-detail__label--err {
  color: var(--color-primary-dark);
}
.conv-detail__label--err::before {
  background: var(--color-primary-dark);
}
.conv-detail__img {
  width: 100%;
  height: 220px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  overflow: hidden;
}
.conv-detail__outputs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.conv-detail__output-cell {
  position: relative;
  width: calc(50% - 4px);
}
.conv-detail__output-cell .conv-detail__img {
  width: 100%;
  height: 200px;
}
.conv-detail__provider-tag {
  position: absolute;
  bottom: 8px;
  left: 8px;
  font-size: 11px;
  font-family: var(--font-display);
  letter-spacing: 0.05em;
  line-height: 1;
  padding: 3px 7px;
  border-radius: 2px;
  background: rgba(28, 28, 26, 0.6);
  color: #f5f2ec;
  backdrop-filter: blur(4px);
  white-space: nowrap;
  pointer-events: none;
}
.conv-detail__noout {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--color-primary-dark);
  font-size: 13px;
  padding: 20px 0;
}
.conv-detail__section {
  margin-bottom: 16px;
}
.conv-detail__kvblock {
  font-size: 13px;
  color: var(--color-text);
  line-height: 1.8;
}
/* 技术文本区块 */
.conv-detail__prompt,
.conv-detail__error,
.conv-detail__resp {
  margin: 0;
  padding: 12px 14px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--color-text);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 220px;
  overflow: auto;
  font-family: var(--font-mono, monospace);
}
/* 提示词：红线信笺，呼应“写给模型的信” */
.conv-detail__prompt {
  border-left: 3px solid var(--color-primary);
}
.conv-detail__error {
  border-color: var(--color-primary);
  color: var(--color-primary-dark);
}
.conv-detail__resp {
  color: var(--color-text-secondary);
}

@media (max-width: 640px) {
  .conv-toolbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  .conv-card {
    flex-wrap: wrap;
  }
  .conv-card__arrow {
    display: none;
  }
  .conv-detail__io {
    flex-direction: column;
  }
}
</style>
