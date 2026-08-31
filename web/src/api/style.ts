// 风格转换相关接口：分析图片、提交转换、查询任务、取消任务、删除结果
import { request } from './request'
import type { AnalysisResult, StyleResult, StyleTask } from '@/types'

/** 图片分析参数（skillId 可选，默认 photo-revival） */
export interface AnalyzeParams {
  imageId: string
  skillId?: string
  extraPrompt?: string
  /** 拍摄地点：冰箱贴等需要英文城市名排版的技能使用，如「昆明/中国」 */
  location?: string
  /** 签名文字：马克笔童画等需要签名的技能使用 */
  signature?: string
  /** 通用输入变量：技能声明的 inputVariables 由用户填写，替换提示词模板中的 {{KEY}} 占位符 */
  variables?: Record<string, string>
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
  /** 拍摄地点：冰箱贴等需要英文城市名排版的技能使用，如「昆明/中国」 */
  location?: string
  /** 签名文字：马克笔童画等需要签名的技能使用 */
  signature?: string
  /** 通用输入变量：技能声明的 inputVariables 由用户填写，替换提示词模板中的 {{KEY}} 占位符 */
  variables?: Record<string, string>
  /** 重新生成时用户填写的修改意见（将在原提示词基础上叠加后交给模型） */
  feedback?: string
  /** 原任务ID：提供时在原任务内重新生成并替换同 provider 的旧结果，不创建新任务 */
  regenTaskId?: string
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
 * 查询任务状态（需登录）
 */
export function getTaskStatus(taskId: string) {
  return request<StyleTask>({ url: `/style/tasks/${taskId}`, method: 'get' })
}

/**
 * 公开查看任务结果（无需登录，用于分享海报扫码查看）
 */
export function getPublicTaskStatus(taskId: string) {
  return request<StyleTask>({ url: `/style/public/tasks/${taskId}`, method: 'get' })
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

/**
 * 删除指定结果（多模型场景下用户可删除不想要的结果）
 */
export function removeTaskResults(taskId: string, resultIds: string[]) {
  return request<StyleResult[]>({
    url: `/style/tasks/${taskId}/results`,
    method: 'delete',
    data: { resultIds },
  })
}
