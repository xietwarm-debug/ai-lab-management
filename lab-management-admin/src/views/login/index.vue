<template>
  <div class="login-page">
    <section class="login-panel">
      <div class="login-copy">
        <span class="eyebrow">Lab Admin</span>
        <h1>AI实验室管理助手后台</h1>
        <p>复用现有 Flask 接口，面向管理员与教师角色的电脑端管理后台。</p>
      </div>

      <el-form :model="form" label-position="top" @submit.prevent="handleSubmit">
        <el-form-item label="账号">
          <el-input v-model="form.username" placeholder="请输入账号" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
        <el-button type="primary" class="submit-btn" :loading="authStore.loading" @click="handleSubmit">
          登录后台
        </el-button>
      </el-form>
    </section>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const form = reactive({
  username: '',
  password: ''
})

async function handleSubmit() {
  if (!form.username.trim() || !form.password.trim()) {
    ElMessage.warning('请输入账号和密码')
    return
  }

  let user = null
  try {
    user = await authStore.login({
      username: form.username.trim(),
      password: form.password,
      deviceName: 'lab-management-admin'
    })
  } catch (error) {
    return
  }

  if (!['admin', 'teacher'].includes(user.role)) {
    await authStore.logout()
    ElMessage.error('当前账号没有后台访问权限')
    return
  }

  router.replace(String(route.query.redirect || '/dashboard'))
}
</script>

<style scoped lang="scss">
.login-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 24px;
}

.login-panel {
  width: min(460px, 100%);
  padding: 36px;
  border: 1px solid rgba(15, 118, 110, 0.12);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: var(--app-shadow);
}

.login-copy {
  margin-bottom: 24px;
}

.login-copy h1 {
  margin: 8px 0 10px;
  font-size: 30px;
  line-height: 1.2;
}

.login-copy p {
  margin: 0;
  color: var(--app-muted);
}

.eyebrow {
  display: inline-flex;
  padding: 6px 10px;
  border-radius: 999px;
  background: var(--app-primary-soft);
  color: #115e59;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.submit-btn {
  width: 100%;
  margin-top: 8px;
}
</style>
