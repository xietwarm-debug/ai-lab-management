<template>
  <view class="container reportPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">数据报表中心</view>
            <view class="subtitle">统一统计与一键导出</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="loading" @click="fetchReport">刷新</button>
        </view>
        <view class="heroMeta muted">统计区间：{{ filters.startDate }} ~ {{ filters.endDate }}（{{ report.range.days || 0 }} 天）</view>
        <view class="heroMeta muted">生成时间：{{ report.generatedAt || "-" }}</view>

        <view class="filterGrid">
          <picker mode="date" :value="filters.startDate" @change="onStartDateChange">
            <view class="dateField">{{ filters.startDate || "开始日期" }}</view>
          </picker>
          <picker mode="date" :value="filters.endDate" @change="onEndDateChange">
            <view class="dateField">{{ filters.endDate || "结束日期" }}</view>
          </picker>
        </view>
        <view class="chipRow">
          <view class="chip" @click="setQuickRange(7)">近7天</view>
          <view class="chip" @click="setQuickRange(30)">近30天</view>
          <view class="chip" @click="setQuickRange(90)">近90天</view>
        </view>
        <view class="rowBetween actions">
          <button class="btnGhost miniBtn" size="mini" :loading="exporting === 'csv'" @click="downloadReport('csv')">导出 CSV</button>
          <button class="btnPrimary miniBtn" size="mini" :loading="exporting === 'excel'" @click="downloadReport('excel')">导出 Excel</button>
        </view>
      </view>

      <view class="metricGrid">
        <view class="card metricCard" v-for="item in summaryCards" :key="item.key">
          <view class="metricLabel">{{ item.label }}</view>
          <view class="metricValue">{{ item.value }}</view>
          <view class="metricSub">{{ item.sub }}</view>
        </view>
      </view>

      <view class="card sectionCard">
        <view class="cardTitle">预约统计报表</view>
        <view class="muted">Top 实验室预约量</view>
        <view class="list" v-if="topLabs.length > 0">
          <view class="listItem" v-for="item in topLabs" :key="item.labName">
            <view class="rowBetween">
              <view>{{ item.labName || "-" }}</view>
              <view class="muted">{{ toInt(item.total) }} 次</view>
            </view>
          </view>
        </view>
        <view class="empty" v-else>暂无数据</view>
      </view>

      <view class="card sectionCard">
        <view class="cardTitle">实验室利用率报表</view>
        <view class="muted">Top 实验室利用率</view>
        <view class="list" v-if="labRows.length > 0">
          <view class="listItem" v-for="item in labRows.slice(0, 6)" :key="item.labId">
            <view class="rowBetween">
              <view>{{ item.labName || "-" }}</view>
              <view class="muted">{{ formatPercent(item.utilizationRate) }}</view>
            </view>
          </view>
        </view>
        <view class="empty" v-else>暂无数据</view>
      </view>

      <view class="card sectionCard">
        <view class="cardTitle">设备故障率报表</view>
        <view class="muted">问题类型分布</view>
        <view class="list" v-if="issueRows.length > 0">
          <view class="listItem" v-for="item in issueRows" :key="item.issueType">
            <view class="rowBetween">
              <view>{{ item.issueType || "-" }}</view>
              <view class="muted">{{ toInt(item.count) }} 单</view>
            </view>
          </view>
        </view>
        <view class="empty" v-else>暂无数据</view>
      </view>

      <view class="card sectionCard">
        <view class="cardTitle">用户活跃度报表</view>
        <view class="muted">角色活跃情况</view>
        <view class="list" v-if="roleRows.length > 0">
          <view class="listItem" v-for="item in roleRows" :key="item.role">
            <view class="rowBetween">
              <view>{{ item.role || "-" }}</view>
              <view class="muted">{{ toInt(item.active) }}/{{ toInt(item.total) }} · {{ formatPercent(item.activityRate) }}</view>
            </view>
          </view>
        </view>
        <view class="empty" v-else>暂无数据</view>
      </view>

      <view class="card sectionCard">
        <view class="cardTitle">公告触达报表</view>
        <view class="muted">最近公告触达率</view>
        <view class="list" v-if="announcementRows.length > 0">
          <view class="listItem" v-for="item in announcementRows.slice(0, 6)" :key="item.announcementId">
            <view class="rowBetween">
              <view class="lineClamp">{{ item.title || "-" }}</view>
              <view class="muted">{{ formatPercent(item.readRate) }}</view>
            </view>
          </view>
        </view>
        <view class="empty" v-else>暂无数据</view>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"

function pad(n) {
  return n < 10 ? `0${n}` : `${n}`
}
function todayYmd() {
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
function shiftDateText(baseText, diffDays) {
  const base = new Date(`${baseText}T00:00:00`)
  if (Number.isNaN(base.getTime())) return baseText
  base.setDate(base.getDate() + Number(diffDays || 0))
  return `${base.getFullYear()}-${pad(base.getMonth() + 1)}-${pad(base.getDate())}`
}
function toQuery(params) {
  const out = []
  Object.keys(params || {}).forEach((k) => {
    const v = (params || {})[k]
    if (v === undefined || v === null || v === "") return
    out.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
  })
  return out.join("&")
}
function createEmptyReport() {
  return {
    generatedAt: "",
    range: { startDate: "", endDate: "", days: 0 },
    reservation: { summary: {}, topLabs: [] },
    labUtilization: { summary: {}, labs: [] },
    equipmentFailure: { summary: {}, byIssueType: [] },
    repairEfficiency: { summary: {} },
    courseTaskCompletion: { summary: {} },
    userActivity: { summary: {}, byRole: [] },
    announcementReach: { summary: {}, items: [] }
  }
}

export default {
  data() {
    return {
      loading: false,
      exporting: "",
      filters: { startDate: "", endDate: "" },
      report: createEmptyReport()
    }
  },
  computed: {
    summaryCards() {
      const r = this.report || {}
      const reservation = (r.reservation || {}).summary || {}
      const lab = (r.labUtilization || {}).summary || {}
      const equipment = (r.equipmentFailure || {}).summary || {}
      const repair = (r.repairEfficiency || {}).summary || {}
      const task = (r.courseTaskCompletion || {}).summary || {}
      const user = (r.userActivity || {}).summary || {}
      const announce = (r.announcementReach || {}).summary || {}
      return [
        { key: "reservation", label: "预约统计", value: this.toInt(reservation.total), sub: `通过 ${this.toInt(reservation.approved)} · 待审 ${this.toInt(reservation.pending)}` },
        { key: "lab", label: "实验室利用率", value: this.formatPercent(lab.overallRate), sub: `已用 ${this.toInt(lab.totalUsedSlots)} / ${this.toInt(lab.totalAvailableSlots)}` },
        { key: "equipment", label: "设备故障率", value: this.formatPercent(equipment.affectedFailureRate), sub: `受影响设备 ${this.toInt(equipment.affectedEquipments)}` },
        { key: "repair", label: "报修效率", value: this.formatPercent(repair.completionRate), sub: `平均响应 ${this.toInt(repair.avgResponseMinutes)} 分钟` },
        { key: "task", label: "课程任务完成率", value: this.formatPercent(task.completionRate), sub: `已交 ${this.toInt(task.submittedSubmissions)} / ${this.toInt(task.expectedSubmissions)}` },
        { key: "user", label: "用户活跃度", value: this.formatPercent(user.activityRate), sub: `活跃用户 ${this.toInt(user.activeUsers)}` },
        { key: "announcement", label: "公告触达", value: this.formatPercent(announce.reachRate), sub: `阅读用户 ${this.toInt(announce.uniqueReaders)}` }
      ]
    },
    topLabs() {
      return Array.isArray(((this.report || {}).reservation || {}).topLabs) ? this.report.reservation.topLabs : []
    },
    labRows() {
      return Array.isArray(((this.report || {}).labUtilization || {}).labs) ? this.report.labUtilization.labs : []
    },
    issueRows() {
      return Array.isArray(((this.report || {}).equipmentFailure || {}).byIssueType) ? this.report.equipmentFailure.byIssueType : []
    },
    roleRows() {
      return Array.isArray(((this.report || {}).userActivity || {}).byRole) ? this.report.userActivity.byRole : []
    },
    announcementRows() {
      return Array.isArray(((this.report || {}).announcementReach || {}).items) ? this.report.announcementReach.items : []
    }
  },
  onShow() {
    const s = uni.getStorageSync("session")
    if (!s || s.role !== "admin") {
      uni.showToast({ title: "无权限", icon: "none" })
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    if (!this.filters.startDate || !this.filters.endDate) this.setQuickRange(30)
    this.fetchReport()
  },
  onPullDownRefresh() {
    this.fetchReport(true)
  },
  methods: {
    toInt(v) {
      const n = Number(v)
      return Number.isFinite(n) ? Math.round(n) : 0
    },
    formatPercent(v) {
      return `${Math.round((Number(v || 0) || 0) * 10000) / 100}%`
    },
    setQuickRange(days) {
      const end = todayYmd()
      this.filters.endDate = end
      this.filters.startDate = shiftDateText(end, -Math.max(1, Number(days || 1)) + 1)
    },
    onStartDateChange(e) {
      this.filters.startDate = (e.detail || {}).value || ""
    },
    onEndDateChange(e) {
      this.filters.endDate = (e.detail || {}).value || ""
    },
    validateRange() {
      if (!this.filters.startDate || !this.filters.endDate) return false
      if (this.filters.startDate > this.filters.endDate) {
        uni.showToast({ title: "开始日期不能大于结束日期", icon: "none" })
        return false
      }
      return true
    },
    async fetchReport(stopRefresh = false) {
      if (!this.validateRange()) {
        if (stopRefresh) uni.stopPullDownRefresh()
        return
      }
      if (this.loading) {
        if (stopRefresh) uni.stopPullDownRefresh()
        return
      }
      this.loading = true
      try {
        const qs = toQuery({ startDate: this.filters.startDate, endDate: this.filters.endDate })
        const res = await uni.request({ url: `${BASE_URL}/admin/reports/center?${qs}`, method: "GET" })
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          uni.showToast({ title: payload.msg || "获取报表失败", icon: "none" })
          return
        }
        this.report = { ...createEmptyReport(), ...(payload.data || {}) }
      } catch (e) {
        uni.showToast({ title: "获取报表失败", icon: "none" })
      } finally {
        this.loading = false
        if (stopRefresh) uni.stopPullDownRefresh()
      }
    },
    downloadReport(format) {
      if (!this.validateRange()) return
      if (this.exporting) return
      this.exporting = format
      const qs = toQuery({ startDate: this.filters.startDate, endDate: this.filters.endDate, format })
      uni.downloadFile({
        url: `${BASE_URL}/admin/reports/center/export?${qs}`,
        success: (res) => {
          if (res.statusCode !== 200) {
            uni.showToast({ title: "导出失败", icon: "none" })
            return
          }
          uni.openDocument({
            filePath: res.tempFilePath,
            fileType: format === "excel" ? "xls" : "csv",
            fail: () => uni.showToast({ title: "已导出，请在文件管理查看", icon: "none" })
          })
        },
        fail: () => uni.showToast({ title: "导出失败", icon: "none" }),
        complete: () => { this.exporting = "" }
      })
    }
  }
}
</script>

<style lang="scss">
.reportPage { padding-bottom: 24px; }
.heroCard { border: 1px solid rgba(22, 119, 255, 0.2); background: linear-gradient(160deg, #ffffff 0%, #eff6ff 100%); }
.heroTop { align-items: flex-start; }
.heroMeta { margin-top: 6px; }
.miniBtn { min-height: 30px; line-height: 30px; padding: 0 10px; border-radius: 9px; font-size: 12px; }
.filterGrid { margin-top: 8px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.dateField { border: 1px solid rgba(148, 163, 184, 0.32); border-radius: 10px; padding: 8px 10px; font-size: 12px; color: #334155; background: #fff; }
.chipRow { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 8px; }
.chip { padding: 4px 10px; border-radius: 999px; border: 1px solid rgba(148, 163, 184, 0.4); background: #fff; font-size: 12px; color: #334155; }
.actions { margin-top: 8px; }
.metricGrid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.metricCard { border: 1px solid rgba(148, 163, 184, 0.24); min-height: 80px; }
.metricLabel { font-size: 12px; color: #64748b; }
.metricValue { margin-top: 4px; font-size: 20px; font-weight: 700; color: #0f172a; }
.metricSub { margin-top: 4px; font-size: 11px; color: #94a3b8; }
.sectionCard { border: 1px solid rgba(148, 163, 184, 0.24); }
.list { margin-top: 8px; display: flex; flex-direction: column; gap: 8px; }
.listItem { border: 1px solid rgba(148, 163, 184, 0.24); border-radius: 10px; padding: 8px 10px; background: #fff; font-size: 12px; color: #1e293b; }
.empty { margin-top: 10px; font-size: 12px; color: #94a3b8; }
.lineClamp { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 220px; }
</style>
