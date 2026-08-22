// 积分相关接口
import { request } from './request'
import type {
  CreditBalanceResponse,
  CreditHistoryResponse,
  InviteInfoResponse,
  RechargeRequest,
} from '@/types'

/** 支付订单响应 */
export interface CreateOrderResponse {
  outTradeNo: string
  qrCode: string
  amount: number
  credits: number
}

/** 订单状态查询响应 */
export interface OrderStatusResponse {
  status: string
  tradeStatus: string
  tradeNo: string
}

/**
 * 获取积分余额和邀请信息
 */
export function getCreditBalance() {
  return request<CreditBalanceResponse>({
    url: '/credits/balance',
    method: 'get',
  })
}

/**
 * 获取积分交易历史
 */
export function getCreditHistory(params: { page: number; pageSize: number }) {
  return request<CreditHistoryResponse>({
    url: '/credits/history',
    method: 'get',
    params,
  })
}

/**
 * 创建充值订单（扫码支付）
 */
export function createRechargeOrder(data: RechargeRequest) {
  return request<CreateOrderResponse>({
    url: '/credits/create-order',
    method: 'post',
    data,
  })
}

/**
 * 查询订单支付状态
 */
export function queryOrderStatus(outTradeNo: string) {
  return request<OrderStatusResponse>({
    url: '/credits/query-order',
    method: 'get',
    params: { out_trade_no: outTradeNo },
  })
}

/**
 * 获取邀请信息
 */
export function getInviteInfo() {
  return request<InviteInfoResponse>({
    url: '/credits/invite-info',
    method: 'get',
  })
}
