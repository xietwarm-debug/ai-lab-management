<template>
  <view class="container homePage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="heroTitle">{{ greetingText }}，{{ displayName }}</view>
            <view class="heroSub">实验室预约、通知提醒与进度跟踪</view>
          </view>
          <view class="verifiedTag">已认证</view>
        </view>
        <view class="heroMetaRow">
          <view class="heroMetaItem">
            <view class="dot online"></view>
            <view>服务状态正常</view>
          </view>
          <view class="heroMetaItem">最近同步 {{ lastSync || "--:--:--" }}</view>
        </view>
        <view class="heroActionRow">
          <button class="btnPrimary heroBtn" @click="goReserve">立即预约</button>
          <button class="btnSecondary heroBtn" @click="goLabs">查看实验室</button>
        </view>
      </view>

      <view class="overviewGrid">
        <view class="card overviewCard" v-for="item in overviewCards" :key="item.key">
          <view class="overviewLabel">{{ item.label }}</view>
          <view class="overviewValue">{{ item.value }}</view>
          <view class="overviewHint">{{ item.hint }}</view>
        </view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">核心功能</view>
          <view class="muted">高频入口</view>
        </view>
        <view class="featureGrid">
          <view class="featureCard" v-for="item in featureEntries" :key="item.key" @click="goByKey(item.key)">
            <view class="rowBetween">
              <view class="featureIcon" :class="'tone-' + item.tone">{{ item.icon }}</view>
              <view class="featureBadge" v-if="item.badge > 0">{{ item.badge }}</view>
            </view>
            <view class="featureName">{{ item.name }}</view>
            <view class="featureDesc">{{ item.desc }}</view>
          </view>
        </view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">最近动态</view>
          <button
            class="btnSecondary miniBtn"
            size="mini"
            :disabled="unreadCount === 0"
            @click="markAllAsRead"
          >一键已读</button>
        </view>

        <view class="loadingText muted" v-if="loading">同步中...</view>

        <view class="emptyState compactEmpty" v-else-if="latestNotifications.length === 0">
          <view class="emptyIcon">信</view>
          <view class="emptyTitle">暂无新动态</view>
          <view class="emptySub">预约状态和失物消息会在这里显示</view>
        </view>

        <view class="activityList" v-else>
          <view class="activityItem" v-for="n in latestNotifications" :key="n.id || n.createdAt" @click="goNotifications">
            <view class="rowBetween">
              <view class="activityHead">
                <view class="activityType" :class="n.type">{{ typeText(n.type) }}</view>
                <view class="activityName">{{ n.labName || "系统通知" }}</view>
              </view>
              <view class="rowBetween activityRight">
                <view class="statusTag" :class="statusTone(n.status)">{{ statusText(n.status) }}</view>
                <view class="redDot" v-if="isUnread(n)"></view>
              </view>
            </view>
            <view class="activityMessage lineClamp">{{ n.message || "暂无内容" }}</view>
            <view class="activityTime muted">{{ n.createdAt || "-" }}</view>
          </view>
        </view>

        <button class="btnGhost fullBtn" @click="goNotifications">进入通知中心</button>
      </view>

      <view class="card accountCard">
        <view class="rowBetween">
          <view>
            <view class="cardTitle">账号与安全</view>
            <view class="cardDesc">当前账号：{{ user || "-" }}</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" @click="refreshDashboard">刷新数据</button>
        </view>
        <button class="btnDanger logoutBtn" @click="logout">退出登录</button>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"

function parseListPayload(payload) {
  if (Array.isArray(payload)) return payload
  if (payload && Array.isArray(payload.data)) return payload.data
  if (payload && payload.ok && Array.isArray(payload.data)) return payload.data
  return []
}

function nowTimeText() {
  const d = new Date()
  const p = (n) => (n < 10 ? `0${n}` : `${n}`)
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

function getReadKey(username) {
  return {
    reservation: `notifications_last_read_reservation_${username}`,
    lostfound: `notifications_last_read_lostfound_${username}`
  }
}

function sortedByCreatedAtDesc(rows) {
  return rows
    .slice()
    .sort((a, b) => String(b.createdAt || "").localeCompare(String(a.createdAt || "")))
}

export default {
  data() {
    return {
      user: "",
      loading: false,
      lastSync: "",
      allNotifications: [],
      myReservations: [],
      unreadCount: 0,
      reservationUnreadCount: 0,
      lostFoundUnreadCount: 0,
      pendingReserveCount: 0,
      approvedReserveCount: 0,
      myReservationCount: 0,
      lastReadReservation: "",
      lastReadLostfound: ""
    }
  },
  computed: {
    displayName() {
      return this.user || "同学"
    },
    greetingText() {
      const hour = new Date().getHours()
      if (hour < 11) return "上午好"
      if (hour < 14) return "中午好"
      if (hour < 18) return "下午好"
      return "晚上好"
    },
    overviewCards() {
      return [
        {
          key: "unread",
          label: "未读提醒",
          value: this.unreadCount,
          hint: this.unreadCount > 0 ? "建议优先处理" : "当前已清空"
        },
        {
          key: "pending",
          label: "待审批预约",
          value: this.pendingReserveCount,
          hint: "审批前可改期/取消"
        },
        {
          key: "approved",
          label: "已通过预约",
          value: this.approvedReserveCount,
          hint: "可按时进实验室"
        },
        {
          key: "total",
          label: "我的预约总数",
          value: this.myReservationCount,
          hint: "含历史记录"
        }
      ]
    },
    featureEntries() {
      return [
        {
          key: "labs",
          icon: "室",
          name: "实验室列表",
          desc: "查看状态、容量与时段",
          tone: "blue",
          badge: 0
        },
        {
          key: "reserve",
          icon: "约",
          name: "我要预约",
          desc: "新建预约申请",
          tone: "green",
          badge: 0
        },
        {
          key: "my",
          icon: "单",
          name: "我的预约",
          desc: "进度查询与改期",
          tone: "amber",
          badge: this.pendingReserveCount
        },
        {
          key: "notifications",
          icon: "讯",
          name: "通知中心",
          desc: "预约与失物消息",
          tone: "violet",
          badge: this.unreadCount
        },
        {
          key: "lostfound",
          icon: "物",
          name: "失物招领",
          desc: "查看与发布信息",
          tone: "teal",
          badge: this.lostFoundUnreadCount
        }
      ]
    },
    latestNotifications() {
      return sortedByCreatedAtDesc(this.allNotifications).slice(0, 3)
    }
  },
  onShow() {
    this.bootstrap()
  },
  methods: {
    bootstrap() {
      const s = uni.getStorageSync("session")
      this.user = s && s.username ? s.username : ""
      if (!this.user) {
        uni.showToast({ title: "请先登录", icon: "none" })
        uni.reLaunch({ url: "/pages/login/login" })
        return
      }
      const keys = getReadKey(this.user)
      this.lastReadReservation = uni.getStorageSync(keys.reservation) || ""
      this.lastReadLostfound = uni.getStorageSync(keys.lostfound) || ""
      this.fetchDashboard()
    },
    requestList(url) {
      return new Promise((resolve, reject) => {
        uni.request({
          url,
          method: "GET",
          success: (res) => resolve(parseListPayload(res.data)),
          fail: (err) => reject(err)
        })
      })
    },
    async fetchDashboard() {
      if (!this.user) return
      this.loading = true
      try {
        const [notifications, reservations] = await Promise.all([
          this.requestList(`${BASE_URL}/notifications`),
          this.requestList(`${BASE_URL}/reservations?user=${encodeURIComponent(this.user)}`)
        ])

        this.allNotifications = notifications
        this.myReservations = reservations
        this.recalculateMetrics()
        this.lastSync = nowTimeText()
      } catch (e) {
        this.allNotifications = []
        this.myReservations = []
        this.recalculateMetrics()
      } finally {
        this.loading = false
      }
    },
    refreshDashboard() {
      this.fetchDashboard()
      uni.showToast({ title: "正在刷新", icon: "none" })
    },
    recalculateMetrics() {
      const reservations = this.myReservations
      this.myReservationCount = reservations.length
      this.pendingReserveCount = reservations.filter((x) => x.status === "pending").length
      this.approvedReserveCount = reservations.filter((x) => x.status === "approved").length

      const reservationUnread = this.allNotifications.filter((x) => {
        if (x.type !== "reservation") return false
        if (!this.lastReadReservation) return true
        return (x.createdAt || "") > this.lastReadReservation
      })
      const lostfoundUnread = this.allNotifications.filter((x) => {
        if (x.type !== "lostfound") return false
        if (!this.lastReadLostfound) return true
        return (x.createdAt || "") > this.lastReadLostfound
      })

      this.reservationUnreadCount = reservationUnread.length
      this.lostFoundUnreadCount = lostfoundUnread.length
      this.unreadCount = this.reservationUnreadCount + this.lostFoundUnreadCount
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
      const row = sortedByCreatedAtDesc(this.allNotifications).find((x) => x.type === type)
      return row ? row.createdAt || "" : ""
    },
    markAllAsRead() {
      if (!this.user || this.unreadCount === 0) return
      const keys = getReadKey(this.user)
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
      this.recalculateMetrics()
      uni.showToast({ title: "已标记已读", icon: "success" })
    },
    goByKey(key) {
      if (key === "labs") return this.goLabs()
      if (key === "reserve") return this.goReserve()
      if (key === "my") return this.goMy()
      if (key === "notifications") return this.goNotifications()
      if (key === "lostfound") return this.goLostFound()
    },
    goLabs() {
      uni.navigateTo({ url: "/pages/labs/labs" })
    },
    goReserve() {
      uni.navigateTo({ url: "/pages/reserve/reserve" })
    },
    goMy() {
      uni.navigateTo({ url: "/pages/my/my" })
    },
    goLostFound() {
      uni.navigateTo({ url: "/pages/lostfound/list" })
    },
    goNotifications() {
      uni.navigateTo({ url: "/pages/notifications/list" })
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
    },
    logout() {
      const s = uni.getStorageSync("session") || {}
      uni.request({
        url: `${BASE_URL}/auth/logout`,
        method: "POST",
        header: { "Content-Type": "application/json" },
        data: { refreshToken: s.refreshToken || "" },
        complete: () => {
          uni.removeStorageSync("session")
          uni.reLaunch({ url: "/pages/login/login" })
        }
      })
    }
  }
}
</script>

<style lang="scss">
.homePage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.2);
  background: linear-gradient(155deg, #ffffff 0%, #edf5ff 62%, #e6f0ff 100%);
}

.heroTop {
  align-items: flex-start;
}

.heroTitle {
  font-size: 22px;
  line-height: 30px;
  font-weight: 700;
  color: #0f172a;
}

.heroSub {
  margin-top: 4px;
  font-size: 12px;
  color: #475569;
}

.verifiedTag {
  min-width: 56px;
  height: 24px;
  line-height: 24px;
  text-align: center;
  border-radius: 999px;
  border: 1px solid #bfdbfe;
  color: #1d4ed8;
  background: #eff6ff;
  font-size: 11px;
  font-weight: 600;
  padding: 0 8px;
  box-sizing: border-box;
}

.heroMetaRow {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.heroMetaItem {
  height: 26px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.32);
  padding: 0 10px;
  background: rgba(255, 255, 255, 0.78);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #334155;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot.online {
  background: #16a34a;
  box-shadow: 0 0 0 4px rgba(22, 163, 74, 0.12);
}

.heroActionRow {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.heroBtn {
  flex: 1;
}

.overviewGrid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.overviewCard {
  min-height: 102px;
}

.overviewLabel {
  font-size: 12px;
  color: #64748b;
}

.overviewValue {
  margin-top: 4px;
  font-size: 24px;
  line-height: 1.15;
  font-weight: 700;
  color: #0f172a;
}

.overviewHint {
  margin-top: 4px;
  font-size: 11px;
  color: #94a3b8;
}

.featureGrid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.featureCard {
  position: relative;
  border: 1px solid rgba(148, 163, 184, 0.26);
  border-radius: 12px;
  background: #fff;
  padding: 10px;
  transition: transform 0.14s ease, box-shadow 0.14s ease;
}

.featureCard:active {
  transform: scale(0.985);
  box-shadow: 0 5px 14px rgba(15, 23, 42, 0.08);
}

.featureIcon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}

.featureIcon.tone-blue {
  color: #1d4ed8;
  background: #eaf3ff;
}

.featureIcon.tone-green {
  color: #15803d;
  background: #eafaf0;
}

.featureIcon.tone-amber {
  color: #b45309;
  background: #fff4dd;
}

.featureIcon.tone-violet {
  color: #6d28d9;
  background: #f3ebff;
}

.featureIcon.tone-teal {
  color: #0f766e;
  background: #e6fffb;
}

.featureBadge {
  min-width: 18px;
  height: 18px;
  line-height: 18px;
  border-radius: 999px;
  background: #ef4444;
  color: #fff;
  text-align: center;
  font-size: 10px;
  padding: 0 5px;
  box-sizing: border-box;
}

.featureName {
  margin-top: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.featureDesc {
  margin-top: 4px;
  font-size: 11px;
  color: #64748b;
  line-height: 16px;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  font-size: 12px;
  border-radius: 9px;
}

.loadingText {
  margin-top: 8px;
}

.compactEmpty {
  margin-top: 12px;
  padding: 16px 12px;
}

.activityList {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.activityItem {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 12px;
  background: #fff;
  padding: 10px;
}

.activityHead {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 6px;
}

.activityType {
  height: 18px;
  line-height: 18px;
  padding: 0 7px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
  background: #eaf3ff;
  color: #1d4ed8;
  flex-shrink: 0;
}

.activityType.lostfound {
  background: #fff7e6;
  color: #8a5a00;
}

.activityName {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activityRight {
  gap: 8px;
}

.activityMessage {
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

.activityTime {
  margin-top: 6px;
  font-size: 11px;
}

.redDot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #dc2626;
}

.fullBtn {
  width: 100%;
  margin-top: 10px;
}

.accountCard {
  border: 1px solid rgba(31, 77, 143, 0.1);
}

.logoutBtn {
  margin-top: 10px;
  width: 100%;
}
</style>
