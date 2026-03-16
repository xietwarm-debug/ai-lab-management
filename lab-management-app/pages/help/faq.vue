<template>
  <view class="container faqPage" :class="themeClass">
    <view class="stack">
      <view class="card">
        <view class="title">常见问题</view>
        <view class="subtitle">覆盖学生、教师、管理员常用操作</view>
      </view>

      <view class="card" v-for="(item, idx) in faqList" :key="`faq-${idx}`">
        <view class="qLine">Q{{ idx + 1 }}. {{ item.q }}</view>
        <view class="aLine">{{ item.a }}</view>
      </view>
    </view>
  </view>
</template>

<script>
import { themePageMixin } from "@/common/theme.js"

const COMMON_FAQ = [
  {
    q: "看不到可预约实验室怎么办？",
    a: "请先确认日期时段是否开放、实验室是否被占用，以及账号是否有对应访问权限。"
  },
  {
    q: "借用申请提交后多久有结果？",
    a: "通常由管理员在审批中心处理。可在“我的借用”里查看审批和归还状态。"
  },
  {
    q: "通知没有红点或数量不对怎么办？",
    a: "下拉刷新后重试，并确认当前登录账号是否正确；必要时重新登录。"
  }
]

const TEACHER_FAQ = [
  {
    q: "作业批改里看不到课程或任务怎么办？",
    a: "请确认你是课程负责教师，课程状态为启用，且任务未删除。"
  },
  {
    q: "待批改数量和列表不一致怎么办？",
    a: "大厅显示的是当前筛选口径下的总待批改数，进入批改页后可再次下拉刷新。"
  }
]

const ADMIN_FAQ = [
  {
    q: "为什么有些资产无法被借用？",
    a: "资产“是否允许租借”为否时，用户端不会展示该资产。机房电脑默认不可借用。"
  },
  {
    q: "如何处理逾期未归还用户？",
    a: "在租借审批中心可看到逾期状态与用户标记，后续申请会有特殊提醒。"
  }
]

export default {
  mixins: [themePageMixin],
  data() {
    return {
      role: ""
    }
  },
  computed: {
    faqList() {
      if (this.role === "teacher") return COMMON_FAQ.concat(TEACHER_FAQ)
      if (this.role === "admin") return COMMON_FAQ.concat(ADMIN_FAQ)
      return COMMON_FAQ
    }
  },
  onShow() {
    const session = uni.getStorageSync("session") || {}
    if (!session.username || !session.token) {
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    this.role = String(session.role || "").trim().toLowerCase()
  }
}
</script>

<style lang="scss">
.faqPage {
  padding-bottom: 24px;
}

.qLine {
  font-size: 15px;
  line-height: 22px;
  color: var(--color-text-primary);
  font-weight: 600;
}

.aLine {
  margin-top: 8px;
  font-size: 13px;
  line-height: 20px;
  color: var(--color-text-secondary);
}
</style>
