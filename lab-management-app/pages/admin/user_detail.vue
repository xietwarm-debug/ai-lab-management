<template>
  <view class="container detailPage">
    <view class="stack">
      <view class="card" v-if="loading">
        <view class="muted">正在加载用户详情...</view>
      </view>

      <template v-else>
        <view class="card">
          <view class="title">{{ user.username || "-" }}</view>
          <view class="subtitle">ID {{ user.id || "-" }} · 角色 {{ roleText(user.role) }} · 状态 {{ stateText(user) }}</view>
          <view class="muted">班级 {{ user.className || "-" }} · 毕业 {{ user.graduationYear || "-" }} · 最近登录 {{ user.lastLoginAt || "从未登录" }}</view>
        </view>

        <view class="metricGrid">
          <view class="card metricCard" v-for="item in summaryCards" :key="item.key">
            <view class="metricLabel">{{ item.label }}</view>
            <view class="metricValue">{{ item.value }}</view>
          </view>
        </view>

        <view class="card">
          <view class="chipRow">
            <view
              v-for="tab in tabs"
              :key="tab.value"
              class="chip"
              :class="{ chipOn: currentTab === tab.value }"
              @click="currentTab = tab.value"
            >
              {{ tab.label }}
            </view>
          </view>
        </view>

        <view class="card" v-if="currentTab === 'reservations'">
          <view class="cardTitle">预约记录</view>
          <view class="rowItem" v-for="r in detail.reservations || []" :key="`res-${r.id}`">
            <view>{{ r.labName || "-" }} · {{ r.date || "-" }} {{ r.time || "-" }}</view>
            <view class="muted">{{ r.status || "-" }} · {{ r.createdAt || "-" }}</view>
          </view>
          <view class="muted" v-if="!(detail.reservations || []).length">暂无记录</view>
        </view>

        <view class="card" v-if="currentTab === 'repairs'">
          <view class="cardTitle">报修记录</view>
          <view class="rowItem" v-for="r in detail.repairs || []" :key="`repair-${r.id}`">
            <view>{{ r.orderNo || "-" }} · {{ r.issueType || "-" }} · {{ r.status || "-" }}</view>
            <view class="muted">{{ r.labName || "-" }} / {{ r.equipmentName || "-" }} · {{ r.createdAt || "-" }}</view>
          </view>
          <view class="muted" v-if="!(detail.repairs || []).length">暂无记录</view>
        </view>

        <view class="card" v-if="currentTab === 'lostfound'">
          <view class="cardTitle">失物招领记录</view>
          <view class="rowItem" v-for="r in detail.lostFound || []" :key="`lost-${r.id}`">
            <view>{{ r.title || "-" }} · {{ r.status || "-" }}</view>
            <view class="muted">关系 {{ r.relation || "-" }} · {{ r.createdAt || "-" }}</view>
          </view>
          <view class="muted" v-if="!(detail.lostFound || []).length">暂无记录</view>
        </view>

        <view class="card" v-if="currentTab === 'courses'">
          <view class="cardTitle">课程参与</view>
          <view class="muted sectionLabel">授课</view>
          <view class="rowItem" v-for="c in (detail.courses || {}).teaching || []" :key="`teach-${c.id}`">
            <view>{{ c.name || "-" }} · {{ c.courseCode || "-" }}</view>
            <view class="muted">{{ c.className || "-" }} · {{ c.status || "-" }}</view>
          </view>
          <view class="muted" v-if="!(((detail.courses || {}).teaching || []).length)">暂无授课记录</view>

          <view class="muted sectionLabel">学生参与</view>
          <view class="rowItem" v-for="c in (detail.courses || {}).joined || []" :key="`join-${c.courseId}`">
            <view>{{ c.name || "-" }} · {{ c.courseCode || "-" }}</view>
            <view class="muted">{{ c.className || "-" }} · {{ c.teacherUserName || "-" }}</view>
          </view>
          <view class="muted" v-if="!(((detail.courses || {}).joined || []).length)">暂无参与记录</view>
        </view>

        <view class="card" v-if="currentTab === 'audit'">
          <view class="cardTitle">审计行为</view>
          <view class="rowItem" v-for="a in detail.auditActions || []" :key="`audit-${a.id}`">
            <view>{{ a.action || "-" }}</view>
            <view class="muted">{{ a.operatorName || "-" }} · {{ a.createdAt || "-" }}</view>
          </view>
          <view class="muted" v-if="!(detail.auditActions || []).length">暂无记录</view>
        </view>

        <view class="card" v-if="currentTab === 'violations'">
          <view class="cardTitle">违规记录</view>
          <view class="rowItem" v-for="v in detail.violationRecords || []" :key="`vio-${v.source}-${v.id}`">
            <view>{{ v.source || "-" }} · {{ v.reason || "-" }}</view>
            <view class="muted">{{ v.happenedAt || "-" }} · {{ v.detail || "-" }}</view>
          </view>
          <view class="muted" v-if="!(detail.violationRecords || []).length">暂无记录</view>
        </view>
      </template>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"

function toInt(v, d = 0) {
  const n = Number(v)
  return Number.isFinite(n) ? Math.round(n) : d
}

export default {
  data() {
    return {
      uid: 0,
      loading: false,
      currentTab: "reservations",
      tabs: [
        { label: "预约", value: "reservations" },
        { label: "报修", value: "repairs" },
        { label: "失物", value: "lostfound" },
        { label: "课程", value: "courses" },
        { label: "审计", value: "audit" },
        { label: "违规", value: "violations" }
      ],
      detail: {}
    }
  },
  computed: {
    user() { return (this.detail || {}).user || {} },
    summary() { return (this.detail || {}).summary || {} },
    summaryCards() {
      return [
        { key: "reservation", label: "预约", value: toInt(this.summary.reservationTotal, 0) },
        { key: "repair", label: "报修", value: toInt(this.summary.repairTotal, 0) },
        { key: "lost", label: "失物", value: toInt(this.summary.lostFoundTotal, 0) },
        { key: "course", label: "课程", value: toInt(this.summary.courseTotal, 0) },
        { key: "audit", label: "审计", value: toInt(this.summary.auditTotal, 0) },
        { key: "violation", label: "违规", value: toInt(this.summary.violationTotal, 0) }
      ]
    }
  },
  onLoad(query) {
    this.uid = toInt((query || {}).uid, 0)
    if (this.uid <= 0) {
      uni.showToast({ title: "用户ID无效", icon: "none" })
      return
    }
    this.fetchDetail()
  },
  methods: {
    roleText(role) {
      if (role === "admin") return "管理员"
      if (role === "teacher") return "教师"
      if (role === "student") return "学生"
      return role || "未知"
    },
    stateText(u) {
      if (Number((u || {}).isFrozen || 0) === 1) return "冻结"
      if (Number((u || {}).isActive || 0) === 1) return "活跃"
      return "停用"
    },
    fetchDetail() {
      if (this.uid <= 0) return
      this.loading = true
      uni.request({
        url: `${BASE_URL}/users/${this.uid}/detail?limit=30`,
        method: "GET",
        success: (res) => {
          const payload = res && res.data
          if (!payload || !payload.ok) {
            uni.showToast({ title: (payload && payload.msg) || "获取失败", icon: "none" })
            return
          }
          this.detail = payload.data || {}
        },
        fail: () => uni.showToast({ title: "请求失败", icon: "none" }),
        complete: () => { this.loading = false }
      })
    }
  }
}
</script>

<style lang="scss">
.detailPage { padding-bottom: 20px; }
.chipRow { display: flex; flex-wrap: wrap; gap: 8px; }
.chipOn { border-color: #bfdbfe; background: #eaf3ff; color: #1d4ed8; }
.metricGrid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.metricCard { min-height: 78px; }
.metricLabel { font-size: 12px; color: #64748b; }
.metricValue { margin-top: 4px; font-size: 22px; font-weight: 700; color: #0f172a; }
.sectionLabel { margin-top: 10px; }
.rowItem { margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(148, 163, 184, 0.2); }
</style>
