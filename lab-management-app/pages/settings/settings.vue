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

      <view class="card" v-if="isStudent">
        <view class="cardTitle">作业提醒订阅</view>
        <view class="themeRow">
          <view class="themeMeta">
            <view class="themeName">{{ reminderForm.enabled ? "已开启提醒" : "已关闭提醒" }}</view>
            <view class="muted themeHint">开启后，系统会在截止前与逾期时发送作业提醒</view>
          </view>
          <switch :checked="reminderForm.enabled" @change="onReminderEnabledSwitch" />
        </view>

        <view class="label">截止前提醒时间</view>
        <picker :range="beforeHoursOptions" range-key="label" :value="beforeHoursIndex" @change="onBeforeHoursChange">
          <view class="pickerValue">{{ beforeHoursText }}</view>
        </picker>

        <view class="themeRow">
          <view class="themeMeta">
            <view class="themeName">逾期后继续提醒</view>
            <view class="muted themeHint">任务截止后仍未提交时继续推送提醒</view>
          </view>
          <switch :checked="reminderForm.remindOverdue" @change="onReminderOverdueSwitch" />
        </view>

        <view class="btnStack">
          <button class="btnPrimary" :loading="reminderSaving" @click="saveReminder">保存提醒设置</button>
        </view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">账号与安全</view>
          <button class="btnSecondary miniBtn" size="mini" :disabled="securityLoading || deviceLoading" @click="refreshSecurity">
            {{ securityLoading || deviceLoading ? "刷新中..." : "刷新" }}
          </button>
        </view>

        <view class="securityList">
          <view class="securityItem">
            <view class="themeMeta">
              <view class="themeName">手机号</view>
              <view class="muted themeHint">{{ phoneBound ? (phoneMasked || phoneValue) : "未绑定" }}</view>
            </view>
            <button class="btnSecondary miniBtn" size="mini" @click="bindPhone">
              {{ phoneBound ? "修改手机号" : "绑定手机号" }}
            </button>
          </view>

          <view class="securityItem">
            <view class="themeMeta">
              <view class="themeName">邮箱</view>
              <view class="muted themeHint">{{ emailBound ? (emailMasked || emailValue) : "未绑定" }}</view>
            </view>
            <button class="btnSecondary miniBtn" size="mini" @click="bindEmail">
              {{ emailBound ? "修改邮箱" : "绑定邮箱" }}
            </button>
          </view>
        </view>

        <view class="label">登录设备管理</view>
        <view class="loadingText muted" v-if="deviceLoading">设备信息加载中...</view>
        <view class="emptyState compactEmpty" v-else-if="devices.length === 0">
          <view class="emptyIcon">端</view>
          <view class="emptyTitle">暂无在线设备</view>
          <view class="emptySub">登录后会自动记录设备信息</view>
        </view>
        <view class="deviceList" v-else>
          <view class="deviceItem" v-for="item in devices" :key="item.id">
            <view class="rowBetween">
              <view class="deviceName">{{ item.deviceName || "未知设备" }}</view>
              <view class="chip" v-if="item.isCurrent">当前设备</view>
            </view>
            <view class="muted deviceMeta">最近活动：{{ item.lastSeenAt || "-" }} · IP：{{ item.loginIp || "-" }}</view>
            <view class="muted deviceMeta">登录时间：{{ item.createdAt || "-" }}</view>
            <view class="deviceActionRow">
              <button
                class="btnSecondary miniBtn"
                size="mini"
                :disabled="item.isCurrent || revokingDeviceId === item.id"
                @click="revokeDevice(item)"
              >{{ revokingDeviceId === item.id ? "处理中..." : "下线此设备" }}</button>
            </view>
          </view>
        </view>

        <button class="btnSecondary fullBtn" :disabled="revokeOthersLoading || devices.length <= 1" @click="revokeOtherDevices">
          {{ revokeOthersLoading ? "处理中..." : "下线其他设备" }}
        </button>
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
import {
  BASE_URL,
  changePassword,
  getAuthSecurity,
  bindSecurityPhone,
  bindSecurityEmail,
  listLoginDevices,
  revokeLoginDevice,
  revokeOtherLoginDevices,
  getCourseTaskReminderSubscription,
  saveCourseTaskReminderSubscription
} from "@/common/api.js"
import { themePageMixin } from "@/common/theme.js"

const THEME_KEY = "theme"

function normalizeTheme(theme) {
  return theme === "dark" ? "dark" : "light"
}

function profileStorageKey(account) {
  return `user_profile_${account}`
}

function isValidEmail(text) {
  return /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(String(text || "").trim())
}

export default {
  mixins: [themePageMixin],
  data() {
    return {
      username: "",
      role: "",
      theme: "light",
      reminderSaving: false,
      securityLoading: false,
      deviceLoading: false,
      revokingDeviceId: 0,
      revokeOthersLoading: false,
      phoneValue: "",
      phoneMasked: "",
      emailValue: "",
      emailMasked: "",
      devices: [],
      beforeHoursOptions: [
        { label: "截止前 6 小时", value: 6 },
        { label: "截止前 12 小时", value: 12 },
        { label: "截止前 24 小时", value: 24 },
        { label: "截止前 48 小时", value: 48 },
        { label: "截止前 72 小时", value: 72 }
      ],
      reminderForm: {
        enabled: true,
        beforeHours: 24,
        remindOverdue: true
      }
    }
  },
  computed: {
    isDark() {
      return this.theme === "dark"
    },
    isStudent() {
      return this.role === "student"
    },
    phoneBound() {
      return !!String(this.phoneValue || "").trim()
    },
    emailBound() {
      return !!String(this.emailValue || "").trim()
    },
    beforeHoursIndex() {
      const idx = this.beforeHoursOptions.findIndex((item) => Number(item.value) === Number(this.reminderForm.beforeHours))
      return idx >= 0 ? idx : 2
    },
    beforeHoursText() {
      const row = this.beforeHoursOptions[this.beforeHoursIndex] || this.beforeHoursOptions[2] || {}
      return row.label || "截止前 24 小时"
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
    if (this.isStudent) this.loadReminder()
    this.refreshSecurity()
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
    onReminderEnabledSwitch(e) {
      this.reminderForm.enabled = !!(e && e.detail && e.detail.value)
    },
    onReminderOverdueSwitch(e) {
      this.reminderForm.remindOverdue = !!(e && e.detail && e.detail.value)
    },
    onBeforeHoursChange(e) {
      const idx = Number(e && e.detail && e.detail.value)
      if (!Number.isFinite(idx) || idx < 0 || idx >= this.beforeHoursOptions.length) return
      this.reminderForm.beforeHours = Number((this.beforeHoursOptions[idx] || {}).value || 24)
    },
    async loadReminder() {
      try {
        const res = await getCourseTaskReminderSubscription()
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) return
        const data = payload.data || {}
        this.reminderForm.enabled = !!data.enabled
        this.reminderForm.beforeHours = Number(data.beforeHours || 24)
        this.reminderForm.remindOverdue = !!data.remindOverdue
      } catch (e) {}
    },
    async saveReminder() {
      if (this.reminderSaving) return
      this.reminderSaving = true
      try {
        const res = await saveCourseTaskReminderSubscription({
          enabled: !!this.reminderForm.enabled,
          beforeHours: Number(this.reminderForm.beforeHours || 24),
          remindOverdue: !!this.reminderForm.remindOverdue
        })
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "保存失败", icon: "none" })
          return
        }
        uni.showToast({ title: "提醒设置已保存", icon: "success" })
      } catch (e) {
        uni.showToast({ title: "保存失败，请重试", icon: "none" })
      } finally {
        this.reminderSaving = false
      }
    },
    getCurrentRefreshToken() {
      const s = uni.getStorageSync("session") || {}
      return String(s.refreshToken || "").trim()
    },
    syncProfilePhoneCache(phone) {
      const key = profileStorageKey(this.username)
      const oldProfile = uni.getStorageSync(key) || {}
      uni.setStorageSync(key, {
        ...oldProfile,
        phone: String(phone || "").trim()
      })
    },
    async refreshSecurity() {
      await this.loadSecurityOverview()
      await this.loadLoginDevices()
    },
    async loadSecurityOverview() {
      if (this.securityLoading) return
      this.securityLoading = true
      try {
        const res = await getAuthSecurity(this.getCurrentRefreshToken())
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          uni.showToast({ title: payload.msg || "安全信息加载失败", icon: "none" })
          return
        }
        const data = payload.data || {}
        this.phoneValue = String(data.phone || "").trim()
        this.phoneMasked = String(data.phoneMasked || "").trim()
        this.emailValue = String(data.email || "").trim()
        this.emailMasked = String(data.emailMasked || "").trim()
      } catch (e) {
        uni.showToast({ title: "安全信息加载失败", icon: "none" })
      } finally {
        this.securityLoading = false
      }
    },
    async loadLoginDevices() {
      if (this.deviceLoading) return
      this.deviceLoading = true
      try {
        const res = await listLoginDevices(this.getCurrentRefreshToken())
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "设备信息加载失败", icon: "none" })
          return
        }
        const data = payload.data || {}
        this.devices = Array.isArray(data.items) ? data.items : []
      } catch (e) {
        uni.showToast({ title: "设备信息加载失败", icon: "none" })
      } finally {
        this.deviceLoading = false
      }
    },
    bindPhone() {
      uni.showModal({
        title: this.phoneBound ? "修改手机号" : "绑定手机号",
        editable: true,
        placeholderText: "请输入手机号",
        success: async (m) => {
          if (!m.confirm) return
          const phone = String(m.content || "").trim()
          if (!phone) {
            uni.showToast({ title: "手机号不能为空", icon: "none" })
            return
          }
          try {
            const res = await bindSecurityPhone(phone)
            const payload = (res && res.data) || {}
            if (!payload.ok) {
              uni.showToast({ title: payload.msg || "绑定失败", icon: "none" })
              return
            }
            const data = payload.data || {}
            this.phoneValue = String(data.phone || phone).trim()
            this.phoneMasked = String(data.phoneMasked || "").trim()
            this.syncProfilePhoneCache(this.phoneValue)
            uni.showToast({ title: "手机号已更新", icon: "success" })
          } catch (e) {
            uni.showToast({ title: "绑定失败，请重试", icon: "none" })
          }
        }
      })
    },
    bindEmail() {
      uni.showModal({
        title: this.emailBound ? "修改邮箱" : "绑定邮箱",
        editable: true,
        placeholderText: "请输入邮箱",
        success: async (m) => {
          if (!m.confirm) return
          const email = String(m.content || "").trim()
          if (!email) {
            uni.showToast({ title: "邮箱不能为空", icon: "none" })
            return
          }
          if (!isValidEmail(email)) {
            uni.showToast({ title: "邮箱格式不正确", icon: "none" })
            return
          }
          try {
            const res = await bindSecurityEmail(email)
            const payload = (res && res.data) || {}
            if (!payload.ok) {
              uni.showToast({ title: payload.msg || "绑定失败", icon: "none" })
              return
            }
            const data = payload.data || {}
            this.emailValue = String(data.email || email).trim()
            this.emailMasked = String(data.emailMasked || "").trim()
            uni.showToast({ title: "邮箱已更新", icon: "success" })
          } catch (e) {
            uni.showToast({ title: "绑定失败，请重试", icon: "none" })
          }
        }
      })
    },
    revokeDevice(item) {
      const device = item || {}
      const id = Number(device.id || 0)
      if (!id) return
      if (device.isCurrent) {
        uni.showToast({ title: "当前设备不能在此下线", icon: "none" })
        return
      }
      uni.showModal({
        title: "下线设备",
        content: `确认下线设备“${device.deviceName || "未知设备"}”？`,
        confirmColor: "#ef4444",
        success: async (m) => {
          if (!m.confirm) return
          this.revokingDeviceId = id
          try {
            const res = await revokeLoginDevice(id, this.getCurrentRefreshToken())
            const payload = (res && res.data) || {}
            if (!payload.ok) {
              uni.showToast({ title: payload.msg || "操作失败", icon: "none" })
              return
            }
            uni.showToast({ title: "设备已下线", icon: "success" })
            await this.loadLoginDevices()
          } catch (e) {
            uni.showToast({ title: "操作失败，请重试", icon: "none" })
          } finally {
            this.revokingDeviceId = 0
          }
        }
      })
    },
    revokeOtherDevices() {
      if (this.revokeOthersLoading) return
      uni.showModal({
        title: "下线其他设备",
        content: "将退出当前账号在其他设备上的登录状态，是否继续？",
        confirmColor: "#ef4444",
        success: async (m) => {
          if (!m.confirm) return
          this.revokeOthersLoading = true
          try {
            const res = await revokeOtherLoginDevices(this.getCurrentRefreshToken())
            const payload = (res && res.data) || {}
            if (!payload.ok) {
              uni.showToast({ title: payload.msg || "操作失败", icon: "none" })
              return
            }
            const count = Number(((payload.data || {}).revokedCount) || 0)
            uni.showToast({ title: count > 0 ? `已下线 ${count} 台设备` : "无其他在线设备", icon: "none" })
            await this.loadLoginDevices()
          } catch (e) {
            uni.showToast({ title: "操作失败，请重试", icon: "none" })
          } finally {
            this.revokeOthersLoading = false
          }
        }
      })
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

              changePassword({ oldPassword, newPassword })
                .then((res) => {
                  const payload = (res && res.data) || {}
                  if (!payload.ok) {
                    uni.showToast({ title: payload.msg || "修改失败", icon: "none" })
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
                })
                .catch(() => {
                  uni.showToast({ title: "请求失败", icon: "none" })
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

.securityList {
  margin-top: var(--space-2);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.securityItem {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.pickerValue {
  margin-top: var(--space-2);
  min-height: 38px;
  border: 1px solid var(--color-border-primary);
  border-radius: 10px;
  background: var(--color-bg-card);
  padding: 8px 10px;
  color: var(--color-text-primary);
  display: flex;
  align-items: center;
}

.deviceList {
  margin-top: var(--space-2);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.deviceItem {
  border: 1px solid var(--color-border-primary);
  border-radius: 10px;
  background: var(--color-bg-card);
  padding: 10px;
}

.deviceName {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
}

.deviceMeta {
  margin-top: 4px;
}

.deviceActionRow {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
}

.fullBtn {
  margin-top: var(--space-2);
}
</style>
