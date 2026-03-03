<template>
  <view class="container loginPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="heroBadge">AIlab Secure</view>
        <view class="title">欢迎使用实验室管理系统</view>
        <view class="subtitle">使用账号密码登录，支持学生与管理员角色</view>

        <view class="heroMetaRow">
          <view class="heroMetaItem">安全认证：Token</view>
          <view class="heroMetaItem">会话续期：已启用</view>
        </view>
      </view>

      <view class="card formCard">
        <view class="rowBetween">
          <view class="cardTitle">账号登录</view>
          <view class="muted">{{ modeText }}</view>
        </view>

        <view class="modeRow">
          <view class="chip modeChip" :class="{ chipOn: mode === 'login' }" @click="setMode('login')">登录</view>
          <view class="chip modeChip" :class="{ chipOn: mode === 'register' }" @click="setMode('register')">注册</view>
        </view>

        <view class="label">账号</view>
        <input
          class="inputBase"
          v-model="username"
          placeholder="示例：user1 / admin1"
          maxlength="32"
          @input="onFieldInput('username')"
        />
        <view class="fieldError" v-if="errors.username">{{ errors.username }}</view>

        <view class="label">密码</view>
        <input
          class="inputBase"
          v-model="password"
          type="password"
          placeholder="请输入密码"
          maxlength="64"
          @input="onFieldInput('password')"
        />
        <view class="fieldError" v-if="errors.password">{{ errors.password }}</view>

        <view class="tips muted" v-if="mode === 'login'">旧账号默认密码为用户名</view>
        <view class="tips muted" v-else>新注册密码至少 6 位</view>

        <button class="btnPrimary submitBtn" :disabled="submitting" @click="submitMain">
          {{ submitting ? '处理中...' : (mode === 'login' ? '登录' : '注册') }}
        </button>

        <button class="btnSecondary switchBtn" :disabled="submitting" @click="switchMode">
          {{ mode === 'login' ? '没有账号？去注册' : '已有账号？去登录' }}
        </button>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"

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
  computed: {
    modeText() {
      return this.mode === "login" ? "请输入账号密码" : "创建新账号"
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
    switchMode() {
      this.setMode(this.mode === "login" ? "register" : "login")
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
      if (!this.validate()) return
      if (this.submitting) return

      this.submitting = true
      uni.request({
        url: `${BASE_URL}/login`,
        method: "POST",
        header: { "Content-Type": "application/json", "X-Skip-Auth": "1" },
        data: { username: name, password: pwd },
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
      if (!this.validate()) return
      if (this.submitting) return

      this.submitting = true
      uni.request({
        url: `${BASE_URL}/register`,
        method: "POST",
        header: { "Content-Type": "application/json", "X-Skip-Auth": "1" },
        data: { username: name, password: pwd },
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
      uni.reLaunch({ url: "/pages/index/index" })
    }
  }
}
</script>

<style lang="scss">
.loginPage {
  min-height: 100vh;
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.2);
  background: linear-gradient(155deg, #ffffff 0%, #edf5ff 62%, #e6f0ff 100%);
}

.heroBadge {
  width: fit-content;
  height: 22px;
  line-height: 22px;
  border-radius: 999px;
  padding: 0 10px;
  font-size: 11px;
  font-weight: 600;
  color: #1d4ed8;
  background: #eaf3ff;
  border: 1px solid #bfdbfe;
}

.heroMetaRow {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.heroMetaItem {
  height: 25px;
  line-height: 25px;
  border-radius: 999px;
  padding: 0 10px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(148, 163, 184, 0.24);
  color: #334155;
  font-size: 11px;
}

.formCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.modeRow {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}

.modeChip {
  transition: all 0.14s ease;
}

.chipOn {
  border-color: #bfdbfe;
  background: #eaf3ff;
  color: #1d4ed8;
}

.tips {
  margin-top: 8px;
}

.submitBtn {
  width: 100%;
  margin-top: 12px;
}

.switchBtn {
  width: 100%;
  margin-top: 8px;
}
</style>
