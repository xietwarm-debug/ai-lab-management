<template>
  <view class="container loginPage">
    <!-- 明亮弥散渐变极底色层 -->
    <view class="mesh-bg"></view>

    <!-- 真机滚动流主体 -->
    <view class="content-wrapper">
      <view class="welcome-section">
        <view class="badge">
          <view class="badge-dot"></view>
          <text>AILab Secure</text>
        </view>
        
        <view class="title-wrap">
          <text class="title-main">遇见,</text>
          <text class="title-sub">实验室管理新范式</text>
        </view>
        <text class="desc">学生、教师与管理员的统一控制中枢</text>
      </view>

      <!-- 亮色玻璃拟态半透明底部遮罩 -->
      <view class="form-section">
        <view class="tab-header">
          <text 
            class="tab-item" 
            :class="{ active: mode === 'login' }" 
            @click="setMode('login')"
          >密码登录</text>
          <text 
            class="tab-item" 
            :class="{ active: mode === 'register' }" 
            @click="setMode('register')"
          >新手指引 / 注册</text>
        </view>

        <view class="form-body">
          <view class="input-group">
            <text class="label">账号</text>
            <view class="input-wrapper" :class="{ 'is-error': errors.username }">
              <input
                class="input-box"
                placeholder-class="input-placeholder"
                v-model="username"
                placeholder="请输入账号名称"
                maxlength="32"
                @input="onFieldInput('username')"
              />
            </view>
            <text class="error-msg" v-if="errors.username">{{ errors.username }}</text>
          </view>

          <view class="input-group">
            <text class="label">密码</text>
            <view class="input-wrapper" :class="{ 'is-error': errors.password }">
              <input
                class="input-box"
                placeholder-class="input-placeholder"
                v-model="password"
                type="password"
                placeholder="请输入登录密码"
                maxlength="64"
                @input="onFieldInput('password')"
              />
            </view>
            <text class="error-msg" v-if="errors.password">{{ errors.password }}</text>
          </view>

          <view class="meta-tips">
            <text v-if="mode === 'login'">⚠️ 初始旧账号默认密码为用户名</text>
            <text v-else>🔒 密码请设置至少 6 位安全字符</text>
          </view>

          <button class="submit-btn" :disabled="submitting" @click="submitMain">
            {{ submitting ? '验证中...' : (mode === 'login' ? '立即进入' : '创建账号') }}
          </button>
        </view>

        <view class="footer-copyright">
          <text>© {{ new Date().getFullYear() }} AI实验室 毕设呈现端</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"
import { redirectByRole } from "@/common/session.js"

function resolveDeviceName() {
  try {
    const info = uni.getSystemInfoSync() || {}
    const platform = String(info.platform || info.system || "").trim()
    const model = String(info.model || info.deviceBrand || "").trim()
    const text = `${platform} ${model}`.trim()
    return text.slice(0, 80)
  } catch (e) {
    return ""
  }
}

export default {
  data() {
    return {
      username: "",
      password: "",
      mode: "login",
      submitting: false,
      errors: {
        username: "",
        password: ""
      }
    }
  },
  onShow() {
    const s = uni.getStorageSync("session")
    if (s && s.username && s.token) {
      this.jumpByRole(s.role)
    }
  },
  methods: {
    setMode(mode) {
      if (this.submitting) return
      this.mode = mode
      this.errors.username = ""
      this.errors.password = ""
    },
    onFieldInput(field) {
      this.errors[field] = ""
    },
    validate() {
      const username = this.username.trim()
      const password = this.password
      this.errors.username = ""
      this.errors.password = ""
      let ok = true

      if (!username) {
        this.errors.username = "请输入账号"
        ok = false
      }
      if (!password) {
        this.errors.password = "请输入密码"
        ok = false
      } else if (this.mode === "register" && password.length < 6) {
        this.errors.password = "密码至少 6 位"
        ok = false
      }
      return ok
    },
    submitMain() {
      if (this.mode === "login") {
        this.doLogin()
      } else {
        this.doRegister()
      }
    },
    doLogin() {
      const name = this.username.trim()
      const pwd = this.password
      const deviceName = resolveDeviceName()
      if (!this.validate()) return
      if (this.submitting) return

      this.submitting = true
      uni.request({
        url: `${BASE_URL}/login`,
        method: "POST",
        header: { "Content-Type": "application/json", "X-Skip-Auth": "1" },
        data: { username: name, password: pwd, deviceName },
        success: (res) => {
          if (!res.data || !res.data.ok) {
            uni.showToast({ title: (res.data && res.data.msg) || "登录失败", icon: "none" })
            return
          }

          const session = res.data.data
          uni.setStorageSync("session", session)
          this.jumpByRole(session.role)
        },
        fail: () => {
          uni.showToast({ title: "无法连接后端", icon: "none" })
        },
        complete: () => {
          this.submitting = false
        }
      })
    },
    doRegister() {
      const name = this.username.trim()
      const pwd = this.password
      const deviceName = resolveDeviceName()
      if (!this.validate()) return
      if (this.submitting) return

      this.submitting = true
      uni.request({
        url: `${BASE_URL}/register`,
        method: "POST",
        header: { "Content-Type": "application/json", "X-Skip-Auth": "1" },
        data: { username: name, password: pwd, deviceName },
        success: (res) => {
          if (!res.data || !res.data.ok) {
            uni.showToast({ title: (res.data && res.data.msg) || "注册失败", icon: "none" })
            return
          }

          const session = res.data.data
          uni.setStorageSync("session", session)
          uni.showToast({ title: "注册成功", icon: "success" })
          this.jumpByRole(session.role)
        },
        fail: () => {
          uni.showToast({ title: "无法连接后端", icon: "none" })
        },
        complete: () => {
          this.submitting = false
        }
      })
    },
    jumpByRole(role) {
      redirectByRole(role, { replace: true })
    }
  }
}
</script>

<style lang="scss">
@keyframes fadeDown {
  0% { opacity: 0; transform: translateY(-20px); }
  100% { opacity: 1; transform: translateY(0); }
}
@keyframes slideUp {
  0% { opacity: 0; transform: translateY(40px); }
  100% { opacity: 1; transform: translateY(0); }
}
@keyframes meshLight {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}

page {
  background-color: #f8fafc;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #0f172a;
}

.loginPage {
  min-height: 100vh;
  position: relative;
  overflow: hidden;
  background-color: #f8fafc;
}

/* ================= 高定亮色 SaaS 弥散渐变背景 ================= */
.mesh-bg {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 0;
  /* 清透高亮的蓝紫渐变，代替原本死气沉沉的单色块 */
  background: 
    radial-gradient(circle at 15% 20%, rgba(224, 231, 255, 0.9), transparent 50%), /* 轻盈紫罗兰 */
    radial-gradient(circle at 85% 60%, rgba(219, 234, 254, 0.9), transparent 50%), /* 晨曦蓝 */
    radial-gradient(circle at 50% 90%, rgba(243, 232, 255, 0.9), transparent 50%), /* 温柔浅紫 */
    #f8fafc; /* 超级干净的 Slate-50 底板 */
  background-size: 200% 200%;
  animation: meshLight 20s ease-in-out infinite;
}

.content-wrapper {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* ================= 头部结构：通透欢迎区 ================= */
.welcome-section {
  padding: 40px 32px 30px;
  display: flex;
  flex-direction: column;
  animation: fadeDown 0.8s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.badge {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.9);
  color: #2563eb; /* Blue-600 */
  padding: 6px 14px;
  border-radius: 999px;
  width: fit-content;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 24px;
  backdrop-filter: blur(8px);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.05); /* 淡淡的弥散光 */
}

.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #3b82f6; 
  box-shadow: 0 0 8px rgba(59, 130, 246, 0.4);
}

.title-wrap {
  display: flex;
  flex-direction: column;
  margin-bottom: 12px;
}

.title-main {
  font-size: 40px;
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -0.02em;
  color: #0f172a; /* Slate 900 亮色极深灰 */
}

.title-sub {
  font-size: 28px;
  font-weight: 700;
  color: #334155; /* Slate 700 */
  margin-top: 4px;
}

.desc {
  font-size: 15px;
  color: #64748b; /* Slate 500 */
  line-height: 1.6;
}

/* ================= 底部表单浮层：白玉玻璃态 (Light Glassmorphism) ================= */
.form-section {
  flex: 1;
  background: rgba(255, 255, 255, 0.65); /* 明亮透彻 */
  border-radius: 36px 36px 0 0;
  padding: 40px 32px 50px;
  border-top: 1px solid #ffffff; /* 亮色反光顶缘 */
  box-shadow: 0 -12px 40px rgba(0, 0, 0, 0.04);
  backdrop-filter: blur(24px); 
  display: flex;
  flex-direction: column;
  position: relative;
  /* 上划入场动画 */
  animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.1s both;
}

/* 典雅的 Tab 切换 */
.tab-header {
  display: flex;
  gap: 24px;
  margin-bottom: 36px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05); /* 极弱分隔线 */
  padding-bottom: 12px;
}

.tab-item {
  font-size: 16px;
  font-weight: 500;
  color: #94a3b8; /* Slate-400 */
  position: relative;
  padding-bottom: 12px;
  margin-bottom: -13px; 
  transition: color 0.3s;
}

.tab-item.active {
  color: #0f172a; /* 极简黑字 */
  font-weight: 600;
}

.tab-item.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 20%;
  width: 60%;
  height: 3px;
  background: #3b82f6; 
  border-radius: 3px;
  box-shadow: 0 0 6px rgba(59, 130, 246, 0.3);
}

/* ================== 输入框控件细节 (极简灰底) ================== */
.input-group {
  margin-bottom: 24px;
  display: flex;
  flex-direction: column;
}

.label {
  font-size: 14px;
  font-weight: 600;
  color: #334155; 
  margin-bottom: 10px;
  padding-left: 4px;
}

.input-wrapper {
  background: #ffffff; /* 纯洁净白 */
  border: 1px solid #e2e8f0; /* 极致淡灰色 */
  border-radius: 16px;
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  transition: all 0.25s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.01);
}

.input-wrapper:focus-within {
  background: #ffffff;
  border-color: #3b82f6; /* Blue-500 亮色细微描边 */
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
}

.input-wrapper.is-error {
  border-color: #ef4444; 
  box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.1);
}

.input-box {
  flex: 1;
  font-size: 16px;
  color: #0f172a;
  font-weight: 500;
}

.input-placeholder {
  color: #94a3b8; 
  font-weight: 400;
}

.error-msg {
  color: #ef4444; 
  font-size: 12px;
  margin-top: 8px;
  padding-left: 4px;
  animation: shake 0.3s;
}

.meta-tips {
  margin-top: -4px;
  margin-bottom: 32px;
  padding-left: 4px;
  font-size: 13px;
  color: #64748b;
}

/* ================== 王牌级别主操作按钮 (悬浮微缩发光) ================== */
.submit-btn {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: #ffffff;
  font-size: 17px;
  font-weight: 600;
  height: 56px;
  line-height: 56px;
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.25);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.submit-btn:active {
  transform: scale(0.96); 
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15);
}

.submit-btn[disabled] {
  background: #f1f5f9;
  color: #94a3b8; 
  box-shadow: none;
}

/* ================== 版权底纹 ================== */
.footer-copyright {
  margin-top: auto;
  text-align: center;
  padding-top: 40px;
  font-size: 12px;
  font-weight: 400;
  color: #cbd5e1; 
}
</style>
