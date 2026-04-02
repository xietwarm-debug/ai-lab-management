<template>
  <div class="dashboard-page">
    <section class="hero-card">
      <div>
        <p class="eyebrow">管理总览</p>
        <h1>仪表盘</h1>
        <p class="hero-desc">
          聚合核心指标、风险提醒和快捷入口，帮助{{ roleLabel }}快速了解当前运行状态。
        </p>
        <div class="hero-meta">
          <span>当前账号 {{ authStore.username || '-' }}</span>
          <span>角色 {{ roleLabel }}</span>
          <span>最近更新 {{ lastUpdatedText }}</span>
        </div>
      </div>
      <div class="hero-actions">
        <el-button @click="fetchDashboard" :loading="loading" :icon="RefreshRight">刷新仪表盘</el-button>
        <el-button type="primary" @click="goTo(primaryAction.path)">{{ primaryAction.label }}</el-button>
      </div>
    </section>

    <section class="metric-grid">
      <article
        v-for="item in summaryCards"
        :key="item.key"
        class="metric-card"
        :class="item.tone"
      >
        <span class="metric-label">{{ item.label }}</span>
        <strong class="metric-value">{{ item.value }}</strong>
        <span class="metric-sub">{{ item.description }}</span>
      </article>
    </section>

    <section class="panel-grid">
      <article class="panel-card panel-span-2">
        <div class="panel-head">
          <div>
            <h3>业务概览</h3>
            <span>按模块查看当前压力点与库存状态</span>
          </div>
        </div>
        <div class="overview-grid">
          <div v-for="item in businessCards" :key="item.key" class="overview-item">
            <div class="overview-top">
              <strong>{{ item.label }}</strong>
              <el-tag size="small" :type="item.tagType">{{ item.tagText }}</el-tag>
            </div>
            <div class="overview-value">{{ item.value }}</div>
            <p>{{ item.detail }}</p>
          </div>
        </div>
      </article>

      <article class="panel-card">
        <div class="panel-head">
          <div>
            <h3>快捷入口</h3>
            <span>保留最常用的后台动作</span>
          </div>
        </div>
        <div class="quick-list">
          <button
            v-for="item in quickActions"
            :key="item.path"
            type="button"
            class="quick-item"
            @click="goTo(item.path)"
          >
            <strong>{{ item.label }}</strong>
            <span>{{ item.desc }}</span>
          </button>
        </div>
      </article>

      <article class="panel-card panel-span-2">
        <div class="panel-head">
          <div>
            <h3>近 7 天预约趋势</h3>
            <span>帮助判断高峰时段与审批压力</span>
          </div>
        </div>
        <div v-if="trendRows.length" class="trend-grid">
          <div v-for="item in trendRows" :key="item.date" class="trend-col">
            <span class="trend-label">{{ item.label }}</span>
            <div class="trend-bar-wrap">
              <span class="trend-bar" :style="{ height: `${item.height}%` }" />
            </div>
            <span class="trend-value">{{ item.value }}</span>
          </div>
        </div>
        <el-empty v-else description="暂无趋势数据" :image-size="60" />
      </article>

      <article class="panel-card">
        <div class="panel-head">
          <div>
            <h3>热门实验室</h3>
            <span>近 30 天使用热度排名</span>
          </div>
        </div>
        <div v-if="topLabs.length" class="rank-list">
          <div v-for="(item, index) in topLabs" :key="item.labId || item.labName || index" class="rank-item">
            <span class="rank-index">{{ index + 1 }}</span>
            <div class="rank-copy">
              <strong>{{ item.labName || '未命名实验室' }}</strong>
              <span>{{ item.reservationCount || 0 }} 次预约 / {{ item.userCount || 0 }} 人使用</span>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无实验室热度数据" :image-size="60" />
      </article>

      <article class="panel-card">
        <div class="panel-head">
          <div>
            <h3>最新公告</h3>
            <span>最近发布或排期的通知</span>
          </div>
          <el-button link type="primary" @click="goTo('/announcements')">查看全部</el-button>
        </div>
        <div v-if="recentAnnouncements.length" class="timeline-list">
          <div v-for="item in recentAnnouncements" :key="item.id" class="timeline-item">
            <strong>{{ item.title || '未命名公告' }}</strong>
            <span>{{ item.publishTime || item.createdAt || '-' }}</span>
          </div>
        </div>
        <el-empty v-else description="暂无公告" :image-size="60" />
      </article>

      <article class="panel-card">
        <div class="panel-head">
          <div>
            <h3>最近审计日志</h3>
            <span>便于快速确认近期关键操作</span>
          </div>
          <el-button link type="primary" @click="goTo('/audit-logs')">查看全部</el-button>
        </div>
        <div v-if="recentAudit.length" class="timeline-list">
          <div v-for="(item, index) in recentAudit" :key="`${item.createdAt}-${index}`" class="timeline-item">
            <strong>{{ item.action || '系统操作' }}</strong>
            <span>{{ item.createdAt || '-' }}</span>
          </div>
        </div>
        <el-empty v-else description="暂无审计记录" :image-size="60" />
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RefreshRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { getAdminDashboard, getWorkbenchOverview } from '@/api/overview'
import { useAuthStore } from '@/stores/auth'
import {
  PERMISSION_ASSET_MANAGER,
  PERMISSION_AUDIT_VIEWER,
  PERMISSION_DUTY_OPERATOR,
  PERMISSION_SCHEDULE_MANAGER,
  ROLE_LABEL_MAP
} from '@/utils/constants'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const adminDashboard = ref({})
const workbenchOverview = ref({})

const isAdmin = computed(() => authStore.role === 'admin')
const lastUpdatedText = computed(() => (
  adminDashboard.value.generatedAt
  || workbenchOverview.value.lastUpdated
  || '-'
))
const roleLabel = computed(() => ROLE_LABEL_MAP[authStore.role] || authStore.role || '未知角色')

const adminOverview = computed(() => adminDashboard.value.overview || {})
const adminLabs = computed(() => adminDashboard.value.labs || {})
const adminReservations = computed(() => adminDashboard.value.reservations || {})
const adminEquipment = computed(() => adminDashboard.value.equipment || {})
const adminRepair = computed(() => adminDashboard.value.repair || {})
const adminLostFound = computed(() => adminDashboard.value.lostFound || {})
const overviewMetrics = computed(() => workbenchOverview.value.metrics || {})
const topLabs = computed(() => Array.isArray(adminDashboard.value.topLabs30d) ? adminDashboard.value.topLabs30d.slice(0, 5) : [])
const recentAnnouncements = computed(() => Array.isArray(adminDashboard.value.announcements?.recent) ? adminDashboard.value.announcements.recent.slice(0, 5) : [])
const recentAudit = computed(() => Array.isArray(adminDashboard.value.recentAudit) ? adminDashboard.value.recentAudit.slice(0, 5) : [])

const primaryAction = computed(() => {
  if (isAdmin.value) {
    return {
      label: Number(overviewMetrics.value.pendingCount || 0) > 0 ? '进入待办中心' : '查看通知中心',
      path: Number(overviewMetrics.value.pendingCount || 0) > 0 ? '/todo-center' : '/notification-center'
    }
  }
  return {
    label: '查看预约审批',
    path: '/reservations'
  }
})

const summaryCards = computed(() => {
  if (isAdmin.value) {
    return [
      {
        key: 'pending',
        label: '待审批预约',
        value: adminOverview.value.pendingReservations || 0,
        description: '当前等待管理员处理的预约申请',
        tone: 'primary'
      },
      {
        key: 'labs',
        label: '实验室总数',
        value: adminOverview.value.labsTotal || 0,
        description: `空闲 ${adminLabs.value.free || 0} / 忙碌 ${adminLabs.value.busy || 0}`,
        tone: 'info'
      },
      {
        key: 'repair',
        label: '今日报修',
        value: adminOverview.value.repairToday || 0,
        description: `处理中 ${adminRepair.value.byStatus?.processing || 0} 单`,
        tone: 'warning'
      },
      {
        key: 'alarm',
        label: '今日告警',
        value: adminOverview.value.alarmsToday || 0,
        description: '建议优先核查高风险实验室与设备',
        tone: 'danger'
      }
    ]
  }
  return [
    {
      key: 'review',
      label: '待审核预约',
      value: overviewMetrics.value.teacherPendingReviewCount || 0,
      description: '当前由你处理的预约审核事项',
      tone: 'primary'
    },
    {
      key: 'notice',
      label: '未读消息',
      value: overviewMetrics.value.studentUnreadCount || 0,
      description: '统一消息流中的未读提醒',
      tone: 'info'
    },
    {
      key: 'repair',
      label: '报修进行中',
      value: overviewMetrics.value.studentRepairActiveCount || 0,
      description: '你提交且尚未关闭的报修工单',
      tone: 'warning'
    },
    {
      key: 'reserve',
      label: '我的预约',
      value: overviewMetrics.value.studentReservationCount || 0,
      description: '包含已完成与待审核预约',
      tone: 'success'
    }
  ]
})

const businessCards = computed(() => {
  if (!isAdmin.value) {
    return [
      {
        key: 'teacher-pending',
        label: '教学审核',
        value: overviewMetrics.value.teacherPendingReviewCount || 0,
        detail: '重点关注即将开课的预约审核。',
        tagType: Number(overviewMetrics.value.teacherPendingReviewCount || 0) > 0 ? 'warning' : 'success',
        tagText: Number(overviewMetrics.value.teacherPendingReviewCount || 0) > 0 ? '待处理' : '平稳'
      },
      {
        key: 'teacher-msg',
        label: '消息提醒',
        value: overviewMetrics.value.studentUnreadCount || 0,
        detail: '统一查看审批、借用、报修等通知。',
        tagType: Number(overviewMetrics.value.studentUnreadCount || 0) > 0 ? 'primary' : 'info',
        tagText: Number(overviewMetrics.value.studentUnreadCount || 0) > 0 ? '有更新' : '最新'
      }
    ]
  }

  const pendingReservations = Number(adminOverview.value.pendingReservations || 0)
  const activeRepairs = Number(
    (adminRepair.value.byStatus?.submitted || 0)
    + (adminRepair.value.byStatus?.accepted || 0)
    + (adminRepair.value.byStatus?.processing || 0)
  )
  const repairingEquipments = Number(adminEquipment.value.repairing || 0)
  const pendingClaims = Number(adminLostFound.value.claimPending || 0)

  return [
    {
      key: 'reservation',
      label: '预约审批',
      value: pendingReservations,
      detail: `今日新增 ${adminReservations.value.today || 0} 条预约，近 7 天共 ${adminReservations.value.recent7dTotal || 0} 条。`,
      tagType: pendingReservations > 0 ? 'warning' : 'success',
      tagText: pendingReservations > 0 ? '待处理' : '平稳'
    },
    {
      key: 'repair',
      label: '维修工单',
      value: activeRepairs,
      detail: `今日报修 ${adminOverview.value.repairToday || 0} 单，已完成 ${adminRepair.value.byStatus?.completed || 0} 单。`,
      tagType: activeRepairs > 0 ? 'warning' : 'success',
      tagText: activeRepairs > 0 ? '处理中' : '正常'
    },
    {
      key: 'equipment',
      label: '设备状态',
      value: repairingEquipments,
      detail: `在库 ${adminEquipment.value.total || 0} 台，报废 ${adminEquipment.value.scrapped || 0} 台。`,
      tagType: repairingEquipments > 0 ? 'danger' : 'success',
      tagText: repairingEquipments > 0 ? '需关注' : '稳定'
    },
    {
      key: 'lost-found',
      label: '失物招领',
      value: pendingClaims,
      detail: `开放中 ${adminLostFound.value.open || 0} 条，待认领审核 ${pendingClaims} 条。`,
      tagType: pendingClaims > 0 ? 'primary' : 'info',
      tagText: pendingClaims > 0 ? '待审核' : '常态'
    }
  ]
})

const trendRows = computed(() => {
  const rows = Array.isArray(adminReservations.value.trend7d) ? adminReservations.value.trend7d : []
  const maxValue = Math.max(...rows.map((item) => Number(item.count || 0)), 1)
  return rows.map((item) => ({
    ...item,
    value: Number(item.count || 0),
    height: Math.max((Number(item.count || 0) / maxValue) * 100, Number(item.count || 0) > 0 ? 18 : 6)
  }))
})

const quickActions = computed(() => {
  const items = [
    { label: '待办中心', desc: '集中处理审批与异常事项', path: '/todo-center', adminOnly: true },
    { label: '通知中心', desc: '查看统一消息流与提醒', path: '/notification-center', adminOnly: true },
    { label: '预约审批', desc: '进入预约列表快速审批', path: '/reservations' },
    { label: '实验室管理', desc: '查看实验室状态与平面图', path: '/labs' }
  ]

  if (hasPermission(PERMISSION_DUTY_OPERATOR)) {
    items.push({ label: '运营看板', desc: '查看运行态势与风险', path: '/operations-board' })
  }
  if (hasPermission(PERMISSION_ASSET_MANAGER)) {
    items.push({ label: '资产管理', desc: '检查设备状态与借用', path: '/equipments', adminOnly: true })
  }
  if (hasPermission(PERMISSION_SCHEDULE_MANAGER)) {
    items.push({ label: '排课管理', desc: '处理课表和门禁提醒', path: '/schedule-manage', adminOnly: true })
  }
  if (hasPermission(PERMISSION_AUDIT_VIEWER)) {
    items.push({ label: '审计日志', desc: '追踪关键后台操作', path: '/audit-logs', adminOnly: true })
  }

  return items.filter((item) => !(item.adminOnly && !isAdmin.value)).slice(0, 6)
})

function hasPermission(permission) {
  return authStore.permissions.includes(permission)
}

function goTo(path) {
  if (!path) return
  router.push(path)
}

async function fetchDashboard() {
  loading.value = true
  try {
    const tasks = [getWorkbenchOverview()]
    if (isAdmin.value) tasks.push(getAdminDashboard())

    const [overviewResp, adminResp] = await Promise.all(tasks)
    workbenchOverview.value = overviewResp.data?.data || {}
    if (isAdmin.value) {
      adminDashboard.value = adminResp?.data?.data || {}
    } else {
      adminDashboard.value = {}
    }
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || '加载仪表盘失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchDashboard()
})
</script>

<style scoped lang="scss">
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-card,
.panel-card,
.metric-card {
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 20px;
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.08);
}

.hero-card {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  padding: 28px 32px;
  background:
    radial-gradient(circle at top right, rgba(15, 118, 110, 0.16), transparent 38%),
    linear-gradient(135deg, #ffffff, #f5fbfa);

  h1 {
    margin: 6px 0 10px;
    font-size: 32px;
    color: #17202a;
  }
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.1);
  color: #0f766e;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.hero-desc {
  margin: 0;
  max-width: 720px;
  color: #5b6574;
  line-height: 1.6;
}

.hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 16px;
  color: #6b7280;
  font-size: 13px;
}

.hero-actions {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  flex-shrink: 0;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.metric-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 20px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 18px 42px rgba(15, 23, 42, 0.1);
  }

  &.primary {
    background: linear-gradient(180deg, #eff6ff 0%, #fff 100%);
  }

  &.info {
    background: linear-gradient(180deg, #f0fdfa 0%, #fff 100%);
  }

  &.warning {
    background: linear-gradient(180deg, #fffbeb 0%, #fff 100%);
  }

  &.danger {
    background: linear-gradient(180deg, #fef2f2 0%, #fff 100%);
  }

  &.success {
    background: linear-gradient(180deg, #ecfdf5 0%, #fff 100%);
  }
}

.metric-label {
  color: #6b7280;
  font-size: 13px;
}

.metric-value {
  font-size: 32px;
  line-height: 1;
  color: #17202a;
}

.metric-sub {
  color: #7b8694;
  font-size: 13px;
  line-height: 1.5;
}

.panel-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.panel-card {
  padding: 20px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 18px 42px rgba(15, 23, 42, 0.1);
  }
}

.panel-span-2 {
  grid-column: span 2;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 16px;

  h3 {
    margin: 0 0 4px;
    font-size: 18px;
    color: #17202a;
  }

  span {
    color: #7b8694;
    font-size: 13px;
  }
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.overview-item {
  padding: 16px;
  border-radius: 16px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;

  p {
    margin: 8px 0 0;
    color: #6b7280;
    font-size: 13px;
    line-height: 1.6;
  }
}

.overview-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.overview-value {
  margin-top: 12px;
  font-size: 28px;
  font-weight: 700;
  color: #17202a;
}

.quick-list,
.timeline-list,
.rank-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.quick-item,
.timeline-item,
.rank-item {
  width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #f8fafc;
  padding: 14px 16px;
}

.quick-item {
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;

  strong,
  span {
    display: block;
  }

  strong {
    color: #17202a;
    margin-bottom: 6px;
  }

  span {
    color: #6b7280;
    font-size: 13px;
  }

  &:hover {
    border-color: rgba(15, 118, 110, 0.28);
    transform: translateY(-1px);
  }
}

.timeline-item {
  strong,
  span {
    display: block;
  }

  strong {
    color: #17202a;
    margin-bottom: 6px;
  }

  span {
    color: #6b7280;
    font-size: 13px;
  }
}

.rank-item {
  display: flex;
  gap: 12px;
  align-items: center;
}

.rank-index {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: #0f766e;
  color: #fff;
  font-weight: 700;
  flex-shrink: 0;
}

.rank-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;

  strong {
    color: #17202a;
  }

  span {
    color: #6b7280;
    font-size: 13px;
  }
}

.trend-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 12px;
  align-items: end;
  min-height: 240px;
}

.trend-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.trend-label,
.trend-value {
  font-size: 12px;
  color: #6b7280;
}

.trend-bar-wrap {
  width: 100%;
  min-height: 160px;
  display: flex;
  align-items: end;
  justify-content: center;
  padding: 0 8px;
}

.trend-bar {
  width: 100%;
  border-radius: 14px 14px 6px 6px;
  background: linear-gradient(180deg, #0f766e 0%, #34d399 100%);
}

@media (max-width: 1200px) {
  .metric-grid,
  .panel-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .panel-span-2 {
    grid-column: span 2;
  }
}

@media (max-width: 768px) {
  .hero-card {
    flex-direction: column;
    padding: 24px;
  }

  .hero-actions {
    flex-wrap: wrap;
  }

  .metric-grid,
  .panel-grid,
  .overview-grid {
    grid-template-columns: 1fr;
  }

  .panel-span-2 {
    grid-column: span 1;
  }

  .trend-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
</style>
