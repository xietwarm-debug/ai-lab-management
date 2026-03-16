<template>
  <view class="container profilePage" :class="themeClass">
    <view class="stack">
      <view class="card heroCard">
        <view class="title">个人资料</view>
        <view class="subtitle">更新头像、昵称、手机号与学号/工号</view>
      </view>

      <view class="card formCard">
        <view class="formItem avatarItem" @click="chooseAvatar">
          <view class="fieldLabel">头像</view>
          <view class="rightWrap">
            <view class="avatarWrap">
              <image v-if="avatar" class="avatarImage" :src="avatar" mode="aspectFill" />
              <view v-else class="avatarText">{{ avatarText }}</view>
            </view>
            <view class="itemArrow">&gt;</view>
          </view>
        </view>

        <view class="formItem">
          <view class="fieldLabel">昵称</view>
          <input class="inputValue" v-model.trim="nickname" maxlength="24" placeholder="请输入昵称" />
        </view>

        <view class="formItem">
          <view class="fieldLabel">手机号</view>
          <input class="inputValue" v-model.trim="phone" type="number" maxlength="20" placeholder="请输入手机号" />
        </view>

        <view class="formItem" v-if="isStudent">
          <view class="fieldLabel">学号</view>
          <input class="inputValue" v-model.trim="studentNo" maxlength="64" placeholder="请输入学号" />
        </view>

        <view class="formItem" v-if="isStudent">
          <view class="fieldLabel">班级</view>
          <input class="inputValue" v-model.trim="className" maxlength="64" placeholder="请输入班级" />
        </view>

        <view class="formItem" v-if="isTeacherOrAdmin">
          <view class="fieldLabel">工号</view>
          <input class="inputValue" v-model.trim="jobNo" maxlength="64" placeholder="请输入工号" />
        </view>

        <view class="formItem">
          <view class="fieldLabel">账号</view>
          <view class="readonlyValue">{{ account || "-" }}</view>
        </view>
      </view>

      <button class="btnPrimary saveBtn" :disabled="saving" @click="saveProfile">{{ saving ? "保存中..." : "保存" }}</button>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"
import { themePageMixin } from "@/common/theme.js"

function profileStorageKey(account) {
  return `user_profile_${account}`
}

function normalizeAvatar(url) {
  const text = String(url || "").trim()
  if (!text) return ""
  if (text.startsWith("http://") || text.startsWith("https://")) return text
  if (text.startsWith("/")) return `${BASE_URL}${text}`
  return text
}

function toAvatarPayloadValue(avatarUrl) {
  const text = String(avatarUrl || "").trim()
  if (!text) return ""
  if (text.startsWith(`${BASE_URL}/`)) return text.slice(BASE_URL.length)
  return text
}

export default {
  mixins: [themePageMixin],
  data() {
    return {
      account: "",
      role: "",
      nickname: "",
      phone: "",
      className: "",
      studentNo: "",
      jobNo: "",
      avatar: "",
      saving: false
    }
  },
  computed: {
    isStudent() {
      return this.role === "student"
    },
    isTeacherOrAdmin() {
      return this.role === "teacher" || this.role === "admin"
    },
    avatarText() {
      const source = String(this.nickname || this.account || "").trim()
      if (!source) return "U"
      return source.slice(0, 1).toUpperCase()
    }
  },
  onShow() {
    const session = uni.getStorageSync("session") || {}
    if (!session.username || !session.token) {
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }

    this.account = session.username || ""
    this.role = String(session.role || "").trim()
    this.loadProfileFromCache()
    this.syncProfileFromServer()
  },
  methods: {
    loadProfileFromCache() {
      const profile = uni.getStorageSync(profileStorageKey(this.account)) || {}
      this.nickname = String(profile.nickname || "").trim() || this.account
      this.phone = String(profile.phone || "").trim()
      this.className = String(profile.className || "").trim()
      this.studentNo = String(profile.studentNo || "").trim()
      this.jobNo = String(profile.jobNo || "").trim()
      this.avatar = normalizeAvatar(profile.avatar || profile.avatarUrl)
    },
    applyProfile(profile = {}) {
      this.role = String(profile.role || this.role || "").trim()
      this.nickname = String(profile.nickname || "").trim() || this.account
      this.phone = String(profile.phone || "").trim()
      this.className = String(profile.className || "").trim()
      this.studentNo = String(profile.studentNo || "").trim()
      this.jobNo = String(profile.jobNo || "").trim()
      this.avatar = normalizeAvatar(profile.avatarUrl || profile.avatar)
    },
    cacheProfile(profile = {}) {
      uni.setStorageSync(profileStorageKey(this.account), {
        account: this.account,
        role: this.role,
        nickname: String(profile.nickname || "").trim() || this.account,
        phone: String(profile.phone || "").trim(),
        className: String(profile.className || "").trim(),
        studentNo: String(profile.studentNo || "").trim(),
        jobNo: String(profile.jobNo || "").trim(),
        avatar: toAvatarPayloadValue(profile.avatarUrl || profile.avatar)
      })
    },
    async syncProfileFromServer() {
      try {
        const res = await uni.request({
          url: `${BASE_URL}/me/profile`,
          method: "GET"
        })
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) return
        this.applyProfile(payload.data)
        this.cacheProfile(payload.data)
      } catch (e) {}
    },
    emitProfileUpdated() {
      try {
        uni.$emit("profile:updated", {
          account: this.account,
          nickname: this.nickname,
          phone: this.phone,
          avatarUrl: toAvatarPayloadValue(this.avatar)
        })
      } catch (e) {}
    },
    chooseAvatar() {
      uni.chooseImage({
        count: 1,
        sizeType: ["compressed"],
        sourceType: ["album", "camera"],
        success: (res) => {
          const filePath = (res.tempFilePaths || [])[0]
          if (!filePath) return

          uni.showLoading({ title: "上传中" })
          uni.uploadFile({
            url: `${BASE_URL}/upload`,
            filePath,
            name: "file",
            success: (uploadRes) => {
              let payload = {}
              try {
                payload = typeof uploadRes.data === "string" ? JSON.parse(uploadRes.data || "{}") : (uploadRes.data || {})
              } catch (e) {
                payload = {}
              }

              const url =
                (payload && payload.data && payload.data.url) ||
                (payload && payload.url) ||
                ""
              if (!url) {
                uni.showToast({ title: "上传失败", icon: "none" })
                return
              }
              this.avatar = normalizeAvatar(url)
              uni.showToast({ title: "头像已更新", icon: "success" })
            },
            fail: () => {
              uni.showToast({ title: "上传失败", icon: "none" })
            },
            complete: () => {
              uni.hideLoading()
            }
          })
        }
      })
    },
    async saveProfile() {
      const name = String(this.nickname || "").trim()
      const phone = String(this.phone || "").trim()
      const className = String(this.className || "").trim()
      const studentNo = String(this.studentNo || "").trim()
      const jobNo = String(this.jobNo || "").trim()
      if (!name) {
        uni.showToast({ title: "昵称不能为空", icon: "none" })
        return
      }
      this.saving = true

      try {
        const res = await uni.request({
          url: `${BASE_URL}/me/profile`,
          method: "POST",
          header: { "Content-Type": "application/json" },
          data: {
            nickname: name,
            phone,
            className,
            studentNo,
            jobNo,
            avatarUrl: toAvatarPayloadValue(this.avatar)
          }
        })
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          uni.showToast({ title: payload.msg || "保存失败", icon: "none" })
          return
        }
        this.applyProfile(payload.data)
        this.cacheProfile(payload.data)
        this.emitProfileUpdated()
        uni.showToast({ title: "保存成功", icon: "success" })
        setTimeout(() => {
          uni.navigateBack()
        }, 250)
      } catch (e) {
        uni.showToast({ title: "保存失败", icon: "none" })
      } finally {
        this.saving = false
      }
    }
  }
}
</script>

<style lang="scss">
.profilePage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid var(--color-border-focus);
  background: var(--color-bg-soft);
}

.formCard {
  border: 1px solid var(--color-border-primary);
  padding: 0;
  overflow: hidden;
}

.formItem {
  min-height: 56px;
  border-bottom: 1px solid var(--color-border-primary);
  padding: 0 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-sizing: border-box;
  background: var(--color-bg-card);
}

.formItem:last-child {
  border-bottom: none;
}

.formItem:active {
  background: var(--color-bg-soft);
}

.avatarItem {
  min-height: 88px;
}

.rightWrap {
  display: flex;
  align-items: center;
  min-width: 0;
}

.avatarWrap {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: 1px solid var(--color-border-primary);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
  box-sizing: border-box;
}

.avatarImage {
  width: 100%;
  height: 100%;
}

.avatarText {
  font-size: 24px;
  line-height: 24px;
  color: var(--color-text-primary);
}

.inputValue {
  flex: 1;
  min-width: 0;
  text-align: right;
  font-size: 16px;
  line-height: 24px;
  color: var(--color-text-primary);
}

.readonlyValue {
  flex: 1;
  min-width: 0;
  text-align: right;
  font-size: 16px;
  line-height: 24px;
  color: var(--color-text-muted);
}

.itemArrow {
  font-size: 16px;
  line-height: 24px;
  color: var(--color-text-secondary);
}

.saveBtn {
  width: 100%;
  margin-top: 6px;
  min-height: 44px;
  line-height: 44px;
  border-radius: 12px;
  font-size: 16px;
}

.fieldLabel {
  font-size: 16px;
  line-height: 24px;
  color: var(--color-text-primary);
  margin-right: 16px;
  flex-shrink: 0;
}
</style>

