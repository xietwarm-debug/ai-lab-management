<template>
  <view class="container repairAdminPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">报修工单管理</view>
            <view class="subtitle">提交-受理-处理-完成</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="loading" @click="fetchOrders">刷新</button>
        </view>
        <view class="heroMeta muted">当前账号：{{ operator || "-" }}</view>
        <view class="heroMeta muted">工单总数：{{ rows.length }}</view>
      </view>

      <view class="card">
        <view class="cardTitle">状态筛选</view>
        <view class="chipRow">
          <view
            v-for="opt in statusOptions"
            :key="opt.value"
            class="chip chipBtn"
            :class="{ chipOn: statusFilter === opt.value }"
            @click="setStatusFilter(opt.value)"
          >
            {{ opt.label }}
          </view>
        </view>
      </view>

      <view class="card loadingCard" v-if="loading">
        <view class="muted">正在加载工单...</view>
      </view>

      <view class="emptyState" v-else-if="rows.length === 0">
        <view class="emptyIcon">单</view>
        <view class="emptyTitle">暂无工单</view>
        <view class="emptySub">用户提交报修后会出现在这里</view>
      </view>

      <view class="stack" v-else>
        <view
          class="card orderItem"
          v-for="row in rows"
          :key="row.id"
          :id="`admin-repair-row-${row.id}`"
          :class="{ focusItem: isFocused(row) }"
        >
          <view class="rowBetween">
            <view class="orderNo">{{ row.orderNo || ("#" + row.id) }}</view>
            <view class="statusTag" :class="statusTone(row.status)">{{ statusText(row.status) }}</view>
          </view>
          <view class="orderMeta">实验室：{{ row.labName || "-" }}</view>
          <view class="orderMeta">设备：{{ row.equipmentName || row.assetCode || "未关联设备" }}</view>
          <view class="orderMeta">提交人：{{ row.submitterName || "-" }}</view>
          <view class="orderMeta">负责人：{{ row.assigneeName || "-" }}</view>
          <view class="orderMeta">提交时间：{{ row.submittedAt || "-" }}</view>
          <view class="orderMeta">处理时长：{{ totalMinutesText(row) }}</view>
          <view class="orderDesc lineClamp">{{ row.description || "-" }}</view>
          <view class="actionRow">
            <button
              v-if="row.status === 'submitted'"
              class="btnPrimary miniBtn"
              size="mini"
              :disabled="savingId === row.id"
              @click="updateStatus(row, 'accepted')"
            >
              受理
            </button>
            <button
              v-if="row.status === 'accepted'"
              class="btnPrimary miniBtn"
              size="mini"
              :disabled="savingId === row.id"
              @click="updateStatus(row, 'processing')"
            >
              开始处理
            </button>
            <button
              v-if="row.status === 'processing'"
              class="btnPrimary miniBtn"
              size="mini"
              :disabled="savingId === row.id"
              @click="updateStatus(row, 'completed')"
            >
              标记完成
            </button>
            <button class="btnSecondary miniBtn" size="mini" :disabled="savingId === row.id" @click="viewOrder(row)">
              刷新详情
            </button>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"

const STATUS_OPTIONS = [
  { label: "全部", value: "all" },
  { label: "已提交", value: "submitted" },
  { label: "已受理", value: "accepted" },
  { label: "处理中", value: "processing" },
  { label: "已完成", value: "completed" }
]

function toInt(value) {
  const n = Number(value)
  return Number.isFinite(n) ? Math.round(n) : 0
}

function parseListPayload(payload) {
  if (!payload || typeof payload !== "object") return []
  if (Array.isArray(payload.data)) return payload.data
  if (Array.isArray(payload)) return payload
  return []
}

function normalizeStatusFilter(rawStatus) {
  const status = String(rawStatus || "").trim().toLowerCase()
  const allow = new Set(["all", "submitted", "accepted", "processing", "completed"])
  return allow.has(status) ? status : "all"
}

export default {
  data() {
    return {
      operator: "",
      statusOptions: STATUS_OPTIONS,
      statusFilter: "all",
      focusOrderId: 0,
      rows: [],
      loading: false,
      savingId: 0
    }
  },
  onLoad(options) {
    const opts = options || {}
    const status = normalizeStatusFilter(opts.status)
    if (status !== "all") this.statusFilter = status
    this.focusOrderId = toInt(opts.focusId)
  },
  onShow() {
    if (!this.ensureAdmin()) return
    const session = uni.getStorageSync("session") || {}
    this.operator = String(session.username || "")
    this.fetchOrders()
  },
  methods: {
    isFocused(row) {
      return Number((row && row.id) || 0) === this.focusOrderId
    },
    ensureAdmin() {
      const s = uni.getStorageSync("session")
      if (!s || s.role !== "admin") {
        uni.showToast({ title: "无权限", icon: "none" })
        uni.reLaunch({ url: "/pages/login/login" })
        return false
      }
      return true
    },
    setStatusFilter(value) {
      this.statusFilter = value
      this.fetchOrders()
    },
    statusText(status) {
      if (status === "submitted") return "已提交"
      if (status === "accepted") return "已受理"
      if (status === "processing") return "处理中"
      if (status === "completed") return "已完成"
      return status || "-"
    },
    statusTone(status) {
      if (status === "submitted") return "warning"
      if (status === "accepted") return "info"
      if (status === "processing") return "info"
      if (status === "completed") return "success"
      return "info"
    },
    totalMinutesText(row) {
      const mins = toInt(row && row.durations ? row.durations.totalMinutes : 0)
      if (mins <= 0) return "-"
      if (mins < 60) return `${mins} 分钟`
      const h = Math.floor(mins / 60)
      const m = mins % 60
      return `${h} 小时 ${m} 分钟`
    },
    buildListUrl() {
      const parts = ["page=1", "pageSize=200"]
      if (this.statusFilter !== "all") {
        parts.push(`status=${encodeURIComponent(this.statusFilter)}`)
      }
      return `${BASE_URL}/repair-orders?${parts.join("&")}`
    },
    async fetchOrders() {
      if (this.loading) return
      this.loading = true
      try {
        const res = await uni.request({
          url: this.buildListUrl(),
          method: "GET"
        })
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "工单加载失败", icon: "none" })
          return
        }
        this.rows = parseListPayload(payload)
        this.scrollToFocusedRow()
      } catch (e) {
        this.rows = []
        uni.showToast({ title: "工单加载失败", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    scrollToFocusedRow() {
      if (!this.focusOrderId) return
      this.$nextTick(() => {
        uni.pageScrollTo({
          selector: `#admin-repair-row-${this.focusOrderId}`,
          duration: 220
        })
      })
    },
    async viewOrder(row) {
      if (!row || !row.id) return
      try {
        const res = await uni.request({
          url: `${BASE_URL}/repair-orders/${row.id}`,
          method: "GET"
        })
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          uni.showToast({ title: payload.msg || "加载详情失败", icon: "none" })
          return
        }
        const idx = this.rows.findIndex((x) => Number(x.id) === Number(row.id))
        if (idx >= 0) {
          this.$set(this.rows, idx, payload.data)
        }
      } catch (e) {
        uni.showToast({ title: "加载详情失败", icon: "none" })
      }
    },
    async updateStatus(row, status) {
      if (!row || !row.id || !status || this.savingId) return
      this.savingId = Number(row.id || 0)
      try {
        const res = await uni.request({
          url: `${BASE_URL}/repair-orders/${row.id}/status`,
          method: "POST",
          header: { "Content-Type": "application/json" },
          data: {
            status,
            assigneeName: this.operator || ""
          }
        })
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "状态更新失败", icon: "none" })
          return
        }
        await this.fetchOrders()
        uni.showToast({ title: "状态已更新", icon: "success" })
      } catch (e) {
        uni.showToast({ title: "状态更新失败", icon: "none" })
      } finally {
        this.savingId = 0
      }
    }
  }
}
</script>

<style lang="scss">
.repairAdminPage {
  padding-bottom: 24px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.18);
  background: linear-gradient(160deg, #ffffff 0%, #f2f7ff 100%);
}

.heroTop {
  align-items: flex-start;
}

.heroMeta {
  margin-top: 6px;
}

.chipRow {
  margin-top: 8px;
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

.loadingCard {
  min-height: 72px;
  display: flex;
  align-items: center;
}

.orderItem {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.orderItem.focusItem {
  border-color: #1d4ed8;
  box-shadow: 0 0 0 2px rgba(29, 78, 216, 0.14);
}

.orderNo {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.orderMeta {
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
}

.orderDesc {
  margin-top: 8px;
  font-size: 12px;
  line-height: 18px;
  color: #475569;
}

.lineClamp {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.actionRow {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}
</style>
