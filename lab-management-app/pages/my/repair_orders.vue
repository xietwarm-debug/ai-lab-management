<template>
  <view class="container myRepairPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">我的报修工单</view>
            <view class="subtitle">查看处理进度并提交回访</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="loading" @click="fetchOrders">刷新</button>
        </view>
        <view class="heroMeta muted">共 {{ rows.length }} 条</view>
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
        <view class="emptySub">提交报修后可在这里查看处理进度</view>
      </view>

      <view class="stack" v-else>
        <view
          class="card orderItem"
          v-for="row in rows"
          :key="row.id"
          :id="`repair-row-${row.id}`"
          :class="{ focusItem: isFocused(row) }"
        >
          <view class="rowBetween">
            <view class="orderNo">{{ row.orderNo || ("#" + row.id) }}</view>
            <view class="statusTag" :class="statusTone(row.status)">{{ statusText(row.status) }}</view>
          </view>
          <view class="orderMeta">实验室：{{ row.labName || "-" }}</view>
          <view class="orderMeta">设备：{{ row.equipmentName || row.assetCode || "未关联设备" }}</view>
          <view class="orderMeta">问题类型：{{ issueTypeText(row.issueType) }}</view>
          <view class="orderMeta">提交时间：{{ row.submittedAt || "-" }}</view>
          <view class="orderMeta">处理时长：{{ totalMinutesText(row) }}</view>
          <view class="orderDesc lineClamp">{{ row.description || "-" }}</view>
          <view class="orderMeta" v-if="row.followupAt">
            回访：{{ row.followupScore || "-" }} 星 {{ row.followupComment || "" }}
          </view>
          <view class="actionRow">
            <button
              v-if="row.status === 'completed'"
              class="btnPrimary miniBtn"
              size="mini"
              @click="openFollowup(row)"
            >
              {{ row.followupAt ? "修改回访" : "提交回访" }}
            </button>
          </view>
        </view>
      </view>

      <view class="modalMask" v-if="followupVisible" @click="closeFollowup" />
      <view class="card modalPanel" v-if="followupVisible">
        <view class="rowBetween">
          <view class="cardTitle">工单回访</view>
          <button class="btnSecondary miniBtn" size="mini" @click="closeFollowup">取消</button>
        </view>
        <view class="label">评分</view>
        <view class="scoreRow">
          <view
            v-for="item in scoreOptions"
            :key="item"
            class="chip scoreChip"
            :class="{ chipOn: followupForm.score === item }"
            @click="followupForm.score = item"
          >
            {{ item }} 星
          </view>
        </view>
        <view class="label">回访内容</view>
        <textarea
          class="textareaBase"
          v-model.trim="followupForm.comment"
          maxlength="500"
          placeholder="可选：填写处理满意度与建议"
        />
        <button class="btnPrimary submitBtn" :disabled="followupSaving" @click="submitFollowup">
          {{ followupSaving ? "提交中..." : "提交回访" }}
        </button>
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

function parseListPayload(payload) {
  if (!payload || typeof payload !== "object") return []
  if (Array.isArray(payload.data)) return payload.data
  if (Array.isArray(payload)) return payload
  return []
}

function toInt(value) {
  const n = Number(value)
  return Number.isFinite(n) ? Math.round(n) : 0
}

function normalizeStatusFilter(rawStatus) {
  const status = String(rawStatus || "").trim().toLowerCase()
  const allow = new Set(["all", "submitted", "accepted", "processing", "completed"])
  return allow.has(status) ? status : "all"
}

export default {
  data() {
    return {
      statusOptions: STATUS_OPTIONS,
      statusFilter: "all",
      focusOrderId: 0,
      rows: [],
      loading: false,
      followupVisible: false,
      followupSaving: false,
      followupOrderId: 0,
      followupForm: {
        score: 5,
        comment: ""
      },
      scoreOptions: [5, 4, 3, 2, 1]
    }
  },
  onLoad(options) {
    const opts = options || {}
    const status = normalizeStatusFilter(opts.status)
    if (status !== "all") this.statusFilter = status
    this.focusOrderId = toInt(opts.focusId)
  },
  onShow() {
    const s = uni.getStorageSync("session")
    if (!s || !s.username) {
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    this.fetchOrders()
  },
  methods: {
    isFocused(row) {
      return Number((row && row.id) || 0) === this.focusOrderId
    },
    setStatusFilter(value) {
      this.statusFilter = value
      this.fetchOrders()
    },
    issueTypeText(type) {
      if (type === "computer") return "电脑问题"
      if (type === "lighting") return "电灯问题"
      if (type === "floor") return "地板问题"
      if (type === "network") return "网络问题"
      return "其他问题"
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
      const parts = ["page=1", "pageSize=200", "mine=1"]
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
          selector: `#repair-row-${this.focusOrderId}`,
          duration: 220
        })
      })
    },
    openFollowup(row) {
      if (!row || !row.id || row.status !== "completed") return
      this.followupOrderId = Number(row.id || 0)
      this.followupForm = {
        score: Number(row.followupScore || 5) || 5,
        comment: String(row.followupComment || "")
      }
      this.followupVisible = true
    },
    closeFollowup() {
      this.followupVisible = false
      this.followupSaving = false
      this.followupOrderId = 0
    },
    async submitFollowup() {
      if (this.followupSaving) return
      if (!this.followupOrderId) return
      const score = Number(this.followupForm.score || 0)
      if (!score || score < 1 || score > 5) {
        uni.showToast({ title: "请选择评分", icon: "none" })
        return
      }
      this.followupSaving = true
      try {
        const res = await uni.request({
          url: `${BASE_URL}/repair-orders/${this.followupOrderId}/followup`,
          method: "POST",
          header: { "Content-Type": "application/json" },
          data: {
            score,
            comment: String(this.followupForm.comment || "").trim()
          }
        })
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "回访提交失败", icon: "none" })
          return
        }
        this.closeFollowup()
        await this.fetchOrders()
        uni.showToast({ title: "回访已提交", icon: "success" })
      } catch (e) {
        uni.showToast({ title: "回访提交失败", icon: "none" })
      } finally {
        this.followupSaving = false
      }
    }
  }
}
</script>

<style lang="scss">
.myRepairPage {
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
}

.scoreRow {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.scoreChip {
  transition: all 0.14s ease;
}

.modalMask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.36);
  z-index: 990;
}

.modalPanel {
  position: fixed;
  left: 10px;
  right: 10px;
  bottom: 14px;
  max-height: 80vh;
  overflow-y: auto;
  z-index: 991;
}

.submitBtn {
  width: 100%;
  margin-top: 10px;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}
</style>
