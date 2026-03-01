<template>
  <view class="container notifyPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">通知中心</view>
            <view class="subtitle">预约进度与失物招领动态</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" @click="fetchList">刷新</button>
        </view>
        <view class="heroMetaRow">
          <view class="heroMetaItem">未读总数 {{ unreadTotal }}</view>
          <view class="heroMetaItem">预约 {{ unreadReservation }}</view>
          <view class="heroMetaItem">失物 {{ unreadLostfound }}</view>
        </view>
      </view>

      <view class="card toolbarCard">
        <view class="rowBetween">
          <view class="cardTitle">消息筛选</view>
          <button class="btnSecondary miniBtn" size="mini" :disabled="shown.length === 0" @click="markCurrentRead">
            标记当前已读
          </button>
        </view>

        <view class="filterChips">
          <view
            v-for="item in typeOptions"
            :key="item.value"
            class="chip chipBtn"
            :class="{ chipOn: typeFilter === item.value }"
            @click="setTypeFilter(item.value)"
          >
            {{ item.label }}
            <text v-if="item.value === 'all' && unreadTotal > 0">({{ unreadTotal }})</text>
            <text v-if="item.value === 'reservation' && unreadReservation > 0">({{ unreadReservation }})</text>
            <text v-if="item.value === 'lostfound' && unreadLostfound > 0">({{ unreadLostfound }})</text>
          </view>
        </view>

        <view class="muted summaryText">当前筛选共 {{ shown.length }} 条</view>
      </view>

      <view class="card loadingCard" v-if="loading">
        <view class="muted">正在加载通知...</view>
      </view>

      <view class="stack" v-else-if="shown.length > 0">
        <view class="card noticeItem" v-for="n in shown" :key="n.id || n.createdAt" :class="{ unread: isUnread(n) }">
          <view class="rowBetween">
            <view class="noticeHead">
              <view class="typeTag" :class="n.type">{{ typeText(n.type) }}</view>
              <view class="noticeName">{{ n.labName || '系统通知' }}</view>
            </view>
            <view class="rowBetween noticeRight">
              <view class="statusTag" :class="statusTone(n.status)">{{ statusText(n.status) }}</view>
              <view class="redDot" v-if="isUnread(n)"></view>
            </view>
          </view>
          <view class="noticeMessage lineClamp">{{ n.message || '暂无通知内容' }}</view>
          <view class="muted noticeTime">{{ n.createdAt || '-' }}</view>
        </view>
      </view>

      <view class="emptyState" v-else>
        <view class="emptyIcon">信</view>
        <view class="emptyTitle">暂无通知</view>
        <view class="emptySub">预约和失物相关消息会在这里展示</view>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"

function getReadKeys(username) {
  return {
    reservation: `notifications_last_read_reservation_${username}`,
    lostfound: `notifications_last_read_lostfound_${username}`
  }
}

function sortByCreatedAtDesc(rows) {
  return rows
    .slice()
    .sort((a, b) => String(b.createdAt || "").localeCompare(String(a.createdAt || "")))
}

export default {
  data() {
    return {
      list: [],
      user: "",
      typeFilter: "all",
      lastReadReservation: "",
      lastReadLostfound: "",
      loading: false,
      typeOptions: [
        { label: "全部", value: "all" },
        { label: "预约", value: "reservation" },
        { label: "失物", value: "lostfound" }
      ]
    }
  },
  computed: {
    sortedList() {
      return sortByCreatedAtDesc(this.list)
    },
    shown() {
      if (this.typeFilter === "all") return this.sortedList
      return this.sortedList.filter((n) => n.type === this.typeFilter)
    },
    unreadReservation() {
      return this.sortedList.filter((n) => n.type === "reservation" && this.isUnread(n)).length
    },
    unreadLostfound() {
      return this.sortedList.filter((n) => n.type === "lostfound" && this.isUnread(n)).length
    },
    unreadTotal() {
      return this.unreadReservation + this.unreadLostfound
    }
  },
  onShow() {
    const s = uni.getStorageSync("session")
    this.user = s && s.username ? s.username : ""
    if (!this.user) {
      uni.showToast({ title: "请先登录", icon: "none" })
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }

    const keys = getReadKeys(this.user)
    this.lastReadReservation = uni.getStorageSync(keys.reservation) || ""
    this.lastReadLostfound = uni.getStorageSync(keys.lostfound) || ""
    this.fetchList()
  },
  methods: {
    setTypeFilter(type) {
      this.typeFilter = type
    },
    fetchList() {
      this.loading = true
      uni.request({
        url: `${BASE_URL}/notifications`,
        method: "GET",
        success: (res) => {
          this.list = Array.isArray(res.data) ? res.data : []
        },
        fail: () => {
          this.list = []
          uni.showToast({ title: "获取通知失败", icon: "none" })
        },
        complete: () => {
          this.loading = false
        }
      })
    },
    isUnread(row) {
      if (row.type === "reservation") {
        if (!this.lastReadReservation) return true
        return (row.createdAt || "") > this.lastReadReservation
      }
      if (row.type === "lostfound") {
        if (!this.lastReadLostfound) return true
        return (row.createdAt || "") > this.lastReadLostfound
      }
      return false
    },
    latestByType(type) {
      const row = this.sortedList.find((x) => x.type === type)
      return row ? row.createdAt || "" : ""
    },
    markCurrentRead() {
      if (!this.user) return
      const keys = getReadKeys(this.user)

      if (this.typeFilter === "all") {
        const latestReservation = this.latestByType("reservation")
        const latestLostfound = this.latestByType("lostfound")
        if (latestReservation) {
          this.lastReadReservation = latestReservation
          uni.setStorageSync(keys.reservation, latestReservation)
        }
        if (latestLostfound) {
          this.lastReadLostfound = latestLostfound
          uni.setStorageSync(keys.lostfound, latestLostfound)
        }
      } else if (this.typeFilter === "reservation") {
        const latestReservation = this.latestByType("reservation")
        if (latestReservation) {
          this.lastReadReservation = latestReservation
          uni.setStorageSync(keys.reservation, latestReservation)
        }
      } else if (this.typeFilter === "lostfound") {
        const latestLostfound = this.latestByType("lostfound")
        if (latestLostfound) {
          this.lastReadLostfound = latestLostfound
          uni.setStorageSync(keys.lostfound, latestLostfound)
        }
      }

      uni.showToast({ title: "已标记已读", icon: "success" })
    },
    typeText(type) {
      if (type === "lostfound") return "失物"
      return "预约"
    },
    statusTone(status) {
      if (status === "approved" || status === "closed" || status === "claim_approved") return "success"
      if (status === "pending" || status === "open" || status === "claim_pending") return "warning"
      if (status === "rejected" || status === "cancelled" || status === "claim_rejected") return "danger"
      return "info"
    },
    statusText(status) {
      if (status === "pending") return "待审批"
      if (status === "approved") return "已通过"
      if (status === "rejected") return "已驳回"
      if (status === "cancelled") return "已取消"
      if (status === "open") return "处理中"
      if (status === "closed") return "已处理"
      if (status === "claim_pending") return "认领待审"
      if (status === "claim_approved") return "认领通过"
      if (status === "claim_rejected") return "认领驳回"
      return status || "-"
    }
  }
}
</script>

<style lang="scss">
.notifyPage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.2);
  background: linear-gradient(155deg, #ffffff 0%, #eef6ff 60%, #e7f0ff 100%);
}

.heroTop {
  align-items: flex-start;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  font-size: 12px;
  border-radius: 9px;
}

.heroMetaRow {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.heroMetaItem {
  height: 25px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(255, 255, 255, 0.8);
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  font-size: 11px;
  color: #334155;
}

.toolbarCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.filterChips {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chipBtn {
  transition: all 0.14s ease;
}

.chipOn {
  border-color: #bfdbfe;
  background: #eaf3ff;
  color: #1d4ed8;
}

.summaryText {
  margin-top: 8px;
}

.loadingCard {
  min-height: 68px;
  display: flex;
  align-items: center;
}

.noticeItem {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.noticeItem.unread {
  border-color: rgba(220, 38, 38, 0.28);
  box-shadow: 0 8px 20px rgba(220, 38, 38, 0.08);
}

.noticeHead {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.noticeName {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.typeTag {
  height: 18px;
  line-height: 18px;
  border-radius: 999px;
  padding: 0 7px;
  font-size: 10px;
  font-weight: 600;
  background: #eaf3ff;
  color: #1d4ed8;
  flex-shrink: 0;
}

.typeTag.lostfound {
  background: #fff7e6;
  color: #9a5d00;
}

.noticeRight {
  gap: 8px;
}

.noticeMessage {
  margin-top: 6px;
  color: #475569;
  font-size: 12px;
  line-height: 18px;
}

.lineClamp {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.noticeTime {
  margin-top: 6px;
}

.redDot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #dc2626;
}
</style>
