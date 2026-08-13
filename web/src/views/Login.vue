<script setup lang="ts">
// 登录 / 注册页：切换模式并提交表单
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

// 当前模式：登录 / 注册
const mode = ref<'login' | 'register'>('login')
const loading = ref(false)
const formRef = ref<FormInstance>()

const form = reactive({
  nickname: '',
  email: '',
  password: '',
})

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
      await userStore.register(form.nickname, form.email, form.password)
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
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
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
