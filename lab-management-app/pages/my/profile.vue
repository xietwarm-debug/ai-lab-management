<template>
  <view class="profilePage">
    <view class="formList">
      <view class="formItem avatarItem" @click="chooseAvatar">
        <view class="label">头像</view>
        <view class="rightWrap">
          <view class="avatarWrap">
            <image v-if="avatar" class="avatarImage" :src="avatar" mode="aspectFill" />
            <view v-else class="avatarText">{{ avatarText }}</view>
          </view>
          <view class="arrow">&gt;</view>
        </view>
      </view>

      <view class="formItem">
        <view class="label">昵称</view>
        <input class="inputValue" v-model.trim="nickname" maxlength="24" placeholder="请输入昵称" />
      </view>

      <view class="formItem">
        <view class="label">手机号</view>
        <input class="inputValue" v-model.trim="phone" type="number" maxlength="20" placeholder="请输入手机号" />
      </view>

      <view class="formItem">
        <view class="label">账号</view>
        <view class="readonlyValue">{{ account || "-" }}</view>
      </view>
    </view>

    <button class="saveBtn" :disabled="saving" @click="saveProfile">{{ saving ? "保存中..." : "保存" }}</button>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"

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

export default {
  data() {
    return {
      account: "",
      nickname: "",
      phone: "",
      avatar: "",
      saving: false
    }
  },
  computed: {
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
    const profile = uni.getStorageSync(profileStorageKey(this.account)) || {}
    this.nickname = String(profile.nickname || "").trim() || this.account
    this.phone = String(profile.phone || "").trim()
    this.avatar = normalizeAvatar(profile.avatar)
  },
  methods: {
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
    saveProfile() {
      const name = String(this.nickname || "").trim()
      const phone = String(this.phone || "").trim()
      if (!name) {
        uni.showToast({ title: "昵称不能为空", icon: "none" })
        return
      }
      this.saving = true

      uni.setStorageSync(profileStorageKey(this.account), {
        account: this.account,
        nickname: name,
        phone,
        avatar: this.avatar
      })

      uni.showToast({ title: "保存成功", icon: "success" })
      setTimeout(() => {
        this.saving = false
        uni.navigateBack()
      }, 250)
    }
  }
}
</script>

<style lang="scss">
page {
  background: #ffffff;
}

.profilePage {
  min-height: 100vh;
  background: #ffffff;
  color: #000000;
  padding: 16px;
  box-sizing: border-box;
}

.formList {
  border-top: 1px solid #e5e5e5;
  border-bottom: 1px solid #e5e5e5;
}

.formItem {
  min-height: 56px;
  border-bottom: 1px solid #e5e5e5;
  padding: 16px 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-sizing: border-box;
}

.formItem:last-child {
  border-bottom: none;
}

.formItem:active {
  background: #f5f5f5;
}

.avatarItem {
  min-height: 88px;
}

.label {
  font-size: 16px;
  line-height: 24px;
  color: #000000;
  margin-right: 16px;
  flex-shrink: 0;
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
  border: 1px solid #e5e5e5;
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
  color: #000000;
}

.inputValue {
  flex: 1;
  min-width: 0;
  text-align: right;
  font-size: 16px;
  line-height: 24px;
  color: #000000;
}

.readonlyValue {
  flex: 1;
  min-width: 0;
  text-align: right;
  font-size: 16px;
  line-height: 24px;
  color: #999999;
}

.arrow {
  font-size: 16px;
  line-height: 24px;
  color: #000000;
}

.saveBtn {
  margin-top: 16px;
  height: 48px;
  line-height: 48px;
  border-radius: 0;
  border: 1px solid #e5e5e5;
  background: #ffffff;
  color: #000000;
  font-size: 16px;
}

.saveBtn:active {
  background: #f5f5f5;
}
</style>
