<template>
  <view class="container feedPage" :class="themeClass">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween">
          <view>
            <view class="title">Campus Feed</view>
            <view class="subtitle">System announcements and service updates</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="loading" @click="refreshFeed">Refresh</button>
        </view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">Latest updates</view>
          <view class="muted">{{ feedList.length }} items</view>
        </view>

        <view v-if="loading" class="empty">Loading...</view>

        <view v-else-if="feedList.length === 0" class="emptyState compactEmpty">
          <view class="emptyIcon">N</view>
          <view class="emptyTitle">No updates</view>
          <view class="emptySub">Announcements will appear here after they are published.</view>
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
import { fetchAnnouncementRows } from "@/common/announcements.js"
import { themePageMixin } from "@/common/theme.js"

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
        const result = await fetchAnnouncementRows({ limit: 50, retries: 1, maxAgeMs: 5 * 60 * 1000 })
        const rows = Array.isArray(result && result.rows) ? result.rows : []
        this.feedList = rows.map((row) => ({
          id: `announcement-${row.id}`,
          type: "Announcement",
          title: row.title || "Untitled announcement",
          desc: row.content || "",
          time: row.createdAt || "-"
        }))
        if (result && result.stale) {
          uni.showToast({ title: "Showing cached feed", icon: "none" })
        }
      } catch (e) {
        this.feedList = []
        uni.showToast({ title: "Feed load failed", icon: "none" })
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
