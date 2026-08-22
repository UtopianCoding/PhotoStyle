<script setup lang="ts">
// 登录 / 注册页：切换模式并提交表单，注册时需邮箱验证码
import { ref, reactive, onBeforeUnmount, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { sendVerificationCode } from '@/api/auth'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// 当前模式：登录 / 注册
const mode = ref<'login' | 'register'>('login')
const loading = ref(false)
const formRef = ref<FormInstance>()

const form = reactive({
  nickname: '',
  email: '',
  password: '',
  code: '',
  referralCode: '',
})

// 验证码倒计时
const countdown = ref(0)
const sendingCode = ref(false)
let countdownTimer: ReturnType<typeof setInterval> | null = null

// 表单校验规则
const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '至少 6 位', trigger: 'blur' },
  ],
  nickname: [{ required: false }],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码为 6 位数字', trigger: 'blur' },
  ],
  referralCode: [{ required: false }],
}

// 页面加载时检查 URL 中的邀请码
onMounted(() => {
  const refCode = route.query.ref as string
  if (refCode) {
    form.referralCode = refCode
    mode.value = 'register'
    ElMessage.success('已自动填入邀请码')
  }
})

/** 发送验证码 */
async function onSendCode() {
  if (!form.email) {
    ElMessage.warning('请先输入邮箱')
    return
  }
  // 简单校验邮箱格式
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
    ElMessage.warning('邮箱格式不正确')
    return
  }
  if (countdown.value > 0) return

  sendingCode.value = true
  try {
    await sendVerificationCode(form.email)
    ElMessage.success('验证码已发送')
    // 启动倒计时
    countdown.value = 60
    countdownTimer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0 && countdownTimer) {
        clearInterval(countdownTimer)
        countdownTimer = null
      }
    }, 1000)
  } catch {
    // 拦截器已提示
  } finally {
    sendingCode.value = false
  }
}

/** 提交表单 */
async function onSubmit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    if (mode.value === 'login') {
      await userStore.login(form.email, form.password)
      ElMessage.success('登录成功')
    } else {
      await userStore.register(
        form.email,
        form.password,
        form.code,
        form.nickname,
        form.referralCode || undefined
      )
      ElMessage.success('注册成功')
    }
    router.push('/')
  } catch {
    ElMessage.error(mode.value === 'login' ? '登录失败' : '注册失败')
  } finally {
    loading.value = false
  }
}

/** 切换登录 / 注册模式 */
function switchMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
}

onBeforeUnmount(() => {
  if (countdownTimer) clearInterval(countdownTimer)
})
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <!-- 朱印置于顶端，作为入口签名 -->
      <div class="login-card__seal">影</div>
      <h1 class="login-card__title font-display">
        {{ mode === 'login' ? '登录' : '注册' }}
      </h1>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item v-if="mode === 'register'" label="昵称" prop="nickname">
          <el-input v-model="form.nickname" placeholder="请输入昵称" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <!-- 验证码（仅注册模式，紧跟邮箱下方） -->
        <el-form-item v-if="mode === 'register'" label="验证码" prop="code">
          <div class="login-card__code-row">
            <el-input
              v-model="form.code"
              placeholder="6 位验证码"
              maxlength="6"
              class="login-card__code-input"
            />
            <el-button
              :disabled="countdown > 0"
              :loading="sendingCode"
              @click="onSendCode"
              class="login-card__code-btn"
            >
              {{ countdown > 0 ? `${countdown}s` : '发送验证码' }}
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
        <!-- 邀请码（仅注册模式，可选） -->
        <el-form-item v-if="mode === 'register'" label="邀请码（可选）" prop="referralCode">
          <el-input
            v-model="form.referralCode"
            placeholder="如有邀请码请填写"
            maxlength="8"
          />
        </el-form-item>
        <el-button type="primary" class="w-full login-card__submit" size="large" :loading="loading" @click="onSubmit">
          {{ mode === 'login' ? '登录' : '注册' }}
        </el-button>
      </el-form>
      <p class="login-card__switch">
        <span class="login-card__switch-link" @click="switchMode">
          {{ mode === 'login' ? '没有账号？去注册' : '已有账号？去登录' }}
        </span>
      </p>
    </div>
  </div>
</template>

<style scoped>
/* 米纸底 + 极淡暖渐变，呼应纸张呼吸 */
.login-page {
  min-height: calc(100vh - 60px);
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    linear-gradient(160deg, rgba(232, 224, 213, 0.5) 0%, rgba(245, 242, 236, 0.2) 60%, var(--color-bg) 100%);
  padding: 16px;
}
.login-card {
  width: 100%;
  max-width: 380px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 40px 32px 32px;
  box-shadow: var(--shadow-lg);
  animation: ink-fade-up 0.5s ease-out both;
}
/* 朱印：与页首一致的签名方印，带立体感 */
.login-card__seal {
  width: 44px;
  height: 44px;
  margin: 0 auto 20px;
  border-radius: 4px;
  background: var(--color-primary);
  color: #fff;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 26px;
  line-height: 44px;
  text-align: center;
  box-shadow: var(--shadow-seal);
  position: relative;
}
.login-card__seal::after {
  content: "";
  position: absolute;
  right: 3px;
  bottom: 3px;
  width: 7px;
  height: 7px;
  background: rgba(255, 255, 255, 0.18);
  border-radius: 50%;
}
.login-card__title {
  text-align: center;
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.1em;
  margin-bottom: 24px;
}

/* 验证码行：输入框 + 发送按钮 */
.login-card__code-row {
  display: flex;
  gap: 8px;
  width: 100%;
}
.login-card__code-input {
  flex: 1;
}
.login-card__code-btn {
  flex-shrink: 0;
  min-width: 108px;
  font-size: 13px;
  letter-spacing: 0.02em;
  --el-button-text-color: var(--color-primary);
  --el-button-bg-color: transparent;
  --el-button-border-color: var(--color-primary);
  --el-button-hover-text-color: #fff;
  --el-button-hover-bg-color: var(--color-primary);
  --el-button-hover-border-color: var(--color-primary);
  --el-button-disabled-text-color: var(--color-text-placeholder);
  --el-button-disabled-border-color: var(--color-border);
}

/* 提交按钮：朱砂主色，克制圆角 */
.login-card__submit {
  margin-top: 4px;
  border-radius: 8px;
  letter-spacing: 0.08em;
}
.login-card__switch {
  text-align: center;
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-top: 18px;
}
.login-card__switch-link {
  cursor: pointer;
  transition: color 0.2s;
}
.login-card__switch-link:hover {
  color: var(--color-primary);
}
</style>
