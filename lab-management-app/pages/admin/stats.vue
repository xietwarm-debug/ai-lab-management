<template>
  <view class="container statsPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">后台数据看板</view>
            <view class="subtitle">用户、预约、失物、公告与资产的综合态势</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="loading" @click="reload">刷新</button>
        </view>
        <view class="heroMeta muted">当前账号：{{ operator || "-" }}</view>
        <view class="heroMeta muted">数据时间：{{ dashboard.generatedAt || "-" }}</view>
      </view>

      <view class="metricGrid">
        <view class="card metricCard" v-for="item in kpiCards" :key="item.key">
          <view class="metricIcon" :class="'tone-' + item.tone">{{ item.icon }}</view>
          <view class="metricBody">
            <view class="metricLabel">{{ item.label }}</view>
            <view class="metricValue">{{ item.value }}</view>
            <view class="metricSub">{{ item.sub }}</view>
          </view>
        </view>
      </view>

      <view class="card sectionCard">
        <view class="rowBetween sectionHeader">
          <view class="cardTitle">AI 洞察</view>
          <view class="muted">问答 / 风险 / 设备预测</view>
        </view>
        <view class="rowBetween searchRow">
          <input class="inputBase searchInput" v-model.trim="aiQuestion" maxlength="80" placeholder="例如：当前待审批预约有多少？" @confirm="askAiStats" />
          <button class="btnPrimary miniBtn" size="mini" :loading="aiLoading" @click="askAiStats">提问</button>
        </view>
        <view class="aiAnswer" v-if="aiAnswer">{{ aiAnswer }}</view>
        <view class="subSectionTitle">风险提醒</view>
        <view class="empty" v-if="riskLoading && riskAlerts.length === 0">正在加载风险提醒...</view>
        <view class="stack" v-else-if="riskAlerts.length > 0">
          <view class="insightItem clickableItem" v-for="(item, idx) in riskAlerts" :key="'risk-' + idx" @click="openJump(item.jumpUrl)">
            <view class="rowBetween">
              <view class="insightTitle">{{ item.title || "-" }}</view>
              <view class="newsTag" :class="item.level === 'high' ? 'warning' : 'success'">{{ item.level || "-" }}</view>
            </view>
            <view class="newsMeta">{{ item.description || "-" }}</view>
            <view class="jumpText" v-if="item.jumpUrl">点击前往处理</view>
          </view>
        </view>
        <view class="empty" v-else>暂无风险提醒</view>
        <view class="rowBetween subSectionHeader">
          <view class="subSectionTitle">设备健康预测</view>
          <button class="btnGhost miniBtn" size="mini" :loading="equipmentHealthLoading" @click="refreshEquipmentPrediction">刷新预测</button>
        </view>
        <view class="empty" v-if="equipmentHealthLoading && equipmentHealth.length === 0">正在加载设备预测...</view>
        <view class="stack" v-else-if="equipmentHealth.length > 0">
          <view class="insightItem clickableItem" v-for="item in equipmentHealth" :key="'eq-' + item.equipmentId" @click="openJump(item.jumpUrl)">
            <view class="rowBetween">
              <view class="insightTitle">{{ item.name || "-" }}</view>
              <view class="newsTag" :class="item.riskLevel === 'high' ? 'warning' : item.riskLevel === 'medium' ? 'info' : 'success'">
                {{ item.riskLevel || "-" }}
              </view>
            </view>
            <view class="newsMeta">
              {{ item.assetCode || "-" }} · 风险分 {{ toInt(item.riskScore) }} · 30天报修 {{ toInt(item.repairCount30d) }} · 90天报修 {{ toInt(item.repairCount90d) }}
            </view>
            <view class="newsMeta">
              30天故障概率 {{ probabilityText(item.failureProbability) }} · 预测故障类型 {{ item.predictedIssueType || "-" }}
            </view>
            <view class="newsMeta" v-if="equipmentReasonText(item)">{{ equipmentReasonText(item) }}</view>
            <view class="jumpText" v-if="item.recommendation || item.jumpUrl">
              {{ item.recommendation || "点击查看处理入口" }}
            </view>
          </view>
        </view>
        <view class="empty" v-else>暂无设备预测数据</view>
      </view>

      <view class="card sectionCard">
        <view class="rowBetween sectionHeader">
          <view class="cardTitle">预约趋势（近7天）</view>
          <view class="muted">总计 {{ toInt(dashboard.reservations.recent7dTotal) }} 条</view>
        </view>
        <view class="trendList" v-if="trendItems.length > 0">
          <view class="trendRow" v-for="item in trendItems" :key="item.date">
            <view class="trendDate">{{ item.label }}</view>
            <view class="trendBarWrap">
              <view class="trendBar" :style="{ width: trendWidth(item.count) }"></view>
            </view>
            <view class="trendCount">{{ item.count }}</view>
          </view>
        </view>
        <view class="empty" v-else>暂无趋势数据</view>
      </view>

      <view class="card sectionCard">
        <view class="rowBetween sectionHeader">
          <view class="cardTitle">资源负载</view>
          <view class="muted">关键占比</view>
        </view>
        <view class="ratioList">
          <view class="ratioItem" v-for="item in ratioItems" :key="item.key">
            <view class="rowBetween ratioTop">
              <view class="ratioLabel">{{ item.label }}</view>
              <view class="ratioText">{{ item.value }}/{{ item.total }} ({{ formatPercent(item.value, item.total) }})</view>
            </view>
            <view class="ratioTrack">
              <view class="ratioFill" :class="'tone-' + item.tone" :style="{ width: ratioWidth(item.value, item.total) }"></view>
            </view>
          </view>
        </view>
      </view>

      <view class="card sectionCard">
        <view class="rowBetween sectionHeader">
          <view class="cardTitle">实验室热度（近30天预约）</view>
          <button class="btnGhost miniBtn" size="mini" @click="goApprove">去审批页</button>
        </view>
        <view class="topLabList" v-if="topLabs.length > 0">
          <view class="topLabItem" v-for="(item, idx) in topLabs" :key="item.labName + '-' + idx">
            <view class="rowBetween">
              <view class="topLabName">{{ idx + 1 }}. {{ item.labName || "-" }}</view>
              <view class="topLabCount">{{ toInt(item.count) }} 次</view>
            </view>
            <view class="topLabMeta">待审批 {{ toInt(item.pendingCount) }} · 已通过 {{ toInt(item.approvedCount) }}</view>
          </view>
        </view>
        <view class="empty" v-else>暂无实验室排行数据</view>
      </view>

      <view class="card sectionCard">
        <view class="rowBetween sectionHeader">
          <view class="cardTitle">最新公告</view>
          <button class="btnGhost miniBtn" size="mini" @click="goAdminHome">去公告管理</button>
        </view>
        <view class="newsList" v-if="recentAnnouncements.length > 0">
          <view class="newsItem" v-for="item in recentAnnouncements" :key="'announcement-' + item.id">
            <view class="rowBetween">
              <view class="newsTitle">{{ item.title || "未命名公告" }}</view>
              <view class="newsTag" :class="item.status === 'scheduled' ? 'warning' : 'success'">
                {{ item.status === "scheduled" ? "定时中" : "已发布" }}
              </view>
            </view>
            <view class="newsMeta">
              {{ item.publishAt || "-" }} · {{ item.publisherName || "-" }}<text v-if="item.isPinned"> · 置顶</text>
            </view>
          </view>
        </view>
        <view class="empty" v-else>暂无公告数据</view>
      </view>

      <view class="card sectionCard">
        <view class="rowBetween sectionHeader">
          <view class="cardTitle">最近操作日志</view>
          <button class="btnGhost miniBtn" size="mini" @click="goAudit">查看全部</button>
        </view>
        <view class="auditList" v-if="recentAudit.length > 0">
          <view class="auditItem" v-for="(item, idx) in recentAudit" :key="idx">
            <view class="rowBetween">
              <view class="auditAction">{{ item.action || "-" }}</view>
              <view class="auditTime">{{ item.createdAt || "-" }}</view>
            </view>
            <view class="auditMeta">{{ item.operatorName || "-" }} · {{ item.targetType || "-" }} · {{ item.targetId || "-" }}</view>
          </view>
        </view>
        <view class="empty" v-else>暂无操作日志</view>
      </view>

      <view class="card sectionCard">
        <view class="rowBetween sectionHeader">
          <view class="cardTitle">快捷入口</view>
          <view class="muted">继续处理数据</view>
        </view>
        <view class="entryGrid">
          <view class="entryItem" @click="goUsers">用户管理</view>
          <view class="entryItem" @click="goApprove">预约审批</view>
          <view class="entryItem" @click="goLabs">实验室管理</view>
          <view class="entryItem" @click="goEquipments">资产管理</view>
          <view class="entryItem" @click="goKnowledgeBase">知识库管理</view>
          <view class="entryItem" @click="goNotifications">通知中心</view>
          <view class="entryItem" @click="goAudit">审计日志</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import {
  BASE_URL,
  adminGetAiEquipmentHealth,
  adminRefreshAiEquipmentHealth,
  adminGetAiRiskAlerts,
  adminQueryStatsAi
} from "@/common/api.js"

function toInt(value) {
  const n = Number(value)
  return Number.isFinite(n) ? Math.max(0, Math.round(n)) : 0
}

function createEmptyDashboard() {
  return {
    generatedAt: "",
    overview: {
      usersTotal: 0,
      labsTotal: 0,
      reservationsTotal: 0,
      pendingReservations: 0,
      lostFoundOpen: 0,
      claimPending: 0,
      repairToday: 0,
      alarmsToday: 0
    },
    users: { total: 0, byRole: {} },
    labs: { total: 0, free: 0, busy: 0, totalCapacity: 0, totalDevices: 0 },
    reservations: { total: 0, today: 0, byStatus: {}, recent7dTotal: 0, recent7dByStatus: {}, trend7d: [] },
    lostFound: { total: 0, open: 0, closed: 0, claimPending: 0 },
    announcements: { total: 0, published: 0, scheduled: 0, pinned: 0, recent: [] },
    equipment: { total: 0, inService: 0, repairing: 0, scrapped: 0 },
    repair: { total: 0, today: 0, recent7d: 0 },
    alarms: { total: 0, today: 0, recent7d: 0 },
    topLabs30d: [],
    recentAudit: []
  }
}

export default {
  data() {
    return {
      operator: "",
      loading: false,
      aiLoading: false,
      riskLoading: false,
      equipmentHealthLoading: false,
      aiQuestion: "",
      aiAnswer: "",
      riskAlerts: [],
      equipmentHealth: [],
      dashboard: createEmptyDashboard()
    }
  },
  computed: {
    kpiCards() {
      const o = this.dashboard.overview || {}
      return [
        {
          key: "users",
          label: "系统用户",
          value: toInt(o.usersTotal),
          sub: `管理员 ${toInt((this.dashboard.users.byRole || {}).admin)}`,
          icon: "人",
          tone: "blue"
        },
        {
          key: "reservations",
          label: "预约总量",
          value: toInt(o.reservationsTotal),
          sub: `待审批 ${toInt(o.pendingReservations)}`,
          icon: "约",
          tone: "amber"
        },
        {
          key: "lostfound",
          label: "失物处理中",
          value: toInt(o.lostFoundOpen),
          sub: `认领待审 ${toInt(o.claimPending)}`,
          icon: "物",
          tone: "green"
        },
        {
          key: "alarms",
          label: "今日报警",
          value: toInt(o.alarmsToday),
          sub: `报修今日 ${toInt(o.repairToday)}`,
          icon: "警",
          tone: "red"
        },
        {
          key: "labs",
          label: "实验室总数",
          value: toInt(o.labsTotal),
          sub: `繁忙 ${toInt(this.dashboard.labs.busy)}`,
          icon: "室",
          tone: "violet"
        },
        {
          key: "equipment",
          label: "设备总数",
          value: toInt(this.dashboard.equipment.total),
          sub: `维修中 ${toInt(this.dashboard.equipment.repairing)}`,
          icon: "资",
          tone: "teal"
        },
        {
          key: "announcement",
          label: "公告总数",
          value: toInt(this.dashboard.announcements.total),
          sub: `定时中 ${toInt(this.dashboard.announcements.scheduled)}`,
          icon: "告",
          tone: "indigo"
        },
        {
          key: "reservationToday",
          label: "今日预约",
          value: toInt(this.dashboard.reservations.today),
          sub: `近7天 ${toInt(this.dashboard.reservations.recent7dTotal)}`,
          icon: "今",
          tone: "orange"
        }
      ]
    },
    trendItems() {
      const rows = this.dashboard.reservations && Array.isArray(this.dashboard.reservations.trend7d)
        ? this.dashboard.reservations.trend7d
        : []
      return rows.map((item) => ({
        date: item.date || "",
        label: item.label || (item.date || "").slice(5),
        count: toInt(item.count)
      }))
    },
    maxTrendCount() {
      return this.trendItems.reduce((m, x) => Math.max(m, toInt(x.count)), 0)
    },
    ratioItems() {
      return [
        {
          key: "labsBusy",
          label: "实验室繁忙占比",
          value: toInt(this.dashboard.labs.busy),
          total: toInt(this.dashboard.labs.total),
          tone: "blue"
        },
        {
          key: "equipRepairing",
          label: "设备维修占比",
          value: toInt(this.dashboard.equipment.repairing),
          total: toInt(this.dashboard.equipment.total),
          tone: "amber"
        },
        {
          key: "announceScheduled",
          label: "公告定时占比",
          value: toInt(this.dashboard.announcements.scheduled),
          total: toInt(this.dashboard.announcements.total),
          tone: "violet"
        },
        {
          key: "reservationPending",
          label: "预约待审占比",
          value: toInt(this.dashboard.overview.pendingReservations),
          total: toInt(this.dashboard.reservations.total),
          tone: "red"
        }
      ]
    },
    topLabs() {
      return Array.isArray(this.dashboard.topLabs30d) ? this.dashboard.topLabs30d : []
    },
    recentAudit() {
      return Array.isArray(this.dashboard.recentAudit) ? this.dashboard.recentAudit : []
    },
    recentAnnouncements() {
      return Array.isArray(this.dashboard.announcements.recent) ? this.dashboard.announcements.recent : []
    }
  },
  onShow() {
    if (!this.ensureAdmin()) return
    const s = uni.getStorageSync("session") || {}
    this.operator = s.username || ""
    this.fetchDashboard()
    this.fetchRiskAlerts()
    this.fetchEquipmentHealth()
  },
  onPullDownRefresh() {
    if (!this.ensureAdmin()) {
      uni.stopPullDownRefresh()
      return
    }
    this.fetchDashboard(true)
  },
  methods: {
    toInt,
    ensureAdmin() {
      const s = uni.getStorageSync("session")
      if (!s || s.role !== "admin") {
        uni.showToast({ title: "无权限", icon: "none" })
        uni.reLaunch({ url: "/pages/login/login" })
        return false
      }
      return true
    },
    formatPercent(value, total) {
      const t = toInt(total)
      if (t <= 0) return "0%"
      const v = toInt(value)
      return `${Math.round((v / t) * 100)}%`
    },
    probabilityText(value) {
      const n = Number(value || 0)
      if (!Number.isFinite(n) || n <= 0) return "0%"
      return `${Math.round(n * 100)}%`
    },
    ratioWidth(value, total) {
      const t = toInt(total)
      if (t <= 0) return "0%"
      const v = Math.min(t, toInt(value))
      const pct = Math.round((v / t) * 100)
      return `${Math.max(4, pct)}%`
    },
    trendWidth(count) {
      const max = this.maxTrendCount
      if (max <= 0) return "0%"
      const pct = Math.round((toInt(count) / max) * 100)
      return `${Math.max(6, pct)}%`
    },
    normalizeDashboard(raw) {
      const data = raw && typeof raw === "object" ? raw : {}
      const base = createEmptyDashboard()
      return {
        ...base,
        ...data,
        overview: { ...base.overview, ...(data.overview || {}) },
        users: { ...base.users, ...(data.users || {}), byRole: { ...(base.users.byRole || {}), ...((data.users || {}).byRole || {}) } },
        labs: { ...base.labs, ...(data.labs || {}) },
        reservations: { ...base.reservations, ...(data.reservations || {}), byStatus: { ...(base.reservations.byStatus || {}), ...((data.reservations || {}).byStatus || {}) } },
        lostFound: { ...base.lostFound, ...(data.lostFound || {}) },
        announcements: { ...base.announcements, ...(data.announcements || {}) },
        equipment: { ...base.equipment, ...(data.equipment || {}) },
        repair: { ...base.repair, ...(data.repair || {}) },
        alarms: { ...base.alarms, ...(data.alarms || {}) },
        topLabs30d: Array.isArray(data.topLabs30d) ? data.topLabs30d : [],
        recentAudit: Array.isArray(data.recentAudit) ? data.recentAudit : []
      }
    },
    reload() {
      this.fetchDashboard()
      this.fetchRiskAlerts()
      this.fetchEquipmentHealth()
    },
    async fetchDashboard(stopRefresh = false) {
      if (this.loading) {
        if (stopRefresh) uni.stopPullDownRefresh()
        return
      }
      this.loading = true
      try {
        const res = await uni.request({
          url: `${BASE_URL}/admin/stats/dashboard`,
          method: "GET"
        })
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          uni.showToast({ title: payload.msg || "获取统计失败", icon: "none" })
          return
        }
        this.dashboard = this.normalizeDashboard(payload.data)
      } catch (e) {
        uni.showToast({ title: "获取统计失败", icon: "none" })
      } finally {
        this.loading = false
        if (stopRefresh) uni.stopPullDownRefresh()
      }
    },
    async askAiStats() {
      if (this.aiLoading) return
      this.aiLoading = true
      try {
        const res = await adminQueryStatsAi({ question: String(this.aiQuestion || "").trim() })
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          this.aiAnswer = payload.msg || "AI问答失败"
          return
        }
        this.aiAnswer = String((payload.data && payload.data.answer) || "").trim()
      } catch (e) {
        this.aiAnswer = "AI问答失败"
      } finally {
        this.aiLoading = false
      }
    },
    async fetchRiskAlerts() {
      if (this.riskLoading) return
      this.riskLoading = true
      try {
        const res = await adminGetAiRiskAlerts()
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          this.riskAlerts = []
          return
        }
        this.riskAlerts = Array.isArray(payload.data.alerts) ? payload.data.alerts : []
      } catch (e) {
        this.riskAlerts = []
      } finally {
        this.riskLoading = false
      }
    },
    async fetchEquipmentHealth() {
      if (this.equipmentHealthLoading) return
      this.equipmentHealthLoading = true
      try {
        const res = await adminGetAiEquipmentHealth(6)
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          this.equipmentHealth = []
          return
        }
        this.equipmentHealth = Array.isArray(payload.data.items) ? payload.data.items : []
      } catch (e) {
        this.equipmentHealth = []
      } finally {
        this.equipmentHealthLoading = false
      }
    },
    async refreshEquipmentPrediction() {
      if (this.equipmentHealthLoading) return
      this.equipmentHealthLoading = true
      try {
        const res = await adminRefreshAiEquipmentHealth({ horizonDaysList: [7, 30] })
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "预测刷新失败", icon: "none" })
          return
        }
        uni.showToast({ title: "预测已刷新", icon: "success" })
      } catch (e) {
        uni.showToast({ title: "预测刷新失败", icon: "none" })
      } finally {
        this.equipmentHealthLoading = false
      }
      this.fetchEquipmentHealth()
    },
    equipmentReasonText(item) {
      const lines = Array.isArray(item && item.reasonLines) ? item.reasonLines : []
      return lines.slice(0, 2).join("；")
    },
    openJump(url) {
      const target = String(url || "").trim()
      if (!target) return
      uni.navigateTo({ url: target })
    },
    goAdminHome() {
      uni.switchTab({ url: "/pages/workbench/index" })
    },
    goUsers() {
      uni.navigateTo({ url: "/pages/admin/users" })
    },
    goApprove() {
      uni.navigateTo({ url: "/pages/admin/approve" })
    },
    goLabs() {
      uni.navigateTo({ url: "/pages/admin/labs" })
    },
    goEquipments() {
      uni.navigateTo({ url: "/pages/admin/equipments" })
    },
    goKnowledgeBase() {
      uni.navigateTo({ url: "/pages/admin/knowledge_base" })
    },
    goNotifications() {
      uni.navigateTo({ url: "/pages/notifications/list" })
    },
    goAudit() {
      uni.navigateTo({ url: "/pages/admin/audit" })
    }
  }
}
</script>

<style lang="scss">
.statsPage {
  padding-bottom: 24px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.2);
  background: linear-gradient(160deg, #ffffff 0%, #edf5ff 100%);
}

.heroTop {
  align-items: flex-start;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}

.heroMeta {
  margin-top: 6px;
}

.searchRow {
  gap: 8px;
  align-items: center;
}

.searchInput {
  flex: 1;
  min-height: 38px;
}

.aiAnswer {
  margin-top: 10px;
  font-size: 13px;
  line-height: 20px;
  color: #0f172a;
}

.subSectionTitle {
  margin-top: 14px;
  font-size: 12px;
  color: #64748b;
}

.subSectionHeader {
  align-items: center;
}

.insightItem {
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 12px;
  padding: 10px;
  background: #fff;
}

.clickableItem {
  cursor: pointer;
}

.insightTitle {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.jumpText {
  margin-top: 6px;
  font-size: 11px;
  color: #1d4ed8;
}

.metricGrid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.metricCard {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 86px;
}

.metricIcon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}

.metricIcon.tone-blue { color: #1d4ed8; background: #eaf3ff; }
.metricIcon.tone-amber { color: #b45309; background: #fff4dd; }
.metricIcon.tone-green { color: #15803d; background: #eafaf0; }
.metricIcon.tone-red { color: #b91c1c; background: #fee2e2; }
.metricIcon.tone-violet { color: #6d28d9; background: #f3ebff; }
.metricIcon.tone-teal { color: #0f766e; background: #e6fffb; }
.metricIcon.tone-indigo { color: #4338ca; background: #eef2ff; }
.metricIcon.tone-orange { color: #c2410c; background: #fff7ed; }

.metricBody {
  min-width: 0;
}

.metricLabel {
  font-size: 12px;
  color: #64748b;
}

.metricValue {
  margin-top: 2px;
  font-size: 22px;
  line-height: 1.12;
  font-weight: 700;
  color: #0f172a;
}

.metricSub {
  margin-top: 2px;
  font-size: 11px;
  color: #94a3b8;
}

.sectionCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.sectionHeader {
  align-items: flex-start;
}

.trendList {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.trendRow {
  display: flex;
  align-items: center;
  gap: 8px;
}

.trendDate {
  width: 42px;
  font-size: 12px;
  color: #64748b;
}

.trendBarWrap {
  flex: 1;
  height: 10px;
  border-radius: 999px;
  background: #eef2ff;
  overflow: hidden;
}

.trendBar {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #60a5fa 0%, #2563eb 100%);
}

.trendCount {
  min-width: 30px;
  text-align: right;
  font-size: 12px;
  color: #475569;
}

.ratioList {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ratioTop {
  gap: 8px;
}

.ratioLabel {
  font-size: 12px;
  font-weight: 600;
  color: #0f172a;
}

.ratioText {
  font-size: 11px;
  color: #64748b;
}

.ratioTrack {
  margin-top: 6px;
  width: 100%;
  height: 10px;
  border-radius: 999px;
  background: #f1f5f9;
  overflow: hidden;
}

.ratioFill {
  height: 100%;
  border-radius: 999px;
}

.ratioFill.tone-blue { background: #3b82f6; }
.ratioFill.tone-amber { background: #f59e0b; }
.ratioFill.tone-violet { background: #8b5cf6; }
.ratioFill.tone-red { background: #ef4444; }

.topLabList,
.newsList,
.auditList {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.topLabItem,
.newsItem,
.auditItem {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 10px;
  padding: 8px 10px;
  background: #fff;
}

.topLabName,
.newsTitle,
.auditAction {
  font-size: 13px;
  line-height: 19px;
  font-weight: 600;
  color: #0f172a;
}

.topLabCount {
  font-size: 12px;
  color: #2563eb;
}

.topLabMeta,
.newsMeta,
.auditMeta,
.auditTime {
  margin-top: 4px;
  font-size: 11px;
  color: #64748b;
}

.newsTag {
  height: 20px;
  line-height: 20px;
  border-radius: 999px;
  padding: 0 8px;
  font-size: 10px;
  font-weight: 600;
}

.newsTag.success {
  color: #15803d;
  background: #dcfce7;
}

.newsTag.info {
  color: #1d4ed8;
  background: #dbeafe;
}

.newsTag.warning {
  color: #b45309;
  background: #fef3c7;
}

.entryGrid {
  margin-top: 8px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.entryItem {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 10px;
  padding: 9px 4px;
  text-align: center;
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
  background: #fff;
}

.entryItem:active {
  opacity: 0.86;
}
</style>
