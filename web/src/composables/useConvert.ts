// 风格转换逻辑组合式函数：分析图片 → 选择风格 → 提交任务 → 启动轮询
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { analyze as analyzeApi, convert as convertApi } from '@/api/style'
import { useImageStore } from '@/stores/image'
import { useStyleStore } from '@/stores/style'
import { useTaskStore } from '@/stores/task'
import type { AnalysisResult, StyleTask } from '@/types'

/** 默认使用的技能 ID（分析失败或未返回时兜底） */
const DEFAULT_SKILL_ID = 'photo-revival'

/** skill_id → 中文名称映射（用于提示消息） */
const SKILL_NAME_MAP: Record<string, string> = {
  'photo-revival': '老照片复兴',
  'city-editorial': '城市风景海报',
  'photo-abstract-editorial': '照片抽象编辑',
  'fridge-magnet': '旅行冰箱贴',
  'ink-minimalist': '水墨扁平重构插画',
  'marker-child-doodle': '马克笔童画',
  'scenes-gathered-zine': '实景拼贴',
}

/** 获取技能中文名称 */
export function getSkillName(skillId: string): string {
  return SKILL_NAME_MAP[skillId] || skillId
}

/** 优先使用用户手动选择的技能，否则使用分析推荐的技能，兜底默认 */
function resolveSkillId(
  selected: string,
  result: AnalysisResult | null | undefined,
): string {
  return selected || result?.recommendedSkillId || DEFAULT_SKILL_ID
}

export function useConvert() {
  const converting = ref(false)
  const imageStore = useImageStore()
  const styleStore = useStyleStore()
  const taskStore = useTaskStore()

  /** 分析图片，按用户选择的风格生成提示词 + 诗意小字选项 */
  async function analyze(): Promise<AnalysisResult | null> {
    if (!imageStore.imageId) {
      ElMessage.warning('请先上传图片')
      return null
    }
    styleStore.analyzing = true
    try {
      // 用户手动选择了风格则按该风格分析；未选择时留空，由后端自动推荐
      const params: Parameters<typeof analyzeApi>[0] = {
        imageId: imageStore.imageId,
        skillId: styleStore.selectedSkillId || undefined,
        extraPrompt: styleStore.extraPrompt,
      }
      // 技能声明的输入变量（地点/签名等）随分析请求一并传递，供后端生成提示词
      const vars = collectVariables()
      if (Object.keys(vars).length > 0) {
        params.variables = vars
      }
      const result = await analyzeApi(params)
      styleStore.setAnalysisResult(result)
      // 分析完成后，如果用户未手动选择技能，则自动选中推荐的技能
      if (!styleStore.selectedSkillId && result.recommendedSkillId) {
        styleStore.setSkillId(result.recommendedSkillId)
      }
      ElMessage.success(
        `图片分析完成（推荐风格：${getSkillName(result.recommendedSkillId)}）`,
      )
      return result
    } catch {
      ElMessage.error('图片分析失败')
      return null
    } finally {
      styleStore.analyzing = false
    }
  }

  /** 收集当前技能需要用户填写的输入变量（仅非空值） */
  function collectVariables(): Record<string, string> {
    const vars: Record<string, string> = {}
    const skill = styleStore.skills.find((s) => s.id === styleStore.selectedSkillId)
    const defs = skill?.inputVariables || []
    for (const def of defs) {
      const value = (styleStore.skillVariables[def.key] || '').trim()
      if (value) vars[def.key] = value
    }
    return vars
  }

  /** 提交风格转换任务：优先使用用户选择的技能，否则使用推荐的技能 */
  async function convert(): Promise<StyleTask | null> {
    if (!imageStore.imageId) {
      ElMessage.warning('请先上传图片')
      return null
    }
    const skillId = resolveSkillId(
      styleStore.selectedSkillId,
      styleStore.analysisResult,
    )
    // 校验当前技能必填输入变量是否已填写
    if (!styleStore.isRequiredVariablesFilled()) {
      ElMessage.warning('请先填写必填输入内容（如拍摄地点）')
      return null
    }
    converting.value = true
    try {
      const params: Parameters<typeof convertApi>[0] = {
        imageId: imageStore.imageId,
        skillId,
        provider: styleStore.selectedProvider,
        extraPrompt: styleStore.extraPrompt,
        options: styleStore.options,
        finalPrompt: styleStore.analysisResult?.finalPrompt,
        poeticText: styleStore.selectedPoeticText || undefined,
      }
      // 技能声明的输入变量（地点/签名等）随转换请求一并传递
      const vars = collectVariables()
      if (Object.keys(vars).length > 0) {
        params.variables = vars
      }
      const task = await convertApi(params)
      taskStore.setTask(task)
      taskStore.poll()
      ElMessage.success('已提交转换任务')
      return task
    } catch {
      ElMessage.error('提交转换失败')
      return null
    } finally {
      converting.value = false
    }
  }

  /** 基于原提示词 + 修改意见重新生成（不重新分析图片） */
  async function regenerate(params: {
    imageId: string
    skillId: string
    finalPrompt: string
    feedback: string
    location?: string
    provider?: string
    /** 原任务ID：提供时在原任务内替换同 provider 的旧结果（不创建新任务） */
    regenTaskId?: string
  }): Promise<StyleTask | null> {
    if (!params.finalPrompt?.trim()) {
      ElMessage.warning('缺少原图提示词，无法重新生成')
      return null
    }
    if (!params.feedback?.trim()) {
      ElMessage.warning('请先填写修改意见')
      return null
    }
    converting.value = true
    try {
      const task = await convertApi({
        imageId: params.imageId,
        skillId: params.skillId,
        finalPrompt: params.finalPrompt,
        feedback: params.feedback.trim(),
        location: params.location,
        provider: params.provider || '',
        regenTaskId: params.regenTaskId,
      })
      if (params.regenTaskId) {
        // 原任务内替换：由结果页自行重启轮询，这里不启动独立轮询
        return task
      }
      taskStore.setTask(task)
      taskStore.poll()
      ElMessage.success('已提交重新生成任务')
      return task
    } catch {
      ElMessage.error('提交失败')
      return null
    } finally {
      converting.value = false
    }
  }

  return { converting, analyze, convert, regenerate }
}
