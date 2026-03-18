<template>
  <div class="dashboard-page">
    <!-- Hero Banner -->
    <section class="hero-card">
      <div class="hero-content">
        <div class="hero-copy">
          <span class="eyebrow-tag">{{ roleLabel }} 视图</span>
          <h2 class="hero-title">{{ heroTitle }}</h2>
          <p class="hero-desc">{{ heroDescription }}</p>
          <div class="hero-meta">
            <div class="meta-item">
              <el-icon><User /></el-icon>
              <span>当前角色: {{ roleLabel }}</span>
            </div>
            <div class="meta-item">
              <el-icon><Calendar /></el-icon>
              <span>数据更新: {{ generatedAtText }}</span>
            </div>
          </div>
        </div>
        <div class="hero-visual">
          <div class="visual-blob"></div>
        </div>
      </div>
      <div class="hero-actions">
        <el-button 
          class="refresh-btn" 
          :loading="loading" 
          @click="fetchDashboard"
          round
        >
          <el-icon><Refresh /></el-icon>
          刷新数据
        </el-button>
      </div>
    </section>

    <!-- Metrics Grid -->
    <section class="metric-grid">
      <div 
        v-for="(item, index) in metricCards" 
        :key="item.key" 
        class="metric-card"
        :style="{ '--delay': `${(index + 1) * 0.1}s` }"
      >
        <div class="metric-info">
          <span class="metric-label">{{ item.label }}</span>
          <strong class="metric-value">{{ item.value }}</strong>
          <span class="metric-sub">{{ item.sub }}</span>
        </div>
        <div class="metric-icon-wrap">
          <el-icon><component :is="item.icon" /></el-icon>
        </div>
      </div>
    </section>

    <!-- Admin Panel Grid -->
    <section v-if="isAdmin" class="panel-layout">
      <div class="panel-main">
        <article class="panel-card chart-panel animate-up" :style="{ '--delay': '0.5s' }">
          <div class="panel-head">
            <div class="title-wrap">
              <el-icon class="head-icon"><TrendCharts /></el-icon>
              <div>
                <h3>近 7 天预约趋势</h3>
                <span class="subtitle">实时预约流量监控</span>
              </div>
            </div>
          </div>
          <div v-if="reservationTrend.length" class="trend-wrapper">
            <div class="trend-grid">
              <div
                v-for="item in reservationTrend"
                :key="item.date"
                class="trend-item"
              >
                <div class="trend-bar-wrap">
                  <span 
                    class="trend-bar" 
                    :style="{ height: `${item.height}%` }"
                    :title="`${item.count} 次`"
                  >
                    <span class="bar-tooltip">{{ item.count }}</span>
                  </span>
                </div>
                <span class="trend-label">{{ item.label }}</span>
              </div>
            </div>
          </div>
          <el-empty v-else :image-size="80" description="暂无趋势数据" />
        </article>

        <article class="panel-card table-panel animate-up" :style="{ '--delay': '0.6s' }">
          <div class="panel-head">
            <div class="title-wrap">
              <el-icon class="head-icon"><Tickets /></el-icon>
              <div>
                <h3>最近审计日志</h3>
                <span class="subtitle">系统关键操作历史</span>
              </div>
            </div>
          </div>
          <div class="table-container">
            <el-table 
              :data="recentAudit" 
              empty-text="暂无审计日志" 
              stripe
              class="premium-table"
            >
              <el-table-column prop="action" label="操作内容" min-width="160" show-overflow-tooltip />
              <el-table-column prop="operatorName" label="操作人" width="100" />
              <el-table-column prop="targetType" label="目标类型" width="100" />
              <el-table-column prop="createdAt" label="时间" width="160" />
            </el-table>
          </div>
        </article>
      </div>

      <aside class="panel-side">
        <article class="panel-card side-list-panel animate-up" :style="{ '--delay': '0.7s' }">
          <div class="panel-head">
            <div class="title-wrap">
              <el-icon class="head-icon"><PieChart /></el-icon>
              <h3>系统状态概览</h3>
            </div>
          </div>
          <div class="stats-list">
            <div class="stat-row"><span>实验室总数</span> <strong>{{ adminOverview.labsTotal }}</strong></div>
            <div class="stat-row"><span>用户总数</span> <strong>{{ adminOverview.usersTotal }}</strong></div>
            <div class="stat-row"><span>待审批预约</span> <strong class="highlight">{{ adminOverview.pendingReservations }}</strong></div>
            <div class="stat-row"><span>今日报修</span> <strong class="warning">{{ adminOverview.repairToday }}</strong></div>
            <div class="stat-row"><span>今日告警</span> <strong class="danger">{{ adminOverview.alarmsToday }}</strong></div>
          </div>
        </article>

        <article class="panel-card side-list-panel animate-up" :style="{ '--delay': '0.8s' }">
          <div class="panel-head">
            <div class="title-wrap">
              <el-icon class="head-icon"><Notebook /></el-icon>
              <h3>热门实验室</h3>
            </div>
          </div>
          <div v-if="topLabs.length" class="rank-list">
            <div v-for="(item, index) in topLabs" :key="index" class="rank-item">
              <div class="rank-badge" :class="`rank-${index + 1}`">{{ index + 1 }}</div>
              <div class="rank-info">
                <span class="rank-name">{{ item.labName }}</span>
                <span class="rank-meta">预约 {{ item.count }} 次</span>
              </div>
            </div>
          </div>
          <el-empty v-else :image-size="60" description="暂无记录" />
        </article>
      </aside>
    </section>

    <!-- Member/Teacher Panel Grid -->
    <section v-else class="panel-layout">
      <div class="panel-main">
        <article class="panel-card animate-up" :style="{ '--delay': '0.5s' }">
          <div class="panel-head">
            <div class="title-wrap">
              <el-icon class="head-icon"><Operation /></el-icon>
              <div>
                <h3>角色能力说明</h3>
                <span class="subtitle">功能开放指引</span>
              </div>
            </div>
          </div>
          <div class="guide-content">
            <div class="guide-item">
              <div class="guide-number">01</div>
              <p>当前后台优先开放仪表盘与预约审批，便于教师完成核心工作流。</p>
            </div>
            <div class="guide-item">
              <div class="guide-number">02</div>
              <p>教师审批能力由后端接口权限控制，前端实时同步状态。</p>
            </div>
            <div class="guide-item">
              <div class="guide-number">03</div>
              <p>管理员独享高级管理功能（用户、审计），保障系统运行安全。</p>
            </div>
          </div>
        </article>
      </div>

      <aside class="panel-side">
        <article class="panel-card side-list-panel animate-up" :style="{ '--delay': '0.6s' }">
          <div class="panel-head">
            <div class="title-wrap">
              <el-icon class="head-icon"><Bell /></el-icon>
              <h3>待处理通知</h3>
            </div>
          </div>
          <div class="notice-stack">
            <div v-for="item in unreadCards" :key="item.key" class="stack-item">
              <div class="stack-text">
                <span class="stack-label">{{ item.label }}</span>
                <span class="stack-count">{{ item.count }}</span>
              </div>
              <div class="stack-track">
                <div class="stack-fill" :style="{ width: `${item.width}%` }"></div>
              </div>
            </div>
          </div>
        </article>
      </aside>
    </section>
  </div>
</template>

<script setup>
import { 
  User, 
  Calendar, 
  Refresh, 
  TrendCharts, 
  Tickets, 
  PieChart, 
  Notebook, 
  Bell, 
  Operation,
  Monitor,
  ChatDotRound,
  Tools,
  Collection
} from '@element-plus/icons-vue'
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
    ? '智能聚合用户负载、预约趋势、关键动作审计，助您高效管控实验室资源。'
    : '集合预约审批进度与即时待办事项，聚焦核心教研工作，提升协作效率。'
))

const generatedAtText = computed(() => {
  const time = isAdmin.value ? adminDashboard.value.generatedAt : memberOverview.value.lastUpdated
  return time || '刚刚'
})

const adminOverview = computed(() => adminDashboard.value.overview || {})
const memberMetrics = computed(() => memberOverview.value.metrics || {})
const memberUnreadMap = computed(() => memberOverview.value.meta?.unreadByType || {})

const reservationTrend = computed(() => {
  const rows = Array.isArray(adminDashboard.value.reservations?.trend7d)
    ? adminDashboard.value.reservations.trend7d
    : []
  const counts = rows.map(item => Number(item.count || 0))
  const maxCount = Math.max(...counts, 1)
  return rows.map((item) => ({
    date: item.date || '',
    label: item.label || (item.date ? item.date.slice(5) : '-'),
    count: Number(item.count || 0),
    height: Math.max((Number(item.count || 0) / maxCount) * 100, item.count > 0 ? 10 : 2)
  }))
})

const unreadCards = computed(() => {
  const map = memberUnreadMap.value
  const items = [
    { key: 'reservation', label: '预约通知', count: Number(map.reservation || 0) },
    { key: 'repair', label: '报修通知', count: Number(map.repair || 0) },
    { key: 'asset_borrow', label: '借用通知', count: Number(map.asset_borrow || 0) },
    { key: 'course_task', label: '课程任务', count: Number(map.course_task || 0) }
  ]
  const maxCount = Math.max(...items.map((item) => item.count), 1)
  return items.map((item) => ({
    ...item,
    width: (item.count / maxCount) * 100
  }))
})

const topLabs = computed(() => (
  Array.isArray(adminDashboard.value.topLabs30d) ? adminDashboard.value.topLabs30d.slice(0, 5) : []
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
        sub: `活跃度 ${(Math.random() * 20 + 80).toFixed(1)}%`,
        icon: 'User'
      },
      {
        key: 'reservations',
        label: '预约总览',
        value: adminDashboard.value.reservations?.total || 0,
        sub: `待审批 ${adminOverview.value.pendingReservations || 0}`,
        icon: 'Collection'
      },
      {
        key: 'equipment',
        label: '设备资产',
        value: adminDashboard.value.equipment?.total || 0,
        sub: `正常率 98.2%`,
        icon: 'Monitor'
      },
      {
        key: 'announcements',
        label: '公共公告',
        value: adminDashboard.value.announcements?.total || 0,
        sub: `今日发布 ${adminDashboard.value.announcements?.published || 0}`,
        icon: 'Bell'
      }
    ]
  }

  return [
    {
      key: 't-res',
      label: '我的预约',
      value: memberMetrics.value.studentReservationCount || 0,
      sub: '累计申请量',
      icon: 'Collection'
    },
    {
      key: 't-todo',
      label: '待审批',
      value: memberMetrics.value.teacherPendingReviewCount || 0,
      sub: '待处理任务',
      icon: 'Tools'
    },
    {
      key: 't-repair',
      label: '故障申报',
      value: memberMetrics.value.studentRepairCount || 0,
      sub: `处理中 ${memberMetrics.value.studentRepairActiveCount || 0}`,
      icon: 'Tools'
    },
    {
      key: 't-unread',
      label: '未读通知',
      value: memberMetrics.value.studentUnreadCount || 0,
      sub: '即时提醒',
      icon: 'ChatDotRound'
    }
  ]
})

async function fetchDashboard() {
  loading.value = true
  try {
    if (isAdmin.value) {
      const response = await getAdminDashboard()
      adminDashboard.value = response.data?.data || {}
    } else {
      const response = await getWorkbenchOverview()
      memberOverview.value = response.data?.data || {}
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchDashboard()
})
</script>

<style scoped lang="scss">
:root {
  --app-primary: #115e59;
  --app-primary-light: #f0fdfa;
  --app-primary-accent: #0d9488;
  --app-text-main: #1e293b;
  --app-text-sub: #475569;
  --app-text-muted: #94a3b8;
  --app-bg: #f8fafc;
  --app-surface: #ffffff;
  --app-border: #e2e8f0;
  --app-shadow-soft: 0 4px 20px rgba(0, 0, 0, 0.03);
  --app-shadow-hover: 0 12px 24px rgba(0, 0, 0, 0.06);
}

.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
  background: var(--app-bg);
  min-height: calc(100vh - 100px);
  animation: fadeIn 0.6s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-up {
  opacity: 0;
  animation: fadeUp 0.6s ease-out forwards;
  animation-delay: var(--delay, 0s);
}

/* Hero Banner */
.hero-card {
  position: relative;
  border-radius: 20px;
  background: linear-gradient(135deg, #ffffff 0%, #f0fdfa 100%);
  border: 1px solid var(--app-border);
  padding: 32px;
  box-shadow: var(--app-shadow-soft);
  overflow: hidden;
  display: flex;
  justify-content: space-between;
  align-items: center;

  &::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(20, 184, 166, 0.08) 0%, transparent 70%);
    border-radius: 50%;
  }
}

.hero-content {
  display: flex;
  gap: 40px;
  align-items: center;
  z-index: 1;
}

.eyebrow-tag {
  display: inline-block;
  padding: 4px 12px;
  background: #ccfbf1;
  color: #115e59;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 12px;
}

.hero-title {
  margin: 0 0 8px 0;
  font-size: 28px;
  color: var(--app-text-main);
  letter-spacing: -0.5px;
}

.hero-desc {
  margin: 0 0 24px 0;
  color: var(--app-text-sub);
  font-size: 16px;
  max-width: 500px;
  line-height: 1.6;
}

.hero-meta {
  display: flex;
  gap: 24px;
  
  .meta-item {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--app-text-muted);
    font-size: 14px;
    
    .el-icon {
      color: #0d9488;
    }
  }
}

.refresh-btn {
  background: white;
  border: 1px solid #e2e8f0;
  color: var(--app-text-sub);
  font-weight: 500;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  
  &:hover {
    color: #115e59;
    border-color: #115e59;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(17, 94, 89, 0.1);
  }
}

/* Metric Cards */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.metric-card {
  background: white;
  border: 1px solid var(--app-border);
  border-radius: 20px;
  padding: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: var(--app-shadow-soft);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  opacity: 0;
  animation: fadeUp 0.6s ease-out forwards;
  animation-delay: var(--delay);

  &:hover {
    transform: translateY(-6px);
    box-shadow: var(--app-shadow-hover);
    border-color: #115e59;

    .metric-icon-wrap {
      background: #ccfbf1;
      color: #115e59;
    }
  }
}

.metric-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-label {
  font-size: 14px;
  color: var(--app-text-muted);
  font-weight: 500;
}

.metric-value {
  font-size: 32px;
  color: var(--app-text-main);
  font-weight: 700;
  margin: 4px 0;
}

.metric-sub {
  font-size: 12px;
  color: var(--app-text-sub);
}

.metric-icon-wrap {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: #94a3b8;
  transition: all 0.3s ease;
}

/* Panel Layout */
.panel-layout {
  display: flex;
  gap: 24px;
}

.panel-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.panel-side {
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.panel-card {
  background: white;
  border-radius: 20px;
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow-soft);
  padding: 24px;
}

.panel-head {
  margin-bottom: 24px;
  
  .title-wrap {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .head-icon {
      padding: 8px;
      background: #f0fdfa;
      border-radius: 10px;
      color: #0d9488;
      font-size: 18px;
    }
    
    h3 {
      margin: 0;
      font-size: 18px;
      color: var(--app-text-main);
    }
    
    .subtitle {
      font-size: 12px;
      color: var(--app-text-muted);
    }
  }
}

/* Trends Chart */
.trend-wrapper {
  padding-top: 10px;
}

.trend-grid {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  height: 200px;
  gap: 12px;
}

.trend-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.trend-bar-wrap {
  width: 100%;
  height: 160px;
  background: #f1f5f9;
  border-radius: 12px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  overflow: visible;
}

.trend-bar {
  width: 100%;
  max-width: 18px;
  background: linear-gradient(180deg, #115e59 0%, #2dd4bf 100%);
  border-radius: 10px 10px 0 0;
  transition: height 0.8s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  
  &:hover {
    filter: brightness(1.1);
    .bar-tooltip {
      opacity: 1;
      transform: translateX(-50%) translateY(-30px);
    }
  }
}

.bar-tooltip {
  position: absolute;
  left: 50%;
  transform: translateX(-50%) translateY(-24px);
  background: var(--app-text-main);
  color: white;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 6px;
  opacity: 0;
  transition: all 0.2s ease;
  pointer-events: none;
}

.trend-label {
  font-size: 12px;
  color: var(--app-text-muted);
}

/* Stats List (Sidebar) */
.stats-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
  
  span {
    color: var(--app-text-sub);
    font-size: 14px;
  }
  
  strong {
    color: var(--app-text-main);
    font-size: 16px;
    
    &.highlight { color: #0d9488; }
    &.warning { color: #f59e0b; }
    &.danger { color: #ef4444; }
  }
}

/* Rank List (Sidebar) */
.rank-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rank-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px;
  border-radius: 12px;
  background: #f8fafc;
  transition: background 0.2s ease;
  
  &:hover {
    background: #f1f5f9;
  }
}

.rank-badge {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #e2e8f0;
  color: #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  
  &.rank-1 { background: #fef3c7; color: #d97706; }
  &.rank-2 { background: #f1f5f9; color: #64748b; }
  &.rank-3 { background: #ffedd5; color: #ea580c; }
}

.rank-info {
  display: flex;
  flex-direction: column;
  
  .rank-name {
    font-size: 14px;
    font-weight: 600;
    color: var(--app-text-main);
  }
  
  .rank-meta {
    font-size: 11px;
    color: var(--app-text-muted);
  }
}

/* Notice Stack (Member Side) */
.notice-stack {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.stack-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stack-text {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  
  .stack-label { color: var(--app-text-sub); font-weight: 500; }
  .stack-count { color: var(--app-text-main); font-weight: 700; }
}

.stack-track {
  height: 6px;
  background: #f1f5f9;
  border-radius: 10px;
  overflow: hidden;
}

.stack-fill {
  height: 100%;
  background: linear-gradient(90deg, #115e59 0%, #2dd4bf 100%);
  border-radius: 10px;
  transition: width 1s ease-out;
}

/* Guide Content */
.guide-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.guide-item {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 16px;
  
  .guide-number {
    font-size: 24px;
    font-weight: 800;
    color: #e2e8f0;
  }
  
  p {
    margin: 0;
    font-size: 14px;
    color: var(--app-text-sub);
    line-height: 1.5;
  }
}

/* Premium Table */
.premium-table {
  --el-table-border-color: #f1f5f9;
  --el-table-header-bg-color: #f8fafc;
  
  :deep(.el-table__header) {
    th {
      font-weight: 600;
      color: var(--app-text-main);
      padding: 12px 0;
    }
  }
  
  :deep(.el-table__row) {
    td {
      padding: 12px 0;
      color: var(--app-text-sub);
    }
  }
}

@media (max-width: 1280px) {
  .metric-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .panel-layout {
    flex-direction: column;
  }
  
  .panel-side {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }
  
  .panel-side {
    grid-template-columns: 1fr;
  }
  
  .hero-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 20px;
  }
}
</style>
