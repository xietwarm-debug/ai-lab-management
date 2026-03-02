<template>
  <view class="container portalPage" :class="themeClass">
    <view class="stack">
      <view class="card heroCard">
        <view class="heroBadge">AIlab</view>
        <view class="title">高校实验室智能管理系统</view>
        <view class="subtitle">预约、审批、通知、失物招领一体化平台</view>
        <view class="heroMetaRow">
          <view class="heroMetaItem">当前账号：{{ username || "未登录" }}</view>
          <view class="heroMetaItem">身份：{{ roleText }}</view>
        </view>
      </view>

      <view class="card feedCard" @click="goFeed">
        <view class="rowBetween feedHead">
          <view class="cardTitle">动态</view>
          <view class="feedMore">查看更多</view>
        </view>

        <view v-if="feedLoading" class="feedEmpty">加载中...</view>
        <view v-else-if="previewFeed.length === 0" class="feedEmpty">暂无动态</view>
        <view v-else class="feedPreviewList">
          <view class="feedPreviewItem" v-for="item in previewFeed" :key="item.id">
            <view class="feedPreviewTitle">{{ item.title }}</view>
            <view class="feedPreviewMeta">{{ item.type }} · {{ item.time }}</view>
          </view>
        </view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">快捷入口</view>
        </view>

        <view class="entryGrid">
          <view class="entryCard" v-for="item in entries" :key="item.key" @click="openEntry(item.key)">
            <view class="entryIcon" :class="'tone-' + item.tone">{{ item.icon }}</view>
            <view class="entryName">{{ item.name }}</view>
            <view class="entryDesc">{{ item.desc }}</view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"
import { themePageMixin } from "@/common/theme.js"

function parseListPayload(payload) {
  if (Array.isArray(payload)) return payload
  if (payload && Array.isArray(payload.data)) return payload.data
  if (payload && payload.ok && Array.isArray(payload.data)) return payload.data
  return []
}

export default {
  mixins: [themePageMixin],
  data() {
    return {
      username: "",
      role: "",
      feedList: [],
      feedLoading: false
    }
  },
  computed: {
    roleText() {
      if (this.role === "admin") return "管理员"
      if (this.role === "student") return "学生"
      return "访客"
    },
    previewFeed() {
      return this.feedList.slice(0, 2)
    },
    entries() {
      const base = [
        { key: "labs", icon: "室", name: "实验室", desc: "查看状态", tone: "blue" },
        { key: "reserve", icon: "约", name: "预约", desc: "提交申请", tone: "green" },
        { key: "agent", icon: "AI", name: "助手", desc: "快速预约", tone: "indigo" },
        { key: "notifications", icon: "通", name: "通知", desc: "消息提醒", tone: "violet" },
        { key: "lostfound", icon: "失", name: "失物招领", desc: "发布认领", tone: "slate" },
        { key: "my", icon: "我", name: "我的", desc: "个人中心", tone: "amber" }
      ]
      if (this.role === "admin") {
        base.unshift({ key: "admin", icon: "管", name: "后台", desc: "审批管理", tone: "violet" })
      }
      return base
    }
  },
  onShow() {
    const session = uni.getStorageSync("session") || {}
    this.username = session.username || ""
    this.role = session.role || ""
    this.loadFeedPreview()
  },
  methods: {
    async loadFeedPreview() {
      if (this.feedLoading) return
      this.feedLoading = true
      try {
        const res = await uni.request({
          url: `${BASE_URL}/announcements?limit=5`,
          method: "GET"
        })
        const rows = parseListPayload(res && res.data)
        this.feedList = rows.map((row) => ({
          id: `announcement-${row.id}`,
          type: "系统公告",
          title: row.title || "未命名公告",
          time: row.createdAt || "-"
        }))
      } catch (e) {
        this.feedList = []
      } finally {
        this.feedLoading = false
      }
    },
    openEntry(key) {
      if (key === "admin") return this.goAdmin()
      if (key === "labs") return this.goLabs()
      if (key === "reserve") return this.goReserve()
      if (key === "agent") return this.goAgent()
      if (key === "notifications") return this.goNotifications()
      if (key === "lostfound") return this.goLostFound()
      if (key === "my") return this.goMy()
    },
    goAdmin() {
      uni.navigateTo({ url: "/pages/admin/admin" })
    },
    goLabs() {
      uni.navigateTo({ url: "/pages/labs/labs" })
    },
    goReserve() {
      uni.navigateTo({ url: "/pages/reserve/reserve" })
    },
    goAgent() {
      uni.switchTab({ url: "/pages/agent/agent" })
    },
    goFeed() {
      uni.navigateTo({ url: "/pages/feed/feed" })
    },
    goNotifications() {
      uni.navigateTo({ url: "/pages/notifications/list" })
    },
    goLostFound() {
      uni.navigateTo({ url: "/pages/lostfound/list" })
    },
    goMy() {
      uni.switchTab({ url: "/pages/my/my" })
    }
  }
}
</script>

<style lang="scss">
.portalPage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid var(--color-border-focus);
  background: var(--color-bg-soft);
}

.heroBadge {
  width: fit-content;
  height: 22px;
  line-height: 22px;
  border-radius: 999px;
  padding: 0 10px;
  font-size: 11px;
  font-weight: 600;
  color: var(--info);
  background: var(--color-info-soft);
  border: 1px solid var(--color-border-primary);
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
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-primary);
  color: var(--color-text-secondary);
  font-size: 11px;
}

.feedCard {
  border: 1px solid var(--color-border-primary);
}

.feedHead {
  align-items: center;
}

.feedMore {
  font-size: 12px;
  color: var(--color-text-muted);
}

.feedEmpty {
  margin-top: 10px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.feedPreviewList {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.feedPreviewItem {
  border: 1px solid var(--color-border-primary);
  border-radius: 10px;
  padding: 8px;
  background: var(--color-bg-card);
}

.feedPreviewTitle {
  font-size: 13px;
  line-height: 18px;
  color: var(--color-text-primary);
  font-weight: 600;
}

.feedPreviewMeta {
  margin-top: 4px;
  font-size: 11px;
  line-height: 16px;
  color: var(--color-text-muted);
}

.entryGrid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.entryCard {
  border: 1px solid var(--color-border-primary);
  border-radius: 10px;
  background: var(--color-bg-card);
  padding: 8px;
  transition: transform 0.14s ease, box-shadow 0.14s ease;
}

.entryCard:active {
  transform: scale(0.985);
  box-shadow: var(--shadow-sm);
}

.entryIcon {
  width: 24px;
  height: 24px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
}

.entryIcon.tone-blue {
  color: var(--info);
  background: var(--color-info-soft);
}

.entryIcon.tone-green {
  color: var(--success);
  background: var(--color-success-soft);
}

.entryIcon.tone-amber {
  color: var(--warning);
  background: var(--color-warning-soft);
}

.entryIcon.tone-indigo {
  color: var(--info);
  background: var(--color-info-soft);
}

.entryIcon.tone-violet {
  color: var(--info);
  background: var(--color-info-soft);
}

.entryIcon.tone-slate {
  color: var(--color-text-secondary);
  background: var(--color-bg-soft);
}

.entryName {
  margin-top: 6px;
  font-size: 12px;
  line-height: 16px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.entryDesc {
  margin-top: 2px;
  font-size: 10px;
  line-height: 14px;
  color: var(--color-text-muted);
}
</style>
