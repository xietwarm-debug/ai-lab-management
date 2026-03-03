<template>
  <view class="container settingsPage" :class="themeClass">
    <view class="stack">
      <view class="card heroCard">
        <view class="title">账号设置</view>
        <view class="subtitle">账号安全与主题外观</view>
        <view class="muted accountText">当前账号：{{ username || "-" }}</view>
      </view>

      <view class="card">
        <view class="cardTitle">外观主题</view>
        <view class="themeRow">
          <view class="themeMeta">
            <view class="themeName">{{ isDark ? "暗色模式" : "浅色模式" }}</view>
            <view class="muted themeHint">切换后即时生效，并保存到本地</view>
          </view>
          <switch :checked="isDark" @change="onThemeSwitch" />
        </view>
      </view>

      <view class="card">
        <view class="cardTitle">安全操作</view>
        <view class="btnStack">
          <button class="btnSecondary" @click="changePassword">修改密码</button>
          <button class="btnDanger" @click="clearAllRecords">一键清空所有记录</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"
import { themePageMixin } from "@/common/theme.js"

const THEME_KEY = "theme"

function normalizeTheme(theme) {
  return theme === "dark" ? "dark" : "light"
}

export default {
  mixins: [themePageMixin],
  data() {
    return {
      username: "",
      role: "",
      theme: "light"
    }
  },
  computed: {
    isDark() {
      return this.theme === "dark"
    }
  },
  onLoad() {
    uni.$on("theme:change", this.handleThemeChanged)
  },
  onUnload() {
    uni.$off("theme:change", this.handleThemeChanged)
  },
  onShow() {
    const s = uni.getStorageSync("session") || {}
    if (!s.username || !s.token) {
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    this.username = s.username || ""
    this.role = s.role || ""
    this.theme = this.readTheme()
  },
  methods: {
    readTheme() {
      const app = typeof getApp === "function" ? getApp() : null
      if (app && typeof app.getTheme === "function") {
        return normalizeTheme(app.getTheme())
      }
      return normalizeTheme(uni.getStorageSync(THEME_KEY))
    },
    applyTheme(nextTheme, silent = false) {
      const normalized = normalizeTheme(nextTheme)
      const app = typeof getApp === "function" ? getApp() : null
      if (app && typeof app.setTheme === "function") {
        app.setTheme(normalized)
      } else {
        uni.setStorageSync(THEME_KEY, normalized)
        uni.$emit("theme:change", { theme: normalized })
      }
      this.theme = normalized
      if (!silent) {
        uni.showToast({
          title: normalized === "dark" ? "已切换暗色模式" : "已切换浅色模式",
          icon: "none"
        })
      }
    },
    handleThemeChanged(payload) {
      const nextTheme = payload && payload.theme
      this.theme = normalizeTheme(nextTheme)
    },
    onThemeSwitch(e) {
      const checked = !!(e && e.detail && e.detail.value)
      this.applyTheme(checked ? "dark" : "light")
    },
    changePassword() {
      uni.showModal({
        title: "输入旧密码",
        editable: true,
        placeholderText: "旧密码",
        success: (m1) => {
          if (!m1.confirm) return
          const oldPassword = (m1.content || "").trim()
          if (!oldPassword) {
            uni.showToast({ title: "请输入旧密码", icon: "none" })
            return
          }

          uni.showModal({
            title: "输入新密码",
            editable: true,
            placeholderText: "至少 6 位",
            success: (m2) => {
              if (!m2.confirm) return
              const newPassword = (m2.content || "").trim()
              if (newPassword.length < 6) {
                uni.showToast({ title: "新密码至少 6 位", icon: "none" })
                return
              }

              uni.request({
                url: `${BASE_URL}/auth/change-password`,
                method: "POST",
                header: { "Content-Type": "application/json" },
                data: { oldPassword, newPassword },
                success: (res) => {
                  if (!res.data || !res.data.ok) {
                    uni.showToast({ title: (res.data && res.data.msg) || "修改失败", icon: "none" })
                    return
                  }
                  uni.showModal({
                    title: "修改成功",
                    content: "请重新登录",
                    showCancel: false,
                    success: () => {
                      uni.removeStorageSync("session")
                      uni.reLaunch({ url: "/pages/login/login" })
                    }
                  })
                },
                fail: () => {
                  uni.showToast({ title: "请求失败", icon: "none" })
                }
              })
            }
          })
        }
      })
    },
    clearAllRecords() {
      const isAdmin = this.role === "admin"
      const scope = isAdmin ? "all" : "mine"
      const title = isAdmin ? "确认清空全站记录" : "确认清空我的记录"
      const content = isAdmin
        ? "将清空所有用户的预约与失物招领记录，此操作不可恢复。是否继续？"
        : "将清空你当前账号下的预约与失物招领记录，此操作不可恢复。是否继续？"

      uni.showModal({
        title,
        content,
        confirmColor: "#ef4444",
        success: (m) => {
          if (!m.confirm) return
          uni.request({
            url: `${BASE_URL}/auth/clear-records`,
            method: "POST",
            header: { "Content-Type": "application/json" },
            data: { scope },
            success: (res) => {
              if (!res.data || !res.data.ok) {
                uni.showToast({ title: (res.data && res.data.msg) || "清空失败", icon: "none" })
                return
              }
              const data = res.data.data || {}
              const msg = `已清空：预约 ${Number(data.reservationDeleted || 0)} 条，失物 ${Number(data.lostfoundDeleted || 0)} 条`
              uni.showModal({
                title: "清空完成",
                content: msg,
                showCancel: false
              })

              const reservationReadKey = `notifications_last_read_reservation_${this.username || ""}`
              const lostfoundReadKey = `notifications_last_read_lostfound_${this.username || ""}`
              try {
                uni.removeStorageSync(reservationReadKey)
                uni.removeStorageSync(lostfoundReadKey)
              } catch (e) {}
            },
            fail: () => {
              uni.showToast({ title: "请求失败", icon: "none" })
            }
          })
        }
      })
    }
  }
}
</script>

<style lang="scss">
.settingsPage {
  padding-bottom: var(--space-5);
}

.heroCard {
  border: 1px solid var(--color-border-focus);
  background: var(--color-bg-soft);
}

.accountText {
  margin-top: var(--space-2);
}

.themeRow {
  margin-top: var(--space-2);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.themeMeta {
  flex: 1;
  min-width: 0;
}

.themeName {
  font-size: var(--font-size-md);
  line-height: 1.3;
  font-weight: 600;
  color: var(--color-text-primary);
}

.themeHint {
  margin-top: 2px;
}

.btnStack {
  margin-top: var(--space-2);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
</style>
