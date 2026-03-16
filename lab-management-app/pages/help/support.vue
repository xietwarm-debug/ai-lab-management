<template>
  <view class="container supportPage" :class="themeClass">
    <view class="stack">
      <view class="card">
        <view class="title">客服入口</view>
        <view class="subtitle">工作日 09:00-18:00，建议先查看常见问题</view>
      </view>

      <view class="card">
        <view class="row">
          <view class="label">服务电话</view>
          <view class="value">400-800-1234</view>
        </view>
        <view class="actionRow">
          <button class="btnSecondary miniBtn" size="mini" @click="callPhone">拨打电话</button>
          <button class="btnSecondary miniBtn" size="mini" @click="copyText('400-800-1234', '电话')">复制号码</button>
        </view>

        <view class="row">
          <view class="label">服务邮箱</view>
          <view class="value">support@lab.local</view>
        </view>
        <view class="actionRow">
          <button class="btnSecondary miniBtn" size="mini" @click="copyText('support@lab.local', '邮箱')">复制邮箱</button>
        </view>

        <view class="row">
          <view class="label">企业微信</view>
          <view class="value">lab_support</view>
        </view>
        <view class="actionRow">
          <button class="btnSecondary miniBtn" size="mini" @click="copyText('lab_support', '企业微信')">复制微信号</button>
        </view>
      </view>

      <view class="card">
        <view class="cardTitle">建议路径</view>
        <view class="muted tipText">一般问题先看常见问题，系统异常可直接提交在线反馈并附上复现步骤。</view>
        <view class="actionRow">
          <button class="btnPrimary miniBtn" size="mini" @click="goFaq">常见问题</button>
          <button class="btnPrimary miniBtn" size="mini" @click="goFeedback">在线反馈</button>
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
    copyText(text, label = "内容") {
      uni.setClipboardData({
        data: String(text || ""),
        success: () => uni.showToast({ title: `${label}已复制`, icon: "none" })
      })
    },
    callPhone() {
      if (typeof uni.makePhoneCall !== "function") {
        this.copyText("400-800-1234", "电话")
        return
      }
      uni.makePhoneCall({
        phoneNumber: "400-800-1234",
        fail: () => this.copyText("400-800-1234", "电话")
      })
    },
    goFaq() {
      uni.navigateTo({ url: "/pages/help/faq" })
    },
    goFeedback() {
      uni.navigateTo({ url: "/pages/help/feedback" })
    }
  }
}
</script>

<style lang="scss">
.supportPage {
  padding-bottom: 24px;
}

.row {
  margin-top: 8px;
}

.label {
  font-size: 12px;
  line-height: 18px;
  color: var(--color-text-muted);
}

.value {
  margin-top: 2px;
  font-size: 15px;
  line-height: 22px;
  color: var(--color-text-primary);
  font-weight: 600;
}

.actionRow {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tipText {
  margin-top: 6px;
}
</style>
