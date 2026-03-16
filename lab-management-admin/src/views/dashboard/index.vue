<template>
  <div class="dashboard-page">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="eyebrow">{{ roleLabel }}视图</span>
        <h2>{{ heroTitle }}</h2>
        <p>{{ heroDescription }}</p>
        <div class="hero-meta">
          <span>当前角色：{{ roleLabel }}</span>
          <span>数据更新时间：{{ generatedAtText }}</span>
        </div>
      </div>
      <div class="hero-actions">
        <el-button :loading="loading" @click="fetchDashboard">刷新数据</el-button>
      </div>
    </section>

    <section class="metric-grid">
      <article v-for="item in metricCards" :key="item.key" class="metric-card">
        <span class="metric-label">{{ item.label }}</span>
        <strong class="metric-value">{{ item.value }}</strong>
        <span class="metric-sub">{{ item.sub }}</span>
      </article>
    </section>

    <section v-if="isAdmin" class="panel-grid">
      <article class="panel-card panel-span-2">
        <div class="panel-head">
          <h3>近 7 天预约趋势</h3>
          <span>来自 `/admin/stats/dashboard`</span>
        </div>
        <div v-if="reservationTrend.length" class="trend-grid">
          <div
            v-for="item in reservationTrend"
            :key="item.date"
            class="trend-item"
          >
            <span class="trend-label">{{ item.label }}</span>
            <div class="trend-bar-wrap">
              <span class="trend-bar" :style="{ height: `${item.height}%` }" />
            </div>
            <strong>{{ item.count }}</strong>
          </div>
        </div>
        <el-empty v-else description="暂无近 7 天预约趋势数据" />
      </article>

      <article class="panel-card">
        <div class="panel-head">
          <h3>系统总览</h3>
          <span>关键运行指标</span>
        </div>
        <ul class="bullet-list">
          <li>实验室总数：{{ adminOverview.labsTotal }}</li>
          <li>用户总数：{{ adminOverview.usersTotal }}</li>
          <li>预约总数：{{ adminOverview.reservationsTotal }}</li>
          <li>待审批预约：{{ adminOverview.pendingReservations }}</li>
          <li>今日报修：{{ adminOverview.repairToday }}</li>
          <li>今日告警：{{ adminOverview.alarmsToday }}</li>
        </ul>
      </article>

      <article class="panel-card">
        <div class="panel-head">
          <h3>用户角色分布</h3>
          <span>当前账号结构</span>
        </div>
        <div class="stack-list">
          <div
            v-for="item in userRoleCards"
            :key="item.role"
            class="stack-item"
          >
            <div class="stack-text">
              <strong>{{ item.label }}</strong>
              <span>{{ item.count }} 人</span>
            </div>
            <div class="stack-track">
              <span class="stack-fill" :style="{ width: `${item.width}%` }" />
            </div>
          </div>
        </div>
      </article>

      <article class="panel-card">
        <div class="panel-head">
          <h3>近 30 天热门实验室</h3>
          <span>按预约量排序</span>
        </div>
        <div v-if="topLabs.length" class="rank-list">
          <div
            v-for="(item, index) in topLabs"
            :key="`${item.labName}-${index}`"
            class="rank-item"
          >
            <span class="rank-index">{{ index + 1 }}</span>
            <div class="rank-main">
              <strong>{{ item.labName }}</strong>
              <span>预约 {{ item.count }} 次，待审批 {{ item.pendingCount }} 次</span>
            </div>
            <span class="rank-side">已通过 {{ item.approvedCount }}</span>
          </div>
        </div>
        <el-empty v-else description="暂无实验室排行数据" />
      </article>

      <article class="panel-card">
        <div class="panel-head">
          <h3>最新公告</h3>
          <span>最近 5 条</span>
        </div>
        <div v-if="recentAnnouncements.length" class="timeline-list">
          <div
            v-for="item in recentAnnouncements"
            :key="item.id"
            class="timeline-item"
          >
            <div class="timeline-title">
              <strong>{{ item.title || '-' }}</strong>
              <el-tag size="small" :type="item.status === 'scheduled' ? 'warning' : 'success'">
                {{ item.status === 'scheduled' ? '待发布' : '已发布' }}
              </el-tag>
            </div>
            <span>{{ item.publisherName || '-' }} · {{ item.publishAt || '-' }}</span>
          </div>
        </div>
        <el-empty v-else description="暂无公告数据" />
      </article>

      <article class="panel-card panel-span-2">
        <div class="panel-head">
          <h3>最近审计日志</h3>
          <span>近 8 条系统操作</span>
        </div>
        <el-table :data="recentAudit" empty-text="暂无审计日志" stripe>
          <el-table-column prop="action" label="操作" min-width="180" />
          <el-table-column prop="operatorName" label="操作人" min-width="120" />
          <el-table-column prop="targetType" label="对象类型" min-width="120" />
          <el-table-column prop="targetId" label="对象 ID" min-width="120" />
          <el-table-column prop="createdAt" label="时间" min-width="180" />
        </el-table>
      </article>
    </section>

    <section v-else class="panel-grid">
      <article class="panel-card">
        <div class="panel-head">
          <h3>教师工作台摘要</h3>
          <span>来自 `/overview`</span>
        </div>
        <ul class="bullet-list">
          <li>我的预约总数：{{ memberMetrics.studentReservationCount }}</li>
          <li>待审批实验任务：{{ memberMetrics.teacherPendingReviewCount }}</li>
          <li>我的报修总数：{{ memberMetrics.studentRepairCount }}</li>
          <li>处理中报修：{{ memberMetrics.studentRepairActiveCount }}</li>
          <li>未读通知：{{ memberMetrics.studentUnreadCount }}</li>
        </ul>
      </article>

      <article class="panel-card">
        <div class="panel-head">
          <h3>通知构成</h3>
          <span>按类型统计</span>
        </div>
        <div class="stack-list">
          <div
            v-for="item in unreadCards"
            :key="item.key"
            class="stack-item"
          >
            <div class="stack-text">
              <strong>{{ item.label }}</strong>
              <span>{{ item.count }} 条</span>
            </div>
            <div class="stack-track">
              <span class="stack-fill" :style="{ width: `${item.width}%` }" />
            </div>
          </div>
        </div>
      </article>

      <article class="panel-card panel-span-2">
        <div class="panel-head">
          <h3>角色能力说明</h3>
          <span>{{ roleLabel }}</span>
        </div>
        <ul class="bullet-list">
          <li>当前后台优先开放仪表盘与预约审批，便于教师完成核心工作流。</li>
          <li>教师审批能力由后端 `review_role=teacher` 控制，前端仅负责展示和交互。</li>
          <li>公告发布、用户管理、报表中心等仍保持管理员独享，避免出现前端可见但后端拒绝的误导。</li>
        </ul>
      </article>
    </section>
  </div>
</template>

<script setup>
import { getAdminDashboard, getWorkbenchOverview } from '@/api/overview'
import { useAuthStore } from '@/stores/auth'
import { getRoleLabel } from '@/utils/auth'

const authStore = useAuthStore()
const loading = ref(false)
const adminDashboard = ref({})
const memberOverview = ref({})

const isAdmin = computed(() => authStore.role === 'admin')
const roleLabel = computed(() => getRoleLabel(authStore.role))
const heroTitle = computed(() => (isAdmin.value ? '后台运行总览' : '教师工作台概览'))
const heroDescription = computed(() => (
  isAdmin.value
    ? '聚合用户、实验室、预约、设备、公告和审计信息，帮助管理员快速掌握平台状态。'
    : '聚合我的预约、报修和通知数据，帮助教师优先处理当前待办。'
))

const generatedAtText = computed(() => {
  if (isAdmin.value) {
    return adminDashboard.value.generatedAt || '-'
  }
  return memberOverview.value.lastUpdated || '-'
})

const adminOverview = computed(() => adminDashboard.value.overview || {})
const memberMetrics = computed(() => memberOverview.value.metrics || {})
const memberUnreadMap = computed(() => memberOverview.value.meta?.unreadByType || {})
const reservationTrend = computed(() => {
  const rows = Array.isArray(adminDashboard.value.reservations?.trend7d)
    ? adminDashboard.value.reservations.trend7d
    : []
  const maxCount = Math.max(...rows.map((item) => Number(item.count || 0)), 1)
  return rows.map((item) => ({
    date: item.date || '',
    label: item.label || item.date || '-',
    count: Number(item.count || 0),
    height: Math.max((Number(item.count || 0) / maxCount) * 100, Number(item.count || 0) > 0 ? 12 : 4)
  }))
})

const userRoleCards = computed(() => {
  const byRole = adminDashboard.value.users?.byRole || {}
  const total = Math.max(Number(adminDashboard.value.users?.total || 0), 1)
  return [
    { role: 'admin', label: '管理员', count: Number(byRole.admin || 0) },
    { role: 'teacher', label: '教师', count: Number(byRole.teacher || 0) },
    { role: 'student', label: '学生', count: Number(byRole.student || 0) }
  ].map((item) => ({
    ...item,
    width: Math.max((item.count / total) * 100, item.count > 0 ? 8 : 0)
  }))
})

const unreadCards = computed(() => {
  const map = memberUnreadMap.value
  const items = [
    { key: 'reservation', label: '预约通知', count: Number(map.reservation || 0) },
    { key: 'repair', label: '报修通知', count: Number(map.repair || 0) },
    { key: 'asset_borrow', label: '借用通知', count: Number(map.asset_borrow || 0) },
    { key: 'course_task', label: '课程任务', count: Number(map.course_task || 0) },
    { key: 'lostfound', label: '失物招领', count: Number(map.lostfound || 0) }
  ]
  const maxCount = Math.max(...items.map((item) => item.count), 1)
  return items.map((item) => ({
    ...item,
    width: Math.max((item.count / maxCount) * 100, item.count > 0 ? 10 : 0)
  }))
})

const topLabs = computed(() => (
  Array.isArray(adminDashboard.value.topLabs30d) ? adminDashboard.value.topLabs30d : []
))
const recentAnnouncements = computed(() => (
  Array.isArray(adminDashboard.value.announcements?.recent) ? adminDashboard.value.announcements.recent : []
))
const recentAudit = computed(() => (
  Array.isArray(adminDashboard.value.recentAudit) ? adminDashboard.value.recentAudit : []
))

const metricCards = computed(() => {
  if (isAdmin.value) {
    return [
      {
        key: 'users',
        label: '用户总数',
        value: adminDashboard.value.users?.total || 0,
        sub: `教师 ${adminDashboard.value.users?.byRole?.teacher || 0} / 学生 ${adminDashboard.value.users?.byRole?.student || 0}`
      },
      {
        key: 'reservations',
        label: '预约总数',
        value: adminDashboard.value.reservations?.total || 0,
        sub: `今日 ${adminDashboard.value.reservations?.today || 0} / 待审批 ${adminOverview.value.pendingReservations || 0}`
      },
      {
        key: 'equipment',
        label: '设备总数',
        value: adminDashboard.value.equipment?.total || 0,
        sub: `维修中 ${adminDashboard.value.equipment?.repairing || 0} / 报废 ${adminDashboard.value.equipment?.scrapped || 0}`
      },
      {
        key: 'announcements',
        label: '公告总数',
        value: adminDashboard.value.announcements?.total || 0,
        sub: `已发布 ${adminDashboard.value.announcements?.published || 0} / 待发布 ${adminDashboard.value.announcements?.scheduled || 0}`
      }
    ]
  }

  return [
    {
      key: 'teacher-reservation',
      label: '我的预约',
      value: memberMetrics.value.studentReservationCount || 0,
      sub: `待审核任务 ${memberMetrics.value.teacherPendingReviewCount || 0}`
    },
    {
      key: 'teacher-repair',
      label: '我的报修',
      value: memberMetrics.value.studentRepairCount || 0,
      sub: `处理中 ${memberMetrics.value.studentRepairActiveCount || 0}`
    },
    {
      key: 'teacher-borrow',
      label: '借用待处理',
      value: memberMetrics.value.studentBorrowPendingCount || 0,
      sub: '来自工作台概览'
    },
    {
      key: 'teacher-notice',
      label: '未读通知',
      value: memberMetrics.value.studentUnreadCount || 0,
      sub: '包含预约、报修、课程等提醒'
    }
  ]
})

async function fetchDashboard() {
  loading.value = true
  try {
    if (isAdmin.value) {
      const response = await getAdminDashboard()
      adminDashboard.value = response.data?.data || {}
      return
    }

    const response = await getWorkbenchOverview()
    memberOverview.value = response.data?.data || {}
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
.metric-card,
.panel-card {
  border: 1px solid var(--app-border);
  border-radius: 24px;
  background: var(--app-surface);
  box-shadow: var(--app-shadow);
}

.hero-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 28px;
  background:
    radial-gradient(circle at top right, rgba(13, 148, 136, 0.12), transparent 32%),
    linear-gradient(135deg, #fbfffe 0%, #eef8f6 100%);
}

.hero-copy {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hero-card h2,
.panel-head h3 {
  margin: 0;
}

.hero-card p,
.metric-label,
.metric-sub,
.panel-head span,
.hero-meta {
  color: var(--app-muted);
}

.hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 13px;
}

.eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: var(--app-primary-soft);
  color: #115e59;
  font-size: 12px;
  font-weight: 700;
}

.metric-grid,
.panel-grid,
.trend-grid {
  display: grid;
  gap: 20px;
}

.metric-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.metric-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 24px;
}

.metric-value {
  font-size: 32px;
}

.panel-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.panel-card {
  padding: 24px;
}

.panel-span-2 {
  grid-column: span 2;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.bullet-list {
  margin: 0;
  padding-left: 18px;
  color: #334155;
  line-height: 1.9;
}

.trend-grid {
  grid-template-columns: repeat(7, minmax(0, 1fr));
  align-items: end;
  min-height: 220px;
}

.trend-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.trend-label {
  font-size: 12px;
  color: var(--app-muted);
}

.trend-bar-wrap {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  width: 100%;
  height: 140px;
  padding: 12px;
  border-radius: 20px;
  background: #f1f5f9;
}

.trend-bar {
  width: 100%;
  border-radius: 999px;
  background: linear-gradient(180deg, #0f766e 0%, #14b8a6 100%);
}

.stack-list,
.rank-list,
.timeline-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.stack-item,
.rank-item,
.timeline-item {
  padding: 14px 16px;
  border-radius: 18px;
  background: #f8fafc;
}

.stack-text,
.timeline-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.stack-text span,
.rank-main span,
.timeline-item span {
  color: var(--app-muted);
  font-size: 13px;
}

.stack-track {
  height: 8px;
  border-radius: 999px;
  background: #e2e8f0;
  overflow: hidden;
}

.stack-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #0f766e 0%, #2dd4bf 100%);
}

.rank-item {
  display: flex;
  align-items: center;
  gap: 14px;
}

.rank-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--app-primary-soft);
  color: #115e59;
  font-weight: 700;
}

.rank-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rank-side {
  font-size: 13px;
  color: #0f766e;
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
    align-items: flex-start;
  }

  .metric-grid,
  .panel-grid,
  .trend-grid {
    grid-template-columns: 1fr;
  }

  .panel-span-2 {
    grid-column: span 1;
  }

  .rank-item,
  .stack-text,
  .timeline-title {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
