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
    selectedSkillId.value = skillId
  }

  /** 设置模型服务方 */
  function setProvider(provider: string) {
    selectedProvider.value = provider
  }

  /** 设置附加提示词 */
  function setExtraPrompt(prompt: string) {
    extraPrompt.value = prompt
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
    options,
    analysisResult,
    selectedPoeticText,
    analyzing,
    isAnalyzed,
    setSkills,
    setSkillId,
    setProvider,
    setExtraPrompt,
    setOptions,
    setAnalysisResult,
    setPoeticText,
    reset,
  }
})
