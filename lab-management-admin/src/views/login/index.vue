<template>
  <div class="login-wrapper">
    <!-- 左侧：全屏动态弥散渐变背景 + 品牌区 -->
    <div class="login-brand">
      <div class="brand-header">
        <div class="logo-wrapper">
          <svg viewBox="0 0 24 24" fill="none" class="brand-logo">
            <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
          </svg>
        </div>
        <span class="system-name">AI Lab Admin</span>
      </div>

      <div class="brand-content">
        <div class="brand-text">
          <h1>智能联接，<br>重新定义实验室管理</h1>
          <p>
            专为现代高校与研发中心打造的 AI 实验室基座。<br>
            集设备物联、数据大盘、审批流转与多维权限于一体。
          </p>
        </div>

        <div class="feature-list">
          <div class="feature-item">
            <div class="feature-icon">
              <!-- 精细化设备 -->
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="3" y="3" width="7" height="7"></rect>
                <rect x="14" y="3" width="7" height="7"></rect>
                <rect x="14" y="14" width="7" height="7"></rect>
                <rect x="3" y="14" width="7" height="7"></rect>
              </svg>
            </div>
            <div class="feature-info">
              <strong>精细化设备管控</strong>
              <span>实时监测与自动化调度，提升资产利用率</span>
            </div>
          </div>
          <div class="feature-item">
            <div class="feature-icon">
              <!-- 多角色 -->
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                <circle cx="9" cy="7" r="4"></circle>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
              </svg>
            </div>
            <div class="feature-info">
              <strong>多角色权限融合</strong>
              <span>管理员与教师灵活协同，安全隔离实验数据</span>
            </div>
          </div>
          <div class="feature-item">
            <div class="feature-icon">
              <!-- 数据流 -->
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
              </svg>
            </div>
            <div class="feature-info">
              <strong>全链路数据追溯</strong>
              <span>操作日志与审批自动留痕，过程全面可控</span>
            </div>
          </div>
        </div>
      </div>

      <div class="brand-footer">
        <p>AI实验室管理系统 v1.0.0. 毕业设计展示版</p>
        <p>&copy; {{ new Date().getFullYear() }} All rights reserved.</p>
      </div>
    </div>

    <!-- 右侧：悬浮的白色超大圆角登录卡片 -->
    <div class="login-form-wrapper">
      <div class="login-form-container">
        <div class="form-header">
          <h2>系统登录</h2>
          <p>欢迎回来，请输入您的管理员或教师账号</p>
        </div>

        <el-form :model="form" class="login-form" label-position="top" @submit.prevent="handleSubmit">
          <el-form-item label="账号">
            <el-input 
              v-model="form.username" 
              placeholder="请输入账号" 
              size="large"
            >
              <template #prefix>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                </svg>
              </template>
            </el-input>
          </el-form-item>
          
          <el-form-item label="密码">
            <el-input 
              v-model="form.password" 
              type="password" 
              show-password 
              placeholder="请输入密码" 
              size="large"
            >
              <template #prefix>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>
              </template>
            </el-input>
          </el-form-item>

          <el-button 
            type="primary" 
            class="submit-btn" 
            :loading="authStore.loading" 
            size="large" 
            @click="handleSubmit"
          >
            立 即 登 录
          </el-button>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
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
/* ================== 微动效帧定义 ================== */
@keyframes fadeUpIn {
  0% { opacity: 0; transform: translateY(24px); }
  100% { opacity: 1; transform: translateY(0); }
}
@keyframes slideInLeft {
  0% { opacity: 0; transform: translateX(-30px); }
  100% { opacity: 1; transform: translateX(0); }
}
@keyframes blurIn {
  0% { opacity: 0; filter: blur(8px); transform: translateY(10px); }
  100% { opacity: 1; filter: blur(0); transform: translateY(0); }
}
@keyframes meshGradient {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.login-wrapper {
  display: flex;
  min-height: 100vh;
  width: 100%;
  
  /* 动态弥散渐变背景 Mesh Gradient - 深蓝、深灰、深紫交织 */
  background: 
    radial-gradient(circle at 15% 50%, rgba(30, 27, 75, 1), transparent 50%),
    radial-gradient(circle at 85% 30%, rgba(30, 58, 138, 1), transparent 50%),
    radial-gradient(circle at 50% 80%, rgba(76, 29, 149, 1), transparent 50%),
    #0f172a;
  background-size: 200% 200%;
  animation: meshGradient 20s ease-in-out infinite;
  
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  color: #ffffff;
  position: relative;
  overflow: hidden;
}

/* ================== 左侧品牌与功能区 ================== */
.login-brand {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 48px 64px 28px;
  /* 移除原有的生硬切分背景色，完全通透融入底部的渐变背景 */
  background-color: transparent;
  color: #ffffff;
}

.brand-header {
  position: absolute;
  top: 48px;
  left: 64px;
  z-index: 2;
  display: flex;
  animation: fadeUpIn 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0s both;
  align-items: center;
  gap: 12px;

  .logo-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: #ffffff;
    color: #0c111d; 
    box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.1);
    
    .brand-logo {
      width: 20px;
      height: 20px;
    }
  }

  .system-name {
    font-size: 16px;
    font-weight: 600;
    letter-spacing: 0.5px;
    color: #fafafa;
  }
}

.brand-content {
  flex: 1;
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  justify-content: center; 
  margin-top: 24px;
}

.brand-text {
  margin-bottom: 48px;
  
  h1 {
    font-size: 44px;
    font-weight: 700;
    line-height: 1.25;
    margin: 0 0 20px;
    letter-spacing: -0.02em;
    background: linear-gradient(180deg, #ffffff 0%, #a1a1aa 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: fadeUpIn 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.1s both;
  }
  
  p {
    font-size: 16px;
    line-height: 1.6;
    color: #cbd5e1; /* 弱化灰白色 */
    margin: 0;
    font-weight: 400;
    animation: fadeUpIn 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.2s both;
  }
}

.feature-list {
  display: flex;
  flex-direction: column;
  gap: 24px; /* 增加行间距，提升呼吸感 */
  max-width: 480px;

  .feature-item {
    display: flex;
    align-items: center;
    gap: 20px; /* 增加图文间距 */
    padding: 24px; /* 增加内间距 */
    border-radius: 16px;
    
    /* 极致磨砂玻璃卡片效果替代原本的生硬底色块 */
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.1); /* 1px半透明描边 */
    backdrop-filter: blur(16px);
    
    /* 进场动画与错开帧延迟 */
    animation: slideInLeft 0.8s cubic-bezier(0.16, 1, 0.3, 1) both;
    &:nth-child(1) { animation-delay: 0.3s; }
    &:nth-child(2) { animation-delay: 0.4s; }
    &:nth-child(3) { animation-delay: 0.5s; }

    &:hover {
      background: rgba(255, 255, 255, 0.04);
      transform: translateY(-2px);
      border-color: rgba(255, 255, 255, 0.25);
    }

    .feature-icon {
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 48px;
      height: 48px;
      color: #e4e4e7;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 12px;
    }

    .feature-info {
      display: flex;
      flex-direction: column;
      gap: 8px; /* 加大行间距 */

      strong {
        font-size: 16px;
        color: #f4f4f5;
        font-weight: 500;
        letter-spacing: 0.5px;
      }
      span {
        font-size: 14px;
        color: rgba(255, 255, 255, 0.6); 
        line-height: 1.6;
      }
    }
  }
}

.brand-footer {
  margin-top: auto;
  position: relative;
  z-index: 1;
  /* 整体变细，变淡，整体下移 */
  margin-bottom: -16px;
  p {
    margin: 4px 0;
    font-size: 12px;
    font-weight: 300; /* 更细 */
    color: rgba(255, 255, 255, 0.25); /* 更淡 */
  }
}

/* ================== 右侧悬浮孤岛卡片表单区 ================== */
.login-form-wrapper {
  width: 440px; 
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  
  /* 悬浮的白色卡片属性 */
  background-color: #ffffff;
  border-radius: 24px; /* 巨大圆角 */
  margin: 32px 48px 32px 0; /* 与边缘脱离，形成浮动 */
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.15), 0 4px 12px rgba(0, 0, 0, 0.05); /* 轻微但宽广的浮动阴影 */
  
  padding: 48px;
  z-index: 10;
  
  /* 浮层淡入特效 */
  animation: blurIn 1.2s cubic-bezier(0.16, 1, 0.3, 1) 0.2s both;
}

.login-form-container {
  width: 100%;
  max-width: 320px;
}

.form-header {
  margin-bottom: 40px;
  text-align: left;

  h2 {
    margin: 0 0 8px;
    font-size: 26px;
    font-weight: 700;
    color: #09090b;
    letter-spacing: -0.02em;
  }
  p {
    margin: 0;
    font-size: 14px;
    color: #71717a;
  }
}

.login-form {
  :deep(.el-form-item) {
    margin-bottom: 24px;
  }
  /* 表单文字精细度打磨 */
  :deep(.el-form-item__label) {
    font-weight: 500;
    color: #18181b;
    padding-bottom: 8px;
    font-size: 14px;
    line-height: 1;
  }
  
  :deep(.el-input__wrapper) {
    /* 颜色变浅、变细的细腻边界 */
    box-shadow: 0 0 0 1px #f1f5f9 inset !important; 
    padding: 0 16px;
    border-radius: 12px;
    background-color: #fafafa;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    height: 46px; 

    &:hover {
      box-shadow: 0 0 0 1px #e2e8f0 inset !important;
    }
    
    &.is-focus {
      /* 点击(Focus)时散发蓝色精细发光过渡 */
      box-shadow: 0 0 0 1px #3b82f6 inset, 0 0 12px rgba(59, 130, 246, 0.25) !important;
      background-color: #ffffff;
    }
  }

  :deep(.el-input__inner) {
    color: #0f172a;
    font-size: 14px;
    &::placeholder {
      color: #94a3b8;
    }
  }

  :deep(.el-input__prefix),
  :deep(.el-input__suffix) {
    color: #94a3b8;
    margin-right: 8px;
  }
}

/* 按钮的史诗级打磨：流光渐变与强互动微动效 */
.submit-btn {
  width: 100%;
  margin-top: 16px;
  font-weight: 600;
  border-radius: 12px;
  height: 48px;
  font-size: 16px;
  
  /* 透明发光淡蓝到深蓝渐变色 */
  background: linear-gradient(135deg, #60a5fa 0%, #1d4ed8 100%) !important;
  border: none !important;
  color: #ffffff !important;
  box-shadow: 0 4px 12px rgba(29, 78, 216, 0.15);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  &:hover {
    /* hover:scale(1.05) 微缩放交互核心 */
    transform: scale(1.05);
    box-shadow: 0 12px 24px rgba(29, 78, 216, 0.3);
  }
  
  &:active {
    transform: scale(0.98);
    box-shadow: 0 2px 6px rgba(29, 78, 216, 0.2);
  }
  
  &.is-loading {
    opacity: 0.8;
    pointer-events: none;
    transform: none;
  }
}

/* 响应式调整 */
@media (max-width: 1000px) {
  .login-wrapper {
    flex-direction: column;
  }
  .login-brand {
    padding: 32px;
    flex: none;
  }
  .login-form-wrapper {
    width: auto;
    margin: 20px;
    border-radius: 20px;
  }
}
</style>
