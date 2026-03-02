<template>
  <view class="container feedPage" :class="themeClass">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween">
          <view>
            <view class="title">动态</view>
            <view class="subtitle">系统公告与校园服务更新</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="loading" @click="refreshFeed">刷新</button>
        </view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">最新动态</view>
          <view class="muted">{{ feedList.length }} 条</view>
        </view>

        <view v-if="loading" class="empty">加载中...</view>

        <view v-else-if="feedList.length === 0" class="emptyState compactEmpty">
          <view class="emptyIcon">动</view>
          <view class="emptyTitle">暂无动态</view>
          <view class="emptySub">管理员发布公告后会显示在这里</view>
        </view>

        <view v-else class="stack feedList">
          <view v-for="item in feedList" :key="item.id" class="feedItem">
            <view class="rowBetween">
              <view class="feedType">{{ item.type }}</view>
              <view class="muted">{{ item.time }}</view>
            </view>
            <view class="feedTitle">{{ item.title }}</view>
            <view class="feedDesc">{{ item.desc }}</view>
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
      feedList: [],
      loading: false
    }
  },
  onShow() {
    const s = uni.getStorageSync("session") || {}
    if (!s.username || !s.token) {
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    this.loadFeed()
  },
  methods: {
    async loadFeed() {
      if (this.loading) return
      this.loading = true
      try {
        const res = await uni.request({
          url: `${BASE_URL}/announcements?limit=50`,
          method: "GET"
        })
        const rows = parseListPayload(res && res.data)
        this.feedList = rows.map((row) => ({
          id: `announcement-${row.id}`,
          type: "系统公告",
          title: row.title || "未命名公告",
          desc: row.content || "",
          time: row.createdAt || "-"
        }))
      } catch (e) {
        this.feedList = []
        uni.showToast({ title: "动态加载失败", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    refreshFeed() {
      this.loadFeed()
    }
  }
}
</script>

<style lang="scss">
.feedPage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid var(--color-border-focus);
  background: var(--color-bg-soft);
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  font-size: 12px;
  border-radius: 9px;
}

.compactEmpty {
  margin-top: 10px;
  padding: 16px 12px;
}

.feedList {
  margin-top: 10px;
}

.feedItem {
  border: 1px solid var(--color-border-primary);
  border-radius: 12px;
  background: var(--color-bg-card);
  padding: 10px;
}

.feedType {
  height: 20px;
  line-height: 20px;
  border-radius: 999px;
  padding: 0 8px;
  font-size: 11px;
  color: var(--info);
  background: var(--color-info-soft);
}

.feedTitle {
  margin-top: 8px;
  font-size: 14px;
  line-height: 20px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.feedDesc {
  margin-top: 4px;
  font-size: 12px;
  line-height: 18px;
  color: var(--color-text-secondary);
  white-space: pre-wrap;
}
</style>
