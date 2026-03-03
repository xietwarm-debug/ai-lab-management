<template>
  <view class="myPage" :class="themeClass">
    <view class="profileBar" @click="goProfile">
      <view class="avatarWrap">
        <image v-if="avatar" class="avatarImage" :src="avatar" mode="aspectFill" />
        <view v-else class="avatarText">{{ avatarText }}</view>
      </view>
      <view class="profileText">
        <view class="nickname">{{ nickname }}</view>
        <view class="accountLine">账号：{{ account || "-" }}</view>
      </view>
      <view class="arrow">&gt;</view>
    </view>

    <view class="menuList">
      <view class="menuItem" @click="goReservations">
        <view class="leftWrap">
          <view class="itemIcon">预</view>
          <view class="itemText">我的预约</view>
        </view>
        <view class="arrow">&gt;</view>
      </view>

      <view class="menuItem" @click="goSettings">
        <view class="leftWrap">
          <view class="itemIcon">设</view>
          <view class="itemText">设置</view>
        </view>
        <view class="arrow">&gt;</view>
      </view>
    </view>

    <view class="logoutArea">
      <view class="logoutBtn" @click="handleLogout">退出登录</view>
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

export default {
  mixins: [themePageMixin],
  data() {
    return {
      account: "",
      nickname: "",
      avatar: ""
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
    const savedNick = String(profile.nickname || "").trim()
    this.nickname = savedNick || this.account
    this.avatar = normalizeAvatar(profile.avatar)
  },
  methods: {
    goProfile() {
      uni.navigateTo({ url: "/pages/my/profile" })
    },
    goReservations() {
      uni.navigateTo({ url: "/pages/my/reservations" })
    },
    goSettings() {
      uni.navigateTo({ url: "/pages/settings/settings" })
    },
    handleLogout() {
      uni.removeStorageSync("session")
      uni.reLaunch({ url: "/pages/login/login" })
    }
  }
}
</script>

<style lang="scss">
page {
  background: var(--color-bg-page);
}

.myPage {
  min-height: 100vh;
  background: var(--color-bg-page);
  color: var(--color-text-primary);
  padding: 16px;
  padding-bottom: calc(132px + env(safe-area-inset-bottom));
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

.profileBar {
  display: flex;
  align-items: center;
  border-top: 1px solid var(--color-border-primary);
  border-bottom: 1px solid var(--color-border-primary);
  padding: 16px 0;
  background: var(--color-bg-card);
}

.profileBar:active {
  background: var(--color-bg-soft);
}

.avatarWrap {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  border: 1px solid var(--color-border-primary);
  margin-right: 16px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
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

.profileText {
  min-width: 0;
  flex: 1;
}

.nickname {
  font-size: 20px;
  line-height: 28px;
  color: var(--color-text-primary);
  font-weight: 600;
}

.accountLine {
  margin-top: 4px;
  font-size: 14px;
  line-height: 20px;
  color: var(--color-text-muted);
}

.menuList {
  margin-top: 16px;
  border-top: 1px solid var(--color-border-primary);
  border-bottom: 1px solid var(--color-border-primary);
  background: var(--color-bg-card);
}

.menuItem {
  min-height: 56px;
  padding: 16px 0;
  border-bottom: 1px solid var(--color-border-primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-sizing: border-box;
}

.menuItem:last-child {
  border-bottom: none;
}

.menuItem:active {
  background: var(--color-bg-soft);
}

.leftWrap {
  display: flex;
  align-items: center;
  min-width: 0;
}

.itemIcon {
  width: 24px;
  height: 24px;
  font-size: 24px;
  line-height: 24px;
  color: var(--color-text-primary);
  text-align: center;
  margin-right: 16px;
  flex-shrink: 0;
}

.itemText {
  font-size: 16px;
  line-height: 24px;
  color: var(--color-text-primary);
}

.arrow {
  font-size: 16px;
  line-height: 24px;
  color: var(--color-text-primary);
  margin-left: 16px;
}

.logoutArea {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  width: calc(100% - 32px);
  max-width: 448px;
  bottom: calc(62px + env(safe-area-inset-bottom));
  z-index: 20;
}

.logoutBtn {
  height: 44px;
  border-radius: 22px;
  background: var(--danger);
  color: var(--color-text-inverse);
  font-size: 16px;
  line-height: 44px;
  text-align: center;
}

.logoutBtn:active {
  opacity: 0.9;
}
</style>
