<template>
  <view class="container notifyPage" :class="themeClass">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">通知中心</view>
            <view class="subtitle">预约、借用、报修、报警、失物与作业提醒动态</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" @click="fetchList">刷新</button>
        </view>
        <view class="heroMetaRow">
          <view class="heroMetaItem">未读总数 {{ unreadTotal }}</view>
          <view class="heroMetaItem">预约 {{ unreadReservation }}</view>
          <view class="heroMetaItem">借用 {{ unreadAssetBorrow }}</view>
          <view class="heroMetaItem">报修 {{ unreadRepair }}</view>
          <view class="heroMetaItem">报警 {{ unreadAlarm }}</view>
          <view class="heroMetaItem">失物 {{ unreadLostfound }}</view>
          <view class="heroMetaItem">作业 {{ unreadCourseTask }}</view>
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
            <text v-if="item.value === 'asset_borrow' && unreadAssetBorrow > 0">({{ unreadAssetBorrow }})</text>
            <text v-if="item.value === 'repair' && unreadRepair > 0">({{ unreadRepair }})</text>
            <text v-if="item.value === 'sensor_alarm' && unreadAlarm > 0">({{ unreadAlarm }})</text>
            <text v-if="item.value === 'lostfound' && unreadLostfound > 0">({{ unreadLostfound }})</text>
            <text v-if="item.value === 'course_task' && unreadCourseTask > 0">({{ unreadCourseTask }})</text>
          </view>
        </view>

        <view class="muted summaryText">当前筛选共 {{ shown.length }} 条</view>
      </view>

      <view class="card loadingCard" v-if="loading">
        <view class="muted">正在加载通知...</view>
      </view>

      <view class="stack" v-else-if="shown.length > 0">
        <view
          class="card noticeItem"
          v-for="n in shown"
          :key="n.id || n.createdAt"
          :class="{ unread: isUnread(n) }"
          @click="openNotice(n)"
        >
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
          <view class="rowBetween noticeFoot">
            <view class="muted noticeTime">{{ n.createdAt || '-' }}</view>
            <view class="muted noticeJumpHint">点击查看</view>
          </view>
        </view>
      </view>

      <view class="emptyState" v-else>
        <view class="emptyIcon">信</view>
        <view class="emptyTitle">暂无通知</view>
        <view class="emptySub">预约、借用、报修、失物和作业相关消息会在这里展示</view>
      </view>
    </view>
  </view>
</template>

<script>
import {
  applyNotificationTabBadge,
  buildNotificationReadPatchForRow,
  fetchNotificationRows,
  fetchNotificationReadState,
  loadNotificationReadStateFromStorage,
  mergeNotificationReadState,
  persistNotificationReadStateToStorage,
  updateNotificationReadStatePatch
} from "@/common/notifications.js"
import { themePageMixin } from "@/common/theme.js"

function sortByCreatedAtDesc(rows) {
  return rows
    .slice()
    .sort((a, b) => String(b.createdAt || "").localeCompare(String(a.createdAt || "")))
}

function toPositiveInt(rawValue) {
  const n = Number(rawValue)
  if (!Number.isFinite(n)) return 0
  const rounded = Math.trunc(n)
  return rounded > 0 ? rounded : 0
}

function parseNoticeEntityId(notice) {
  const noticeId = String((notice && notice.id) || "").trim()
  if (!noticeId) return 0

  const reservationMatched = noticeId.match(/^reservation-(\d+)$/)
  if (reservationMatched) return toPositiveInt(reservationMatched[1])

  const repairMatched = noticeId.match(/^repair-(\d+)$/)
  if (repairMatched) return toPositiveInt(repairMatched[1])

  const lostfoundMatched = noticeId.match(/^lostfound-(?:owner|claimant)-(\d+)-/)
  if (lostfoundMatched) return toPositiveInt(lostfoundMatched[1])

  const sensorMatched = noticeId.match(/^sensor-alarm-(\d+)$/)
  if (sensorMatched) return toPositiveInt(sensorMatched[1])

  const borrowRequestMatched = noticeId.match(/^borrow-request-(\d+)-/)
  if (borrowRequestMatched) return toPositiveInt(borrowRequestMatched[1])

  const borrowRemindMatched = noticeId.match(/^borrow-remind-(\d+)-/)
  if (borrowRemindMatched) return toPositiveInt(borrowRemindMatched[1])
  return 0
}

export default {
  mixins: [themePageMixin],
  data() {
    return {
      list: [],
      user: "",
      typeFilter: "all",
      lastReadReservation: "",
      lastReadAssetBorrow: "",
      lastReadRepair: "",
      lastReadAlarm: "",
      lastReadLostfound: "",
      lastReadCourseTask: "",
      loading: false,
      typeOptions: [
        { label: "全部", value: "all" },
        { label: "预约", value: "reservation" },
        { label: "借用", value: "asset_borrow" },
        { label: "报修", value: "repair" },
        { label: "报警", value: "sensor_alarm" },
        { label: "失物", value: "lostfound" },
        { label: "作业", value: "course_task" }
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
    unreadAssetBorrow() {
      return this.sortedList.filter((n) => n.type === "asset_borrow" && this.isUnread(n)).length
    },
    unreadRepair() {
      return this.sortedList.filter((n) => n.type === "repair" && this.isUnread(n)).length
    },
    unreadAlarm() {
      return this.sortedList.filter((n) => n.type === "sensor_alarm" && this.isUnread(n)).length
    },
    unreadLostfound() {
      return this.sortedList.filter((n) => n.type === "lostfound" && this.isUnread(n)).length
    },
    unreadCourseTask() {
      return this.sortedList.filter((n) => n.type === "course_task" && this.isUnread(n)).length
    },
    unreadTotal() {
      return (
        this.unreadReservation +
        this.unreadAssetBorrow +
        this.unreadRepair +
        this.unreadAlarm +
        this.unreadLostfound +
        this.unreadCourseTask
      )
    }
  },
  watch: {
    unreadTotal(value) {
      applyNotificationTabBadge(value)
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

    this.loadReadStateFromLocal()
    this.fetchList()
  },
  methods: {
    currentReadState() {
      return {
        reservation: this.lastReadReservation,
        asset_borrow: this.lastReadAssetBorrow,
        repair: this.lastReadRepair,
        sensor_alarm: this.lastReadAlarm,
        lostfound: this.lastReadLostfound,
        course_task: this.lastReadCourseTask
      }
    },
    loadReadStateFromLocal() {
      this.applyReadState(loadNotificationReadStateFromStorage(this.user, this.currentReadState()))
    },
    persistReadStateToLocal() {
      persistNotificationReadStateToStorage(this.user, this.currentReadState())
    },
    applyReadState(rawState) {
      const normalized = mergeNotificationReadState(this.currentReadState(), rawState)
      this.lastReadReservation = normalized.reservation
      this.lastReadAssetBorrow = normalized.asset_borrow
      this.lastReadRepair = normalized.repair
      this.lastReadAlarm = normalized.sensor_alarm
      this.lastReadLostfound = normalized.lostfound
      this.lastReadCourseTask = normalized.course_task
      this.persistReadStateToLocal()
    },
    async fetchReadState() {
      try {
        const state = await fetchNotificationReadState(this.currentReadState())
        this.applyReadState(state)
      } catch (e) {}
    },
    setTypeFilter(type) {
      this.typeFilter = type
    },
    async fetchList() {
      this.loading = true
      try {
        const [, noticeResult] = await Promise.all([
          this.fetchReadState(),
          fetchNotificationRows(this.user, { retries: 1, maxAgeMs: 60 * 1000 })
        ])
        this.list = Array.isArray(noticeResult && noticeResult.rows) ? noticeResult.rows : []
        if (noticeResult && noticeResult.stale) {
          uni.showToast({ title: "当前显示缓存通知", icon: "none" })
        }
      } catch (e) {
        this.list = []
        uni.showToast({ title: "获取通知失败", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    isUnread(row) {
      if (row.type === "reservation") {
        if (!this.lastReadReservation) return true
        return (row.createdAt || "") > this.lastReadReservation
      }
      if (row.type === "asset_borrow") {
        if (!this.lastReadAssetBorrow) return true
        return (row.createdAt || "") > this.lastReadAssetBorrow
      }
      if (row.type === "repair") {
        if (!this.lastReadRepair) return true
        return (row.createdAt || "") > this.lastReadRepair
      }
      if (row.type === "sensor_alarm") {
        if (!this.lastReadAlarm) return true
        return (row.createdAt || "") > this.lastReadAlarm
      }
      if (row.type === "lostfound") {
        if (!this.lastReadLostfound) return true
        return (row.createdAt || "") > this.lastReadLostfound
      }
      if (row.type === "course_task") {
        if (!this.lastReadCourseTask) return true
        return (row.createdAt || "") > this.lastReadCourseTask
      }
      return false
    },
    latestByType(type) {
      const row = this.sortedList.find((x) => x.type === type)
      return row ? row.createdAt || "" : ""
    },
    currentReadPatch() {
      const patch = {}
      const collectTypes =
        this.typeFilter === "all"
          ? ["reservation", "asset_borrow", "repair", "sensor_alarm", "lostfound", "course_task"]
          : [this.typeFilter]

      collectTypes.forEach((type) => {
        const latest = this.latestByType(type)
        if (latest) patch[type] = latest
      })
      return patch
    },
    async markCurrentRead() {
      if (!this.user) return
      const patch = this.currentReadPatch()
      const patchKeys = Object.keys(patch)
      if (patchKeys.length === 0) {
        uni.showToast({ title: "当前没有可标记消息", icon: "none" })
        return
      }

      try {
        const state = await updateNotificationReadStatePatch(patch, this.currentReadState())
        this.applyReadState(state)
        uni.showToast({ title: "已标记已读", icon: "success" })
      } catch (e) {
        uni.showToast({ title: "标记失败", icon: "none" })
      }
    },
    markNoticeRead(notice) {
      const patch = buildNotificationReadPatchForRow(notice)
      if (!Object.keys(patch).length) return

      const optimisticState = mergeNotificationReadState(this.currentReadState(), patch)
      this.applyReadState(optimisticState)
      updateNotificationReadStatePatch(patch, optimisticState)
        .then((state) => {
          this.applyReadState(state)
        })
        .catch(() => {})
    },
    openNotice(row) {
      const notice = row || {}
      const noticeType = String(notice.type || "").trim()
      const noticeStatus = String(notice.status || "").trim()
      const labName = String(notice.labName || "").trim()
      const entityId = parseNoticeEntityId(notice)
      const session = uni.getStorageSync("session") || {}
      const role = String(session.role || "").trim()

      this.markNoticeRead(notice)

      if (noticeType === "reservation") {
        if (role === "admin" && entityId > 0) {
          uni.navigateTo({ url: `/pages/admin/approve-detail?id=${entityId}` })
          return
        }
        const q = []
        if (entityId > 0) q.push(`focusId=${entityId}`)
        if (noticeStatus) q.push(`status=${encodeURIComponent(noticeStatus)}`)
        const qs = q.length ? `?${q.join("&")}` : ""
        uni.navigateTo({ url: `/pages/my/reservations${qs}` })
        return
      }

      if (noticeType === "repair") {
        const q = []
        if (entityId > 0) q.push(`focusId=${entityId}`)
        if (noticeStatus) q.push(`status=${encodeURIComponent(noticeStatus)}`)
        const qs = q.length ? `?${q.join("&")}` : ""
        const target = role === "admin" ? "/pages/admin/repair_orders" : "/pages/my/repair_orders"
        uni.navigateTo({ url: `${target}${qs}` })
        return
      }

      if (noticeType === "lostfound") {
        const q = []
        if (entityId > 0) q.push(`focusId=${entityId}`)
        if (noticeStatus) q.push(`noticeStatus=${encodeURIComponent(noticeStatus)}`)
        const qs = q.length ? `?${q.join("&")}` : ""
        const target = role === "admin" ? "/pages/admin/lostfound" : "/pages/lostfound/list"
        uni.navigateTo({ url: `${target}${qs}` })
        return
      }

      if (noticeType === "sensor_alarm") {
        const q = []
        if (labName) q.push(`keyword=${encodeURIComponent(labName)}`)
        const qs = q.length ? `?${q.join("&")}` : ""
        uni.navigateTo({ url: `/pages/admin/labs${qs}` })
        return
      }

      if (noticeType === "asset_borrow") {
        const q = []
        if (entityId > 0) q.push(`focusId=${entityId}`)
        if (role === "admin") {
          const adminStatusMap = {
            pending: "pending",
            approved: "approved",
            overdue: "overdue",
            returned: "returned",
            rejected: "rejected",
            cancelled: "cancelled",
            reminder: "approved"
          }
          const status = adminStatusMap[noticeStatus] || ""
          if (status) q.push(`status=${encodeURIComponent(status)}`)
          const qs = q.length ? `?${q.join("&")}` : ""
          uni.navigateTo({ url: `/pages/admin/borrow_approval${qs}` })
          return
        }
        const userStatusMap = {
          pending: "pending",
          approved: "approved",
          overdue: "overdue",
          returned: "returned",
          rejected: "rejected",
          cancelled: "cancelled",
          reminder: "approved"
        }
        const status = userStatusMap[noticeStatus] || ""
        if (status) q.push(`status=${encodeURIComponent(status)}`)
        const qs = q.length ? `?${q.join("&")}` : ""
        uni.navigateTo({ url: `/pages/my/borrowings${qs}` })
        return
      }

      if (noticeType === "course_task") {
        const courseId = Number(notice.courseId || 0)
        if (courseId > 0) {
          uni.navigateTo({ url: `/pages/teacher/course_detail?courseId=${courseId}` })
          return
        }
      }

      uni.showToast({ title: "暂无可跳转页面", icon: "none" })
    },
    typeText(type) {
      if (type === "asset_borrow") return "借用"
      if (type === "course_task") return "作业"
      if (type === "sensor_alarm") return "报警"
      if (type === "lostfound") return "失物"
      if (type === "repair") return "报修"
      return "预约"
    },
    statusTone(status) {
      if (status === "alarm") return "danger"
      if (status === "warning") return "warning"
      if (status === "overdue") return "danger"
      if (status === "reminder") return "warning"
      if (status === "approved" || status === "closed" || status === "claim_approved") return "success"
      if (status === "pending" || status === "open" || status === "claim_pending" || status === "submitted" || status === "course_pending") return "warning"
      if (status === "accepted" || status === "processing") return "info"
      if (status === "completed") return "success"
      if (status === "rejected" || status === "cancelled" || status === "claim_rejected") return "danger"
      return "info"
    },
    statusText(status) {
      if (status === "pending") return "待审批"
      if (status === "approved") return "已通过"
      if (status === "overdue") return "逾期未还"
      if (status === "returned") return "已归还"
      if (status === "reminder") return "归还提醒"
      if (status === "rejected") return "已驳回"
      if (status === "cancelled") return "已取消"
      if (status === "open") return "处理中"
      if (status === "closed") return "已处理"
      if (status === "submitted") return "已提交"
      if (status === "accepted") return "已受理"
      if (status === "processing") return "处理中"
      if (status === "completed") return "已完成"
      if (status === "warning") return "预警"
      if (status === "alarm") return "报警"
      if (status === "course_pending") return "待提交"
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
  border: 1px solid var(--color-border-focus);
  background: var(--color-bg-soft);
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
  border: 1px solid var(--color-border-primary);
  background: var(--color-bg-card);
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  font-size: 11px;
  color: var(--color-text-secondary);
}

.toolbarCard {
  border: 1px solid var(--color-border-primary);
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
  border-color: var(--color-border-focus);
  background: var(--color-info-soft);
  color: var(--info);
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
  border: 1px solid var(--color-border-primary);
}

.noticeItem.unread {
  border-color: var(--danger);
  box-shadow: var(--shadow-sm);
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
  color: var(--color-text-primary);
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
  background: var(--color-info-soft);
  color: var(--info);
  flex-shrink: 0;
}

.typeTag.lostfound {
  background: var(--color-warning-soft);
  color: var(--warning);
}

.typeTag.repair {
  background: #fff1f2;
  color: #be123c;
}

.typeTag.sensor_alarm {
  background: #fee2e2;
  color: #b91c1c;
}

.typeTag.course_task {
  background: #ecfeff;
  color: #0f766e;
}

.typeTag.asset_borrow {
  background: #effff1;
  color: #166534;
}

.noticeRight {
  gap: 8px;
}

.noticeMessage {
  margin-top: 6px;
  color: var(--color-text-secondary);
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

.noticeFoot {
  margin-top: 6px;
}

.noticeJumpHint {
  font-size: 11px;
}

.redDot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--danger);
}
</style>
