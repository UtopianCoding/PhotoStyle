// 风格转换逻辑组合式函数：分析图片 → 提交任务 → 启动轮询
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { analyze as analyzeApi, convert as convertApi } from '@/api/style'
import { useImageStore } from '@/stores/image'
import { useStyleStore } from '@/stores/style'
import { useTaskStore } from '@/stores/task'
import type { AnalysisResult, StyleTask } from '@/types'

/** 默认使用的技能 ID（分析失败或未返回时兜底） */
const DEFAULT_SKILL_ID = 'photo-revival'

/** 从分析结果中取推荐技能，兜底默认 */
function resolveSkillId(result: AnalysisResult | null | undefined): string {
  return result?.recommendedSkillId || DEFAULT_SKILL_ID
}

export function useConvert() {
  const converting = ref(false)
  const imageStore = useImageStore()
  const styleStore = useStyleStore()
  const taskStore = useTaskStore()

  /** 分析图片，生成结构化提示词 + 诗意小字选项，同时拿到后端推荐的技能 ID */
  async function analyze(): Promise<AnalysisResult | null> {
    if (!imageStore.imageId) {
      ElMessage.warning('请先上传图片')
      return null
    }
    styleStore.analyzing = true
    try {
      const result = await analyzeApi({
        imageId: imageStore.imageId,
        // 此处 skillId 只是作为历史兼容字段传，真正的推荐技能由分析接口返回
        skillId: DEFAULT_SKILL_ID,
        extraPrompt: styleStore.extraPrompt,
      })
      styleStore.setAnalysisResult(result)
      ElMessage.success(
        `图片分析完成（推荐风格：${
          result.recommendedSkillId === 'city-editorial' ? '城市风景海报' : '老照片复兴'
        }）`,
      )
      return result
    } catch {
      ElMessage.error('图片分析失败')
      return null
    } finally {
      styleStore.analyzing = false
    }
  }

  /** 提交风格转换任务：使用分析结果推荐的技能 ID */
  async function convert(): Promise<StyleTask | null> {
    if (!imageStore.imageId) {
      ElMessage.warning('请先上传图片')
      return null
    }
    if (!styleStore.analysisResult) {
      ElMessage.warning('请先分析图片')
      return null
    }
    converting.value = true
    try {
      const skillId = resolveSkillId(styleStore.analysisResult)
      const task = await convertApi({
        imageId: imageStore.imageId,
        skillId,
        provider: styleStore.selectedProvider,
        extraPrompt: styleStore.extraPrompt,
        options: styleStore.options,
        finalPrompt: styleStore.analysisResult.finalPrompt,
        poeticText: styleStore.selectedPoeticText || undefined,
      })
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

  return { converting, analyze, convert }
}
