// 风格状态管理：技能列表、选中技能、模型服务方、附加提示词、转换选项、分析结果、诗意小字
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AnalysisResult, Skill } from '@/types'

export const useStyleStore = defineStore('style', () => {
  // 可用技能列表
  const skills = ref<Skill[]>([])
  // 用户选中的技能 ID（空字符串表示未选择，使用分析推荐）
  const selectedSkillId = ref<string>('')
  // 选中的模型服务方
  const selectedProvider = ref<string>('')
  // 附加提示词
  const extraPrompt = ref<string>('')
  // 通用输入变量：技能声明的 inputVariables 由用户填写（key -> 用户输入值）
  const skillVariables = ref<Record<string, string>>({})
  // 转换选项
  const options = ref<Record<string, unknown>>({})
  // 图片分析结果
  const analysisResult = ref<AnalysisResult | null>(null)
  // 用户选择的诗意小字
  const selectedPoeticText = ref<string>('')
  // 是否正在分析
  const analyzing = ref<boolean>(false)

  // 是否已完成分析
  const isAnalyzed = computed(() => !!analysisResult.value)

  /** 设置技能列表 */
  function setSkills(list: Skill[]) {
    skills.value = list
  }

  /** 设置选中技能 ID */
  function setSkillId(skillId: string) {
    if (skillId === selectedSkillId.value) return
    // 切换风格后，之前针对旧风格生成的分析结果（subject_analysis / finalPrompt 等）
    // 已失效。必须清除，否则 convert 会把旧风格的 finalPrompt 发给模型，导致生成风格错乱。
    if (analysisResult.value && analysisResult.value.recommendedSkillId !== skillId) {
      analysisResult.value = null
      selectedPoeticText.value = ''
    }
    selectedSkillId.value = skillId
    // 切换风格后清空上一技能的输入变量（避免把地点的值带到签名等场景）
    skillVariables.value = {}
  }

  /** 设置模型服务方 */
  function setProvider(provider: string) {
    selectedProvider.value = provider
  }

  /** 设置附加提示词 */
  function setExtraPrompt(prompt: string) {
    extraPrompt.value = prompt
  }

  /** 设置通用输入变量（技能声明的 inputVariables） */
  function setSkillVariable(key: string, value: string) {
    skillVariables.value = { ...skillVariables.value, [key]: value }
  }

  /** 获取当前选中技能的输入变量定义 */
  function getCurrentInputVariables(): NonNullable<Skill['inputVariables']> {
    const skill = skills.value.find((s) => s.id === selectedSkillId.value)
    return skill?.inputVariables || []
  }

  /** 校验当前技能必填输入变量是否已填写 */
  function isRequiredVariablesFilled(): boolean {
    return getCurrentInputVariables()
      .filter((v) => v.required)
      .every((v) => (skillVariables.value[v.key] || '').trim().length > 0)
  }

  /** 设置转换选项 */
  function setOptions(opts: Record<string, unknown>) {
    options.value = opts
  }

  /** 设置分析结果 */
  function setAnalysisResult(result: AnalysisResult | null) {
    analysisResult.value = result
    if (!result) {
      selectedPoeticText.value = ''
    }
  }

  /** 设置诗意小字 */
  function setPoeticText(text: string) {
    selectedPoeticText.value = text
  }

  /** 重置风格状态 */
  function reset() {
    selectedProvider.value = ''
    extraPrompt.value = ''
    skillVariables.value = {}
    options.value = {}
    analysisResult.value = null
    selectedPoeticText.value = ''
    analyzing.value = false
  }

  return {
    skills,
    selectedSkillId,
    selectedProvider,
    extraPrompt,
    skillVariables,
    options,
    analysisResult,
    selectedPoeticText,
    analyzing,
    isAnalyzed,
    setSkills,
    setSkillId,
    setProvider,
    setExtraPrompt,
    setSkillVariable,
    getCurrentInputVariables,
    isRequiredVariablesFilled,
    setOptions,
    setAnalysisResult,
    setPoeticText,
    reset,
  }
})
