<template>
  <view class="container helpIndexPage" :class="themeClass">
    <view class="stack">
      <view class="card">
        <view class="title">帮助与反馈</view>
        <view class="subtitle">统一入口：常见问题、在线反馈、客服入口</view>
      </view>

      <view class="card entryList">
        <view class="entryItem" @click="goFaq">
          <view class="leftWrap">
            <view class="entryIcon">问</view>
            <view>
              <view class="entryTitle">常见问题</view>
              <view class="entryDesc muted">快速查看高频问题与处理建议</view>
            </view>
          </view>
          <view class="arrow">&gt;</view>
        </view>

        <view class="entryItem" @click="goFeedback">
          <view class="leftWrap">
            <view class="entryIcon">反</view>
            <view>
              <view class="entryTitle">在线反馈</view>
              <view class="entryDesc muted">提交问题、建议或咨询</view>
            </view>
          </view>
          <view class="arrow">&gt;</view>
        </view>

        <view class="entryItem" @click="goSupport">
          <view class="leftWrap">
            <view class="entryIcon">客</view>
            <view>
              <view class="entryTitle">客服入口</view>
              <view class="entryDesc muted">电话、邮箱与企业微信联系</view>
            </view>
          </view>
          <view class="arrow">&gt;</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { themePageMixin } from "@/common/theme.js"

export default {
  mixins: [themePageMixin],
  onShow() {
    const session = uni.getStorageSync("session") || {}
    if (!session.username || !session.token) {
      uni.reLaunch({ url: "/pages/login/login" })
    }
  },
  methods: {
    goFaq() {
      uni.navigateTo({ url: "/pages/help/faq" })
    },
    goFeedback() {
      uni.navigateTo({ url: "/pages/help/feedback" })
    },
    goSupport() {
      uni.navigateTo({ url: "/pages/help/support" })
    }
  }
}
</script>

<style lang="scss">
.helpIndexPage {
  padding-bottom: 24px;
}

.entryList {
  padding: 0;
}

.entryItem {
  min-height: 62px;
  padding: 12px;
  border-bottom: 1px solid var(--color-border-primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-sizing: border-box;
}

.entryItem:last-child {
  border-bottom: none;
}

.entryItem:active {
  background: var(--color-bg-soft);
}

.leftWrap {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.entryIcon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(22, 119, 255, 0.12);
  color: var(--brand);
  font-size: 14px;
  line-height: 14px;
  flex-shrink: 0;
}

.entryTitle {
  font-size: 15px;
  line-height: 22px;
  color: var(--color-text-primary);
  font-weight: 600;
}

.entryDesc {
  margin-top: 2px;
  font-size: 12px;
  line-height: 18px;
}

.arrow {
  margin-left: 8px;
  color: var(--color-text-muted);
}
</style>
