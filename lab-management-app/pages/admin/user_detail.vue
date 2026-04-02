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

        <view class="card" v-if="canManagePermissions">
          <view class="rowBetween">
            <view>
              <view class="cardTitle">资产只读权限</view>
              <view class="muted">用于手机端只读资产查询和 AI 资产问答。</view>
            </view>
            <view class="statusPill" :class="permissionStatusClass(assetReadPermission)">
              {{ permissionStatusText(assetReadPermission) }}
            </view>
          </view>
          <view class="muted permissionMeta" v-if="assetReadPermission && assetReadPermission.expiresAt">
            到期时间：{{ assetReadPermission.expiresAt }}
          </view>
          <view class="actions">
            <button class="btnSecondary miniBtn" size="mini" :disabled="permissionLoading" @click="fetchPermissions">刷新</button>
            <button
              v-if="!(assetReadPermission && assetReadPermission.granted)"
              class="btnPrimary miniBtn"
              size="mini"
              :disabled="permissionLoading"
              @click="grantAssetReadPermission"
            >
              授权
            </button>
            <button
              v-else
              class="btnDanger miniBtn"
              size="mini"
              :disabled="permissionLoading"
              @click="revokeAssetReadPermission"
            >
              撤销
            </button>
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
import { BASE_URL, adminGetUserPermissions, adminGrantUserPermission, adminRevokeUserPermission } from "@/common/api.js"

const PERMISSION_ASSET_READ_BASIC = "asset.read_basic"

function toInt(v, d = 0) {
  const n = Number(v)
  return Number.isFinite(n) ? Math.round(n) : d
}

export default {
  data() {
    return {
      uid: 0,
      loading: false,
      permissionLoading: false,
      currentRole: "",
      permissionRows: [],
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
    canManagePermissions() {
      const targetRole = String((this.user || {}).role || "").trim()
      return this.currentRole === "admin" && (targetRole === "teacher" || targetRole === "student")
    },
    assetReadPermission() {
      const rows = Array.isArray(this.permissionRows) ? this.permissionRows : []
      return rows.find((item) => String((item && item.permissionCode) || "").trim() === PERMISSION_ASSET_READ_BASIC) || null
    },
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
    try {
      const session = uni.getStorageSync("session") || {}
      this.currentRole = String((session && session.role) || "").trim()
    } catch (e) {
      this.currentRole = ""
    }
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
    permissionStatusText(row) {
      if (row && row.granted) return "已授权"
      if (row && row.source === "expired") return "已过期"
      return "未授权"
    },
    permissionStatusClass(row) {
      if (row && row.granted) return "statusGranted"
      if (row && row.source === "expired") return "statusExpired"
      return "statusPlain"
    },
    async fetchPermissions() {
      if (!this.canManagePermissions || this.uid <= 0) return
      this.permissionLoading = true
      try {
        const res = await adminGetUserPermissions(this.uid)
        const payload = (res && res.data) || {}
        const data = payload && payload.ok ? payload.data : {}
        this.permissionRows = Array.isArray(data.items) ? data.items : []
      } catch (e) {
        this.permissionRows = []
      } finally {
        this.permissionLoading = false
      }
    },
    async grantAssetReadPermission() {
      if (!this.canManagePermissions || this.uid <= 0) return
      this.permissionLoading = true
      try {
        const res = await adminGrantUserPermission(this.uid, { permissionCode: PERMISSION_ASSET_READ_BASIC })
        const payload = (res && res.data) || {}
        if (!payload.ok) throw new Error(payload.msg || "授权失败")
        uni.showToast({ title: "已授权", icon: "success" })
        await this.fetchPermissions()
      } catch (e) {
        uni.showToast({ title: (e && e.message) || "授权失败", icon: "none" })
      } finally {
        this.permissionLoading = false
      }
    },
    revokeAssetReadPermission() {
      if (!this.canManagePermissions || this.uid <= 0) return
      uni.showModal({
        title: "撤销权限",
        content: "确认撤销该用户的资产只读权限吗？",
        success: async (modalRes) => {
          if (!modalRes.confirm) return
          this.permissionLoading = true
          try {
            const res = await adminRevokeUserPermission(this.uid, { permissionCode: PERMISSION_ASSET_READ_BASIC })
            const payload = (res && res.data) || {}
            if (!payload.ok) throw new Error(payload.msg || "撤销失败")
            uni.showToast({ title: "已撤销", icon: "success" })
            await this.fetchPermissions()
          } catch (e) {
            uni.showToast({ title: (e && e.message) || "撤销失败", icon: "none" })
          } finally {
            this.permissionLoading = false
          }
        }
      })
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
          this.fetchPermissions()
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
.permissionMeta { margin-top: 8px; }
.statusPill { padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.statusGranted { background: #ecfdf5; color: #047857; }
.statusExpired { background: #fff7ed; color: #c2410c; }
.statusPlain { background: #f8fafc; color: #475569; }
.sectionLabel { margin-top: 10px; }
.rowItem { margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(148, 163, 184, 0.2); }
</style>
