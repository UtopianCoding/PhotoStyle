// 风格转换相关接口：分析图片、提交转换、查询任务、取消任务
import { request } from './request'
import type { AnalysisResult, StyleTask } from '@/types'

/** 图片分析参数（skillId 可选，默认 photo-revival） */
export interface AnalyzeParams {
  imageId: string
  skillId?: string
  extraPrompt?: string
}

/** 提交转换任务参数（skillId 可选，默认 photo-revival） */
export interface ConvertParams {
  imageId: string
  skillId?: string
  provider?: string
  extraPrompt?: string
  options?: Record<string, unknown>
  finalPrompt?: string
  poeticText?: string
}

/**
 * 分析图片，生成结构化提示词 + 诗意小字选项
 */
export function analyze(params: AnalyzeParams) {
  return request<AnalysisResult>({
    url: '/style/analyze',
    method: 'post',
    data: params,
  })
}

/**
 * 提交风格转换任务
 */
export function convert(params: ConvertParams) {
  return request<StyleTask>({
    url: '/style/convert',
    method: 'post',
    data: params,
  })
}

/**
 * 查询任务状态
 */
export function getTaskStatus(taskId: string) {
  return request<StyleTask>({ url: `/style/tasks/${taskId}`, method: 'get' })
}

/**
 * 取消任务
 */
export function cancelTask(taskId: string) {
  return request<StyleTask>({
    url: `/style/tasks/${taskId}/cancel`,
    method: 'post',
  })
}
