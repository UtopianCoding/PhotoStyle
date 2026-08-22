<script setup lang="ts">
// 积分中心页面：余额展示、交易历史、充值、邀请好友
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { getCreditBalance, getCreditHistory, createRechargeOrder, queryOrderStatus, getInviteInfo } from '@/api/credits'
import type { CreditBalanceResponse, CreditTransactionItem, InviteInfoResponse } from '@/types'
import QRCode from 'qrcode'

const userStore = useUserStore()

// 状态
const loading = ref(false)
const activeTab = ref('balance')
const balanceInfo = ref<CreditBalanceResponse | null>(null)
const historyItems = ref<CreditTransactionItem[]>([])
const historyTotal = ref(0)
const historyPage = ref(1)
const historyPageSize = ref(20)
const historyLoading = ref(false)
const inviteInfo = ref<InviteInfoResponse | null>(null)
const rechargeAmount = ref(50)
const rechargeLoading = ref(false)

// 支付弹窗状态
const payDialogVisible = ref(false)
const qrCodeUrl = ref('')
const currentOutTradeNo = ref('')
const currentCredits = ref(0)
const pollingTimer = ref<ReturnType<typeof setInterval> | null>(null)

// 预设充值金额
const presetAmounts = [10, 50, 100, 200]

// 交易类型映射
const transactionTypeMap: Record<string, { label: string; color: string }> = {
  register_bonus: { label: '注册赠送', color: 'success' },
  recharge: { label: '充值', color: 'primary' },
  convert_cost: { label: '转换消耗', color: 'warning' },
  invite_reward: { label: '邀请奖励', color: 'success' },
  invite_bonus: { label: '被邀请奖励', color: 'success' },
  admin_adjust: { label: '管理员调整', color: 'info' },
}

// 加载余额信息
async function loadBalance() {
  try {
    balanceInfo.value = await getCreditBalance()
    userStore.updateLocalProfile({
      credits: balanceInfo.value.credits,
      referralCode: balanceInfo.value.referralCode ?? undefined,
    })
  } catch {
    ElMessage.error('加载积分信息失败')
  }
}

// 加载交易历史
async function loadHistory() {
  historyLoading.value = true
  try {
    const res = await getCreditHistory({
      page: historyPage.value,
      pageSize: historyPageSize.value,
    })
    historyItems.value = res.items
    historyTotal.value = res.total
  } catch {
    ElMessage.error('加载交易历史失败')
  } finally {
    historyLoading.value = false
  }
}

// 加载邀请信息
async function loadInviteInfo() {
  try {
    inviteInfo.value = await getInviteInfo()
  } catch {
    ElMessage.error('加载邀请信息失败')
  }
}

// 停止轮询
function stopPolling() {
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value)
    pollingTimer.value = null
  }
}

// 轮询查询订单状态
function startPolling(outTradeNo: string) {
  stopPolling()
  pollingTimer.value = setInterval(async () => {
    try {
      const res = await queryOrderStatus(outTradeNo)
      if (res.tradeStatus === 'TRADE_SUCCESS' || res.tradeStatus === 'TRADE_FINISHED') {
        stopPolling()
        payDialogVisible.value = false
        ElMessage.success(`支付成功，+${currentCredits.value} 积分已到账`)
        await loadBalance()
        await loadHistory()
      } else if (res.tradeStatus === 'TRADE_CLOSED') {
        stopPolling()
        payDialogVisible.value = false
        ElMessage.warning('订单已过期，请重新充值')
      }
    } catch {
      // 查询失败继续轮询
    }
  }, 3000)
}

// 关闭支付弹窗
function closePayDialog() {
  stopPolling()
  payDialogVisible.value = false
  qrCodeUrl.value = ''
  currentOutTradeNo.value = ''
}

// 充值
async function handleRecharge() {
  if (rechargeAmount.value <= 0) {
    ElMessage.warning('请输入有效的充值金额')
    return
  }
  rechargeLoading.value = true
  try {
    const res = await createRechargeOrder({ amount: rechargeAmount.value })

    // 如果返回了 qrCode，说明是真实支付宝支付（模拟充值 qrCode 为空）
    if (res.qrCode) {
      currentOutTradeNo.value = res.outTradeNo
      currentCredits.value = res.credits

      // 生成二维码
      qrCodeUrl.value = await QRCode.toDataURL(res.qrCode, {
        width: 240,
        margin: 2,
        color: { dark: '#333333', light: '#ffffff' },
      })

      payDialogVisible.value = true
      startPolling(res.outTradeNo)
    } else {
      // 模拟充值（qrCode 为空，积分直接到账）
      ElMessage.success(`充值成功，+${res.credits} 积分`)
      await loadBalance()
      await loadHistory()
    }
  } catch {
    ElMessage.error('充值失败')
  } finally {
    rechargeLoading.value = false
  }
}

// 复制邀请链接
async function copyInviteLink() {
  if (!inviteInfo.value?.inviteLink) return
  try {
    await navigator.clipboard.writeText(inviteInfo.value.inviteLink)
    ElMessage.success('邀请链接已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

// 分页变化
function handlePageChange(page: number) {
  historyPage.value = page
  loadHistory()
}

// Tab 切换
function handleTabChange(tab: string) {
  activeTab.value = tab
  if (tab === 'history') {
    loadHistory()
  } else if (tab === 'invite') {
    loadInviteInfo()
  }
}

// 格式化交易类型
function formatTransactionType(type: string): string {
  return transactionTypeMap[type]?.label ?? type
}

// 获取交易类型颜色
function getTransactionTypeColor(type: string): string {
  return transactionTypeMap[type]?.color ?? 'info'
}

// 格式化金额显示
function formatAmount(amount: number): string {
  return amount > 0 ? `+${amount}` : `${amount}`
}

onMounted(() => {
  loadBalance()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="credits-page">
    <div class="credits-page__inner">
      <!-- 页眉 -->
      <header class="credits-page__header">
        <span class="credits-page__label font-mono-label">CREDITS CENTER</span>
        <h1 class="credits-page__title font-display">积分中心</h1>
      </header>

      <!-- 余额卡片 -->
      <div class="credits-balance-card">
        <div class="credits-balance-card__content">
          <div class="credits-balance-card__label">当前积分余额</div>
          <div class="credits-balance-card__amount">
            {{ balanceInfo?.credits ?? 0 }}
          </div>
          <div class="credits-balance-card__hint">
            每次风格转换消耗 2 积分
          </div>
        </div>
        <div class="credits-balance-card__stats">
          <div class="credits-balance-card__stat">
            <span class="credits-balance-card__stat-value">{{ balanceInfo?.inviteCount ?? 0 }}</span>
            <span class="credits-balance-card__stat-label">邀请好友</span>
          </div>
        </div>
      </div>

      <!-- Tab 切换 -->
      <el-tabs v-model="activeTab" @tab-change="handleTabChange" class="credits-tabs">
        <!-- 充值 -->
        <el-tab-pane label="充值" name="recharge">
          <div class="credits-section">
            <h3 class="credits-section__title">选择充值金额</h3>
            <div class="recharge-presets">
              <button
                v-for="amount in presetAmounts"
                :key="amount"
                class="recharge-preset-btn"
                :class="{ 'is-active': rechargeAmount === amount }"
                @click="rechargeAmount = amount"
              >
                <span class="recharge-preset-btn__amount">{{ amount }}</span>
                <span class="recharge-preset-btn__label">积分</span>
              </button>
            </div>
            <div class="recharge-custom">
              <el-input-number
                v-model="rechargeAmount"
                :min="1"
                :max="10000"
                :step="10"
                controls-position="right"
                placeholder="自定义金额"
              />
            </div>
            <el-button
              type="primary"
              size="large"
              :loading="rechargeLoading"
              @click="handleRecharge"
              class="recharge-submit-btn"
            >
              立即充值 {{ rechargeAmount }} 积分
            </el-button>
          </div>
        </el-tab-pane>

        <!-- 交易历史 -->
        <el-tab-pane label="交易历史" name="history">
          <div class="credits-section">
            <div v-loading="historyLoading" class="history-list">
              <div v-if="historyItems.length === 0" class="history-empty">
                暂无交易记录
              </div>
              <div v-else>
                <div
                  v-for="item in historyItems"
                  :key="item.transactionId"
                  class="history-item"
                >
                  <div class="history-item__left">
                    <div class="history-item__type">
                      <el-tag :type="getTransactionTypeColor(item.transactionType)" size="small">
                        {{ formatTransactionType(item.transactionType) }}
                      </el-tag>
                    </div>
                    <div class="history-item__desc">{{ item.description }}</div>
                    <div class="history-item__time">{{ item.createdAt }}</div>
                  </div>
                  <div class="history-item__right">
                    <div
                      class="history-item__amount"
                      :class="{ 'is-positive': item.amount > 0, 'is-negative': item.amount < 0 }"
                    >
                      {{ formatAmount(item.amount) }}
                    </div>
                    <div class="history-item__balance">余额: {{ item.balanceAfter }}</div>
                  </div>
                </div>
                <div class="history-pagination">
                  <el-pagination
                    v-model:current-page="historyPage"
                    :page-size="historyPageSize"
                    :total="historyTotal"
                    layout="prev, pager, next"
                    @current-change="handlePageChange"
                  />
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- 邀请好友 -->
        <el-tab-pane label="邀请好友" name="invite">
          <div class="credits-section">
            <div class="invite-info">
              <div class="invite-info__stats">
                <div class="invite-info__stat">
                  <span class="invite-info__stat-value">{{ inviteInfo?.inviteCount ?? 0 }}</span>
                  <span class="invite-info__stat-label">已邀请</span>
                </div>
                <div class="invite-info__stat">
                  <span class="invite-info__stat-value">{{ inviteInfo?.totalRewards ?? 0 }}</span>
                  <span class="invite-info__stat-label">获得积分</span>
                </div>
                <div class="invite-info__stat">
                  <span class="invite-info__stat-value">{{ inviteInfo?.rewardPerInvite ?? 6 }}</span>
                  <span class="invite-info__stat-label">每次奖励</span>
                </div>
              </div>

              <div class="invite-link-section">
                <h4 class="invite-link-section__title">您的邀请链接</h4>
                <div class="invite-link-box">
                  <input
                    type="text"
                    :value="inviteInfo?.inviteLink"
                    readonly
                    class="invite-link-input"
                  />
                  <el-button type="primary" @click="copyInviteLink">
                    复制链接
                  </el-button>
                </div>
                <p class="invite-link-hint">
                  邀请码: <code>{{ inviteInfo?.referralCode }}</code>
                </p>
              </div>

              <div class="invite-rules">
                <h4 class="invite-rules__title">邀请规则</h4>
                <ul class="invite-rules__list">
                  <li>好友通过您的邀请链接注册账号</li>
                  <li>好友注册成功后，您将获得 <strong>6 积分</strong> 奖励</li>
                  <li>好友也将获得 <strong>10 积分</strong> 注册奖励</li>
                  <li>邀请人数无上限，奖励即时到账</li>
                </ul>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>

      <!-- 支付宝扫码支付弹窗 -->
      <el-dialog
        v-model="payDialogVisible"
        title="扫码支付"
        width="320px"
        :close-on-click-modal="false"
        @close="closePayDialog"
      >
        <div class="pay-dialog-content">
          <div class="pay-dialog-amount">
            需支付 <strong>{{ rechargeAmount }}</strong> 元
          </div>
          <div class="pay-dialog-qrcode">
            <img v-if="qrCodeUrl" :src="qrCodeUrl" alt="支付二维码" />
            <div v-else class="pay-dialog-loading">生成二维码中...</div>
          </div>
          <div class="pay-dialog-tip">
            请使用支付宝扫描二维码支付
          </div>
          <div class="pay-dialog-hint">
            支付成功后积分将自动到账
          </div>
        </div>
      </el-dialog>
    </div>
  </div>
</template>

<style scoped>
.credits-page {
  background: var(--color-bg);
  min-height: calc(100vh - 60px);
  padding: 40px 24px;
}

.credits-page__inner {
  max-width: 900px;
  margin: 0 auto;
}

/* 页眉 */
.credits-page__header {
  margin-bottom: 32px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--color-border);
}

.credits-page__label {
  display: inline-block;
  font-size: 11px;
  letter-spacing: 0.14em;
  color: var(--color-text-placeholder);
  text-transform: uppercase;
  margin-bottom: 12px;
}

.credits-page__title {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.04em;
  margin: 0;
}

/* 余额卡片 */
.credits-balance-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 32px;
  background: linear-gradient(135deg, var(--color-bg-card) 0%, var(--color-accent-bg) 100%);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  margin-bottom: 32px;
  box-shadow: var(--shadow-md);
}

.credits-balance-card__label {
  font-size: 13px;
  color: var(--color-text-secondary);
  letter-spacing: 0.04em;
  margin-bottom: 8px;
}

.credits-balance-card__amount {
  font-size: 48px;
  font-weight: 700;
  color: var(--color-primary);
  font-family: var(--font-display);
  line-height: 1;
  margin-bottom: 8px;
}

.credits-balance-card__hint {
  font-size: 12px;
  color: var(--color-text-placeholder);
}

.credits-balance-card__stats {
  display: flex;
  gap: 32px;
}

.credits-balance-card__stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.credits-balance-card__stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text);
}

.credits-balance-card__stat-label {
  font-size: 12px;
  color: var(--color-text-secondary);
}

/* Tab 切换 */
.credits-tabs {
  margin-top: 24px;
}

.credits-section {
  padding: 24px 0;
}

.credits-section__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 20px;
}

/* 充值预设 */
.recharge-presets {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.recharge-preset-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 20px 16px;
  background: var(--color-bg-card);
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s ease;
}

.recharge-preset-btn:hover {
  border-color: var(--color-primary-light);
  transform: translateY(-2px);
}

.recharge-preset-btn.is-active {
  border-color: var(--color-primary);
  background: var(--color-primary-light-bg);
}

.recharge-preset-btn__amount {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text);
}

.recharge-preset-btn__label {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.recharge-custom {
  margin-bottom: 20px;
}

.recharge-submit-btn {
  width: 100%;
  font-size: 16px;
  letter-spacing: 0.06em;
}

.recharge-hint {
  text-align: center;
  font-size: 12px;
  color: var(--color-text-placeholder);
  margin-top: 16px;
}

/* 交易历史 */
.history-list {
  min-height: 300px;
}

.history-empty {
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-placeholder);
  font-size: 14px;
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--color-border);
}

.history-item:last-child {
  border-bottom: none;
}

.history-item__left {
  flex: 1;
}

.history-item__type {
  margin-bottom: 6px;
}

.history-item__desc {
  font-size: 14px;
  color: var(--color-text);
  margin-bottom: 4px;
}

.history-item__time {
  font-size: 12px;
  color: var(--color-text-placeholder);
}

.history-item__right {
  text-align: right;
}

.history-item__amount {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 4px;
}

.history-item__amount.is-positive {
  color: var(--color-success);
}

.history-item__amount.is-negative {
  color: var(--color-warning);
}

.history-item__balance {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.history-pagination {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}

/* 邀请好友 */
.invite-info__stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.invite-info__stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 20px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.invite-info__stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-primary);
}

.invite-info__stat-label {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.invite-link-section {
  margin-bottom: 32px;
}

.invite-link-section__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 12px;
}

.invite-link-box {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
}

.invite-link-input {
  flex: 1;
  padding: 10px 14px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--color-text);
  font-family: var(--font-mono);
}

.invite-link-hint {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin: 0;
}

.invite-link-hint code {
  background: var(--color-accent-bg);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: var(--font-mono);
  color: var(--color-primary);
}

.invite-rules {
  padding: 20px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.invite-rules__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 12px;
}

.invite-rules__list {
  margin: 0;
  padding-left: 20px;
}

.invite-rules__list li {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.8;
}

.invite-rules__list li strong {
  color: var(--color-primary);
  font-weight: 600;
}

@media (max-width: 768px) {
  .credits-balance-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 24px;
  }

  .recharge-presets {
    grid-template-columns: repeat(2, 1fr);
  }

  .invite-info__stats {
    grid-template-columns: 1fr;
  }

  .invite-link-box {
    flex-direction: column;
  }
}

/* 支付宝支付弹窗 */
.pay-dialog-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 8px 0;
}

.pay-dialog-amount {
  font-size: 16px;
  color: var(--color-text);
}

.pay-dialog-amount strong {
  font-size: 24px;
  color: var(--color-primary);
  font-family: var(--font-display);
}

.pay-dialog-qrcode {
  width: 240px;
  height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

.pay-dialog-qrcode img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.pay-dialog-loading {
  color: var(--color-text-placeholder);
  font-size: 14px;
}

.pay-dialog-tip {
  font-size: 14px;
  color: var(--color-text);
}

.pay-dialog-hint {
  font-size: 12px;
  color: var(--color-text-placeholder);
}
</style>
