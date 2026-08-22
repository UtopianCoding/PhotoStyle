<script setup lang="ts">
// 首页：上传照片 → 查看示例 → 选择风格 → 分析图片 → 选择诗意小字 → 一键生成
import { onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import ImageUploader from '@/components/uploader/ImageUploader.vue'
import StyleGallery from '@/components/style/StyleGallery.vue'
import { listSkills } from '@/api/skill'
import { useImageStore } from '@/stores/image'
import { useStyleStore } from '@/stores/style'
import { useConvert } from '@/composables/useConvert'
import type { Skill } from '@/types'

const router = useRouter()
const imageStore = useImageStore()
const styleStore = useStyleStore()
const { converting, analyze, convert } = useConvert()

// 当前选中的技能对象（用于展示描述）
const selectedSkill = computed<Skill | undefined>(() =>
  styleStore.skills.find((s) => s.id === styleStore.selectedSkillId),
)

// 是否选中冰箱贴技能（需要填写拍摄地点）
const isFridgeMagnet = computed(() => styleStore.selectedSkillId === 'fridge-magnet')

// 是否选中马克笔童画技能（需要填写签名）
const isMarkerDoodle = computed(() => styleStore.selectedSkillId === 'marker-child-doodle')

// 是否需要分析图片（根据数据库配置，needAnalysis=false 的技能无需分析）
const needsAnalysis = computed(() => selectedSkill.value?.needAnalysis ?? false)

// 是否允许点击「分析图片」：需要该技能配置了 needAnalysis 且已上传图片
const canAnalyze = computed(() => needsAnalysis.value && !!imageStore.imageId)

// 是否允许点击「开始转换」：必须已上传图片；冰箱贴需额外填地点
const canConvert = computed(() => {
  if (!imageStore.imageId) return false
  if (styleStore.selectedSkillId === 'fridge-magnet') {
    return styleStore.fridgeLocation.trim().length > 0
  }
  // 其余风格：不强制要求先分析，后端会自动后台分析
  return true
})

/** 加载技能列表 */
async function loadSkills() {
  try {
    const skills = await listSkills()
    styleStore.setSkills(skills)
  } catch {
    ElMessage.error('加载风格列表失败')
  }
}

/** 选择技能 */
function onSelectSkill(skill: Skill) {
  styleStore.setSkillId(skill.id)
}

/** 分析图片 */
async function onAnalyze() {
  await analyze()
}

/** 提交转换 */
async function onConvert() {
  const task = await convert()
  if (task) {
    ElMessage.success('任务已提交，正在转换...')
    router.push(`/result/${task.taskId}`)
  }
}

onMounted(loadSkills)

// 切换风格后，清空旧分析结果（新风格的分析需要用户手动点击按钮）
watch(
  () => styleStore.selectedSkillId,
  () => {
    styleStore.setAnalysisResult(null)
  },
)
</script>

<template>
  <div class="home-flow mx-auto max-w-6xl px-4 py-12">
    <!-- 诗意标题 -->
    <section class="hero ink-fade">
      <div class="hero__seal-wrap">
        <span class="hero__seal">影</span>
      </div>
      <h1 class="hero__title font-display">把照片画成一页诗</h1>
      <p class="hero__subtitle">上传照片，AI 分析生成提示词，选择风格一键生成</p>
      <div class="hero__rule" aria-hidden="true"></div>
    </section>

    <!-- 上传区 -->
    <section class="notebook-section ink-fade ink-fade--delay-1">
      <h2 class="notebook-section__label font-display">
        <span class="ink-stamp">壹</span>
        <span>上传照片</span>
      </h2>
      <ImageUploader />
    </section>

    <!-- 选择风格（卡片内嵌示例效果，点击选中） -->
    <section class="notebook-section ink-fade ink-fade--delay-2">
      <h2 class="notebook-section__label font-display">
        <span class="ink-stamp">贰</span>
        <span>选择风格</span>
      </h2>
      <StyleGallery
        :skills="styleStore.skills"
        :selected-id="styleStore.selectedSkillId"
        @select="onSelectSkill"
      />
      <p v-if="selectedSkill" class="skill-desc">{{ selectedSkill.description }}</p>
      <p v-else class="skill-desc skill-desc--hint">
        卡片内为各风格的示例效果，点击选中后再进行分析
      </p>

      <!-- 冰箱贴：拍摄地点输入（自动翻译为英文城市名） -->
      <div v-if="isFridgeMagnet" class="fridge-location">
        <label class="fridge-location__label font-display">拍摄地点</label>
        <input
          v-model="styleStore.fridgeLocation"
          class="fridge-location__input"
          type="text"
          placeholder="如 昆明/中国"
          maxlength="40"
        />
        <p class="fridge-location__hint">将自动翻译为英文城市名，印在海报底部</p>
      </div>

      <!-- 马克笔童画：签名输入 -->
      <div v-if="isMarkerDoodle" class="fridge-location">
        <label class="fridge-location__label font-display">签名</label>
        <input
          v-model="styleStore.markerSignature"
          class="fridge-location__input"
          type="text"
          placeholder="默认 Utopian"
          maxlength="20"
        />
        <p class="fridge-location__hint">英文签名，将潦草手写在右下角（留空则默认 Utopian）</p>
      </div>
    </section>

    <!-- 分析按钮（根据技能的 needAnalysis 配置决定是否显示） -->
    <div v-if="needsAnalysis" class="convert-action">
      <button
        class="analyze-btn font-display"
        :disabled="styleStore.analyzing || !canAnalyze"
        @click="onAnalyze"
      >
        <span v-if="!styleStore.analyzing">分析图片</span>
        <span v-else class="convert-btn__loading">AI 分析中…</span>
      </button>
    </div>

    <!-- 分析结果展示（needAnalysis=false 的技能无分析结果，隐藏） -->
    <section v-if="styleStore.analysisResult && needsAnalysis" class="notebook-section analysis-result ink-fade">
      <h2 class="notebook-section__label font-display">
        <span class="ink-stamp">叁</span>
        <span>分析结果</span>
      </h2>

      <!-- 主体识别 -->
      <div class="analysis-block">
        <h3 class="analysis-block__title">照片主体识别</h3>
        <p class="analysis-block__text">{{ styleStore.analysisResult.subjectAnalysis }}</p>
      </div>

      <!-- 核心元素 -->
      <div v-if="styleStore.analysisResult.coreElements.length" class="analysis-block">
        <h3 class="analysis-block__title">需要保留的核心元素</h3>
        <ul class="analysis-list">
          <li v-for="(el, i) in styleStore.analysisResult.coreElements" :key="i">{{ el }}</li>
        </ul>
      </div>

      <!-- 插画规则 -->
      <div v-if="styleStore.analysisResult.rules" class="analysis-block">
        <h3 class="analysis-block__title">插画规则</h3>
        <div class="rules-grid">
          <div v-if="styleStore.analysisResult.rules.composition" class="rule-item">
            <span class="rule-label">构图</span>
            <span class="rule-value">{{ styleStore.analysisResult.rules.composition }}</span>
          </div>
          <div v-if="styleStore.analysisResult.rules.mainArea" class="rule-item">
            <span class="rule-label">主体区域</span>
            <span class="rule-value">{{ styleStore.analysisResult.rules.mainArea }}</span>
          </div>
          <div v-if="styleStore.analysisResult.rules.negativeSpace" class="rule-item">
            <span class="rule-label">留白</span>
            <span class="rule-value">{{ styleStore.analysisResult.rules.negativeSpace }}</span>
          </div>
          <div v-if="styleStore.analysisResult.rules.style" class="rule-item">
            <span class="rule-label">笔触</span>
            <span class="rule-value">{{ styleStore.analysisResult.rules.style }}</span>
          </div>
          <div v-if="styleStore.analysisResult.rules.colors?.length" class="rule-item">
            <span class="rule-label">色彩</span>
            <span class="rule-value">{{ styleStore.analysisResult.rules.colors.join('、') }}</span>
          </div>
          <div v-if="styleStore.analysisResult.rules.avoid" class="rule-item">
            <span class="rule-label">避免</span>
            <span class="rule-value">{{ styleStore.analysisResult.rules.avoid }}</span>
          </div>
        </div>
      </div>

      <!-- 特殊元素处理 -->
      <div v-if="styleStore.analysisResult.specialNotes" class="analysis-block">
        <h3 class="analysis-block__title">特殊元素处理</h3>
        <p class="analysis-block__text">{{ styleStore.analysisResult.specialNotes }}</p>
      </div>

      <!-- 最终提示词 -->
      <div class="analysis-block">
        <h3 class="analysis-block__title">最终生成提示词（英文）</h3>
        <div class="prompt-box">{{ styleStore.analysisResult.finalPrompt }}</div>
      </div>

      <!-- 诗意小字选择 -->
      <div v-if="styleStore.analysisResult.poeticOptions.length" class="analysis-block">
        <h3 class="analysis-block__title">诗意小字</h3>
        <p class="analysis-block__hint">选择一句小字写在画面下方（可不选）</p>
        <div class="poetic-options">
          <button
            v-for="opt in styleStore.analysisResult.poeticOptions"
            :key="opt"
            class="poetic-chip"
            :class="{ 'poetic-chip--active': styleStore.selectedPoeticText === opt }"
            @click="styleStore.setPoeticText(styleStore.selectedPoeticText === opt ? '' : opt)"
          >
            {{ opt }}
          </button>
        </div>
      </div>
    </section>

    <!-- 提交转换按钮：只要有图片即可转换，无需先分析 -->
    <div v-if="imageStore.imageId" class="convert-action">
      <button
        class="convert-btn font-display"
        :disabled="converting || !canConvert"
        @click="onConvert"
      >
        <span v-if="!converting">开始转换</span>
        <span v-else class="convert-btn__loading">生成中…</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
/* 整体如笔记本纵向流动，章节间以温暖细分隔线区分 */
.home-flow {
  display: flex;
  flex-direction: column;
}

/* 诗意标题：居中、大留白，宋体质感，顶部朱印点睛 */
.hero {
  text-align: center;
  padding: 64px 0 56px;
}
.hero__seal-wrap {
  display: flex;
  justify-content: center;
  margin-bottom: 26px;
}
.hero__seal {
  width: 60px;
  height: 60px;
  border-radius: 6px;
  background: var(--color-primary);
  color: #fff;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 34px;
  line-height: 60px;
  text-align: center;
  box-shadow: var(--shadow-seal);
  position: relative;
}
.hero__seal::after {
  content: "";
  position: absolute;
  right: 4px;
  bottom: 4px;
  width: 9px;
  height: 9px;
  background: rgba(255, 255, 255, 0.18);
  border-radius: 50%;
}
.hero__title {
  font-size: clamp(2rem, 5vw, 2.75rem);
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.08em;
  line-height: 1.4;
}
.hero__subtitle {
  margin-top: 16px;
  font-size: 16px;
  color: var(--color-text-secondary);
  letter-spacing: 0.04em;
}
/* 副标题下的墨线分隔：呼应纸张，收束 Hero */
.hero__rule {
  width: 72px;
  height: 2px;
  margin: 36px auto 0;
  background: linear-gradient(90deg, transparent, var(--color-primary) 30%, var(--color-primary) 70%, transparent);
  opacity: 0.55;
}

/* 章节块：无卡片阴影，仅以细线分隔，留白即结构 */
.notebook-section {
  padding: 44px 0;
  border-top: 1px solid rgba(156, 150, 139, 0.15);
}
.notebook-section:first-of-type {
  border-top: none;
}
.notebook-section__label {
  font-size: 17px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 22px;
  letter-spacing: 0.06em;
  display: flex;
  align-items: center;
  gap: 12px;
}
/* 朱印编号：章节的墨色锚点 */
.ink-stamp {
  width: 32px;
  height: 32px;
  border-radius: 4px;
  background: var(--color-primary);
  color: #fff;
  font-size: 17px;
  line-height: 32px;
  text-align: center;
  flex-shrink: 0;
  box-shadow: var(--shadow-seal);
}

/* 风格描述文字 */
.skill-desc {
  margin-top: 16px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--color-text-secondary);
  letter-spacing: 0.02em;
  text-align: center;
}
.skill-desc--hint {
  opacity: 0.6;
}

/* 冰箱贴拍摄地点输入 */
.fridge-location {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.fridge-location__label {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.06em;
}
.fridge-location__input {
  width: min(320px, 100%);
  padding: 10px 14px;
  font-size: 15px;
  color: var(--color-text);
  background: #fff;
  border: 1px solid rgba(156, 150, 139, 0.35);
  border-radius: 10px;
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  letter-spacing: 0.04em;
}
.fridge-location__input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(200, 68, 43, 0.12);
}
.fridge-location__hint {
  font-size: 12px;
  color: var(--color-text-secondary);
  opacity: 0.7;
  letter-spacing: 0.02em;
}

/* 朱砂转换按钮：纸面上的唯一强调标点 */
.convert-action {
  text-align: center;
  padding: 48px 0 32px;
}
.convert-btn {
  appearance: none;
  border: none;
  cursor: pointer;
  background: var(--color-primary);
  color: #fff;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.1em;
  padding: 15px 48px;
  border-radius: 10px;
  box-shadow: 0 4px 14px rgba(200, 68, 43, 0.28);
  transition: background-color 0.2s ease, transform 0.1s ease, box-shadow 0.2s ease;
}
.convert-btn:hover:not(:disabled) {
  background: var(--color-primary-dark);
  box-shadow: 0 6px 20px rgba(168, 54, 31, 0.32);
}
.convert-btn:active:not(:disabled) {
  transform: translateY(1px);
  box-shadow: 0 2px 8px rgba(168, 54, 31, 0.24);
}
.convert-btn:disabled {
  background: rgba(156, 150, 139, 0.5);
  cursor: not-allowed;
  box-shadow: none;
}
.convert-btn__loading {
  opacity: 0.9;
}

/* 分析按钮：墨色描边，区别于朱砂转换按钮 */
.analyze-btn {
  appearance: none;
  cursor: pointer;
  background: transparent;
  color: var(--color-text);
  border: 2px solid var(--color-text);
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.1em;
  padding: 13px 44px;
  border-radius: 10px;
  transition: all 0.2s ease;
}
.analyze-btn:hover:not(:disabled) {
  background: var(--color-text);
  color: #fff;
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}
.analyze-btn:active:not(:disabled) {
  transform: translateY(0);
}
.analyze-btn:disabled {
  border-color: rgba(156, 150, 139, 0.4);
  color: rgba(156, 150, 139, 0.6);
  cursor: not-allowed;
}

/* 分析结果区域 */
.analysis-result {
  padding: 28px;
  background: rgba(245, 242, 235, 0.5);
  border-radius: 12px;
  border: 1px solid rgba(156, 150, 139, 0.12);
}
.analysis-block {
  margin-bottom: 20px;
}
.analysis-block:last-child {
  margin-bottom: 0;
}
.analysis-block__title {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 8px;
  letter-spacing: 0.04em;
}
.analysis-block__text {
  font-size: 14px;
  line-height: 1.7;
  color: var(--color-text-secondary);
}
.analysis-block__hint {
  font-size: 12px;
  color: var(--color-text-secondary);
  opacity: 0.7;
  margin-bottom: 8px;
}
.analysis-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.analysis-list li {
  font-size: 14px;
  color: var(--color-text-secondary);
  padding: 3px 0;
  padding-left: 16px;
  position: relative;
}
.analysis-list li::before {
  content: "·";
  position: absolute;
  left: 4px;
  color: var(--color-primary);
  font-weight: 700;
}

/* 规则网格 */
.rules-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.rule-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.rule-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  opacity: 0.7;
}
.rule-value {
  font-size: 13px;
  color: var(--color-text);
}

/* 提示词展示框 */
.prompt-box {
  font-size: 13px;
  line-height: 1.6;
  color: var(--color-text);
  background: #fff;
  border: 1px solid rgba(156, 150, 139, 0.2);
  border-radius: 8px;
  padding: 12px;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 200px;
  overflow-y: auto;
}

/* 诗意小字选项 */
.poetic-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.poetic-chip {
  appearance: none;
  cursor: pointer;
  background: #fff;
  border: 1px solid rgba(156, 150, 139, 0.3);
  border-radius: 20px;
  padding: 6px 16px;
  font-size: 14px;
  color: var(--color-text-secondary);
  transition: all 0.2s ease;
  font-family: var(--font-display, serif);
}
.poetic-chip:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.poetic-chip--active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}

/* 移动端：标题与留白收敛 */
@media (max-width: 640px) {
  .hero {
    padding: 40px 0 44px;
  }
  .hero__seal {
    width: 52px;
    height: 52px;
    font-size: 28px;
    line-height: 52px;
  }
  .notebook-section {
    padding: 30px 0;
  }
  .analysis-result {
    padding: 20px;
  }
}
</style>
