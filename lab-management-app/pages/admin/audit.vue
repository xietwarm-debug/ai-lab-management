<template>
  <view class="container">
    <view class="stack">
      <view>
        <view class="title">审计日志</view>
        <view class="subtitle">按动作、操作者、目标类型筛选关键操作</view>
      </view>

      <view class="card filter">
        <view class="row">
          <picker mode="selector" :range="actionOptions" range-key="label" :value="actionIndex" @change="onActionChange">
            <view class="pickerBox">
              <text class="pickerLabel">动作：</text>
              <text>{{ currentActionLabel }}</text>
            </view>
          </picker>
        </view>
        <view class="row">
          <input
            class="input"
            v-model.trim="filters.operator"
            placeholder="操作者用户名，如：admin1"
          />
        </view>
        <view class="row dateRow">
          <picker mode="date" :value="filters.startDate" @change="onStartDateChange">
            <view class="pickerBox">
              <text class="pickerLabel">开始日期：</text>
              <text>{{ filters.startDate || "不限" }}</text>
            </view>
          </picker>
          <picker mode="date" :value="filters.endDate" @change="onEndDateChange">
            <view class="pickerBox">
              <text class="pickerLabel">结束日期：</text>
              <text>{{ filters.endDate || "不限" }}</text>
            </view>
          </picker>
        </view>
        <view class="row chips">
          <view
            class="chipItem"
            :class="{ on: filters.targetType === item.value }"
            v-for="item in targetTypes"
            :key="item.value || 'all'"
            @click="filters.targetType = item.value"
          >{{ item.label }}</view>
        </view>
        <view class="row chips">
          <view
            class="chipItem"
            :class="{ on: pageSize === item }"
            v-for="item in [20, 50, 100]"
            :key="item"
            @click="pageSize = item"
          >每页 {{ item }} 条</view>
        </view>
        <view class="actions">
          <button class="btnGhost" size="mini" @click="resetFilters">重置</button>
          <button class="btnPrimary" size="mini" @click="queryLogs">查询</button>
          <button class="btnGhost" size="mini" @click="exportCsv">导出</button>
        </view>
      </view>

      <view class="card tips rowBetween">
        <view class="muted">已加载 {{ list.length }} / {{ total || 0 }} 条</view>
        <view class="muted" v-if="lastUpdated">更新于 {{ lastUpdated }}</view>
      </view>

      <view class="card empty" v-if="loading">加载中...</view>

      <view class="card item" :class="{ warnItem: isRiskyAction(row.action) }" v-for="row in list" :key="row.id">
        <view class="rowBetween">
          <view class="actionBlock">
            <view class="action">{{ actionText(row.action) }}</view>
            <view class="riskTag" v-if="isRiskyAction(row.action)">重点</view>
          </view>
          <view class="time">{{ row.createdAt }}</view>
        </view>
        <view class="meta">
          操作人：{{ row.operatorName || "-" }}
          <text v-if="row.operatorRole">（{{ row.operatorRole }}）</text>
          · IP：{{ row.ip || "-" }}
        </view>
        <view class="meta">目标：{{ row.targetType || "-" }} / {{ row.targetId || "-" }}</view>
        <view class="detail" v-if="hasDetail(row.detail)">{{ detailText(row.detail) }}</view>
      </view>

      <view class="card loadCard" v-if="!loading && list.length > 0">
        <button class="btnGhost" size="mini" :disabled="!hasMore || loadingMore" @click="fetchMore">
          {{ loadMoreText }}
        </button>
      </view>

      <view class="empty" v-if="!loading && list.length === 0">暂无日志</view>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"

function nowText() {
  const d = new Date()
  const p = (n) => (n < 10 ? `0${n}` : `${n}`)
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

export default {
  data() {
    return {
      loading: false,
      loadingMore: false,
      lastUpdated: "",
      page: 1,
      pageSize: 50,
      total: 0,
      hasMore: false,
      list: [],
      filters: {
        action: "",
        operator: "",
        targetType: "",
        startDate: "",
        endDate: ""
      },
      targetTypes: [
        { label: "全部类型", value: "" },
        { label: "预约", value: "reservation" },
        { label: "用户", value: "user" },
        { label: "实验室", value: "lab" },
        { label: "失物", value: "lostfound" },
        { label: "认证", value: "auth" }
      ],
      actionOptions: [
        { label: "全部动作", value: "" },
        { label: "用户升权", value: "admin.user.promote" },
        { label: "用户降权", value: "admin.user.demote" },
        { label: "实验室更新", value: "admin.lab.update" },
        { label: "失物状态变更", value: "admin.lostfound.status" },
        { label: "预约通过", value: "admin.reservation.approve" },
        { label: "预约驳回", value: "admin.reservation.reject" },
        { label: "预约备注", value: "admin.reservation.note" },
        { label: "预约取消", value: "admin.reservation.cancel" },
        { label: "预约改期", value: "admin.reservation.reschedule" },
        { label: "批量通过", value: "admin.reservation.batch_approve" },
        { label: "批量取消", value: "admin.reservation.batch_cancel" },
        { label: "登录成功", value: "auth.login.success" },
        { label: "登录失败", value: "auth.login.failed" },
        { label: "注册成功", value: "auth.register.success" },
        { label: "注册失败", value: "auth.register.failed" },
        { label: "刷新成功", value: "auth.refresh.success" },
        { label: "刷新失败", value: "auth.refresh.failed" },
        { label: "改密成功", value: "auth.change_password.success" },
        { label: "改密失败", value: "auth.change_password.failed" }
      ]
    }
  },
  computed: {
    actionIndex() {
      const idx = this.actionOptions.findIndex((x) => x.value === this.filters.action)
      return idx >= 0 ? idx : 0
    },
    currentActionLabel() {
      const row = this.actionOptions[this.actionIndex]
      return row ? row.label : "全部动作"
    },
    loadMoreText() {
      if (this.loadingMore) return "加载中..."
      if (this.hasMore) return "加载更多"
      return "已加载全部"
    }
  },
  onShow() {
    const s = uni.getStorageSync("session")
    if (!s || s.role !== "admin") {
      uni.showToast({ title: "无权限", icon: "none" })
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    this.queryLogs()
  },
  onPullDownRefresh() {
    this.queryLogs()
  },
  onReachBottom() {
    this.fetchMore()
  },
  methods: {
    actionText(action) {
      const map = {
        "admin.user.promote": "用户升权",
        "admin.user.demote": "用户降权",
        "admin.lab.update": "实验室更新",
        "admin.lostfound.status": "失物状态变更",
        "admin.reservation.approve": "预约通过",
        "admin.reservation.reject": "预约驳回",
        "admin.reservation.note": "预约备注",
        "admin.reservation.cancel": "预约取消",
        "admin.reservation.reschedule": "预约改期",
        "admin.reservation.batch_approve": "批量通过",
        "admin.reservation.batch_cancel": "批量取消",
        "auth.login.success": "登录成功",
        "auth.login.failed": "登录失败",
        "auth.register.success": "注册成功",
        "auth.register.failed": "注册失败",
        "auth.refresh.success": "刷新成功",
        "auth.refresh.failed": "刷新失败",
        "auth.change_password.success": "修改密码成功",
        "auth.change_password.failed": "修改密码失败"
      }
      return map[action] || action || "-"
    },
    isRiskyAction(action) {
      return (
        action === "admin.reservation.batch_cancel" ||
        action === "admin.reservation.cancel" ||
        action === "admin.reservation.reject" ||
        /\.failed$/.test(action || "")
      )
    },
    hasDetail(detail) {
      return detail && typeof detail === "object" && Object.keys(detail).length > 0
    },
    detailText(detail) {
      try {
        return JSON.stringify(detail, null, 2)
      } catch (e) {
        return ""
      }
    },
    onActionChange(e) {
      const i = Number(e.detail.value || 0)
      const row = this.actionOptions[i] || this.actionOptions[0]
      this.filters.action = row.value
    },
    onStartDateChange(e) {
      this.filters.startDate = e.detail.value || ""
    },
    onEndDateChange(e) {
      this.filters.endDate = e.detail.value || ""
    },
    validateRange() {
      const start = this.filters.startDate
      const end = this.filters.endDate
      if (start && end && start > end) {
        uni.showToast({ title: "开始日期不能大于结束日期", icon: "none" })
        return false
      }
      return true
    },
    buildQuery({ page = 1, pageSize = 50, forExport = false } = {}) {
      const parts = []
      if (forExport) {
        const estimated = this.total > 0 ? this.total : 2000
        const exportLimit = Math.min(Math.max(estimated, 200), 5000)
        parts.push(`limit=${exportLimit}`)
      } else {
        parts.push(`page=${page}`)
        parts.push(`pageSize=${pageSize}`)
      }
      if (this.filters.action) {
        parts.push(`action=${encodeURIComponent(this.filters.action)}`)
      }
      if (this.filters.operator) {
        parts.push(`operator=${encodeURIComponent(this.filters.operator)}`)
      }
      if (this.filters.targetType) {
        parts.push(`targetType=${encodeURIComponent(this.filters.targetType)}`)
      }
      if (this.filters.startDate) {
        parts.push(`startDate=${encodeURIComponent(this.filters.startDate)}`)
      }
      if (this.filters.endDate) {
        parts.push(`endDate=${encodeURIComponent(this.filters.endDate)}`)
      }
      return parts.join("&")
    },
    resetFilters() {
      this.filters.action = ""
      this.filters.operator = ""
      this.filters.targetType = ""
      this.filters.startDate = ""
      this.filters.endDate = ""
      this.pageSize = 50
      this.queryLogs()
    },
    queryLogs() {
      this.page = 1
      this.total = 0
      this.hasMore = false
      this.list = []
      this.fetchLogs({ reset: true })
    },
    fetchLogs({ reset = false } = {}) {
      if (!this.validateRange()) {
        uni.stopPullDownRefresh()
        return
      }
      if (reset) {
        if (this.loading) return
        this.loading = true
      } else {
        if (this.loading || this.loadingMore || !this.hasMore) return
        this.loadingMore = true
      }

      const requestPage = reset ? 1 : this.page
      uni.request({
        url: `${BASE_URL}/audit-logs?${this.buildQuery({ page: requestPage, pageSize: this.pageSize })}`,
        method: "GET",
        success: (res) => {
          const payload = res.data || {}
          if (!payload.ok) {
            if (reset) this.list = []
            uni.showToast({ title: payload.msg || "获取失败", icon: "none" })
            return
          }

          const rows = Array.isArray(payload.data) ? payload.data : []
          const meta = payload.meta || {}
          const total = Number(meta.total || 0)
          const hasMore = typeof meta.hasMore === "boolean" ? meta.hasMore : rows.length >= this.pageSize

          if (reset) {
            this.list = rows
          } else {
            this.list = this.list.concat(rows)
          }

          this.total = total || this.list.length
          this.hasMore = hasMore
          this.page = requestPage + 1
          this.lastUpdated = nowText()
        },
        fail: () => {
          if (reset) this.list = []
          uni.showToast({ title: "获取失败", icon: "none" })
        },
        complete: () => {
          this.loading = false
          this.loadingMore = false
          uni.stopPullDownRefresh()
        }
      })
    },
    fetchMore() {
      this.fetchLogs({ reset: false })
    },
    exportCsv() {
      if (!this.validateRange()) return
      const qs = this.buildQuery({ forExport: true })
      uni.downloadFile({
        url: `${BASE_URL}/audit-logs/export?${qs}`,
        method: "GET",
        success: (res) => {
          if (res.statusCode !== 200) {
            uni.showToast({ title: "导出失败", icon: "none" })
            return
          }
          uni.openDocument({
            filePath: res.tempFilePath,
            fileType: "csv",
            fail: () => uni.showToast({ title: "导出成功，请在文件中查看", icon: "none" })
          })
        },
        fail: () => uni.showToast({ title: "导出失败", icon: "none" })
      })
    }
  }
}
</script>

<style>
.filter {
  border: 1px solid rgba(31, 77, 143, 0.08);
}
.row {
  margin-bottom: 8px;
}
.input {
  width: 100%;
  min-height: 36px;
  box-sizing: border-box;
  border: 1px solid #d7e0ea;
  border-radius: 10px;
  padding: 8px 10px;
  background: #fff;
  font-size: 13px;
}
.pickerBox {
  min-height: 36px;
  display: flex;
  align-items: center;
  padding: 8px 10px;
  border: 1px solid #d7e0ea;
  border-radius: 10px;
  background: #fff;
  font-size: 13px;
}
.pickerLabel {
  color: #64748b;
  margin-right: 4px;
}
.dateRow {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chipItem {
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid #d7e0ea;
  background: #f8fafc;
  color: #334155;
  font-size: 12px;
}
.chipItem.on {
  border-color: #1f4d8f;
  background: #e6f0ff;
  color: #1f4d8f;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.tips {
  border: 1px solid rgba(31, 77, 143, 0.06);
}
.item {
  border: 1px solid rgba(31, 77, 143, 0.06);
}
.warnItem {
  border-color: rgba(185, 28, 28, 0.22);
  background: rgba(254, 242, 242, 0.8);
}
.actionBlock {
  display: flex;
  align-items: center;
  gap: 8px;
}
.action {
  font-weight: 600;
  color: #0f172a;
}
.riskTag {
  font-size: 11px;
  color: #b91c1c;
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 999px;
  padding: 2px 8px;
}
.time {
  font-size: 12px;
  color: #64748b;
}
.meta {
  margin-top: 6px;
  font-size: 12px;
  color: #475569;
}
.detail {
  margin-top: 8px;
  padding: 8px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  color: #334155;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}
.loadCard {
  text-align: center;
}
.empty {
  text-align: center;
  color: #94a3b8;
}
</style>
