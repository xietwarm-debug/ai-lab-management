<template>
  <div class="ops-page">
    <section class="hero-card animate-up" style="--delay: 0.1s">
      <div class="hero-copy">
        <span class="eyebrow">运营总览</span>
        <h2>大屏运营看板</h2>
        <p>面向管理员和值班老师的统一总览页，聚合今日预约、借用逾期、门禁待处理、设备风险、实验室使用率和近 7 天趋势。</p>
        <div class="hero-meta">
          <span>更新时间 {{ board.generatedAt || '-' }}</span>
          <span>今日活跃实验室 {{ overview.todayActiveLabs || 0 }}</span>
          <span>忙碌实验室 {{ overview.busyLabCount || 0 }} / {{ overview.labTotal || 0 }}</span>
        </div>
      </div>
      <div class="hero-actions">
        <el-button type="primary" :loading="loading" @click="fetchBoard">刷新看板</el-button>
      </div>
    </section>

    <section class="metric-grid">
      <article class="metric-card animate-up" style="--delay: 0.1s">
        <span class="metric-label">今日预约</span>
        <strong class="metric-value">{{ overview.todayReservations || 0 }}</strong>
        <span class="metric-sub">当天提交与处理的预约总量</span>
      </article>
      <article class="metric-card warn animate-up" style="--delay: 0.2s">
        <span class="metric-label">借用逾期</span>
        <strong class="metric-value">{{ overview.overdueBorrows || 0 }}</strong>
        <span class="metric-sub">已到期但未归还的借用单</span>
      </article>
      <article class="metric-card accent animate-up" style="--delay: 0.3s">
        <span class="metric-label">门禁待处理</span>
        <strong class="metric-value">{{ overview.pendingDoorReminders || 0 }}</strong>
        <span class="metric-sub">今日待确认开门的提醒</span>
      </article>
      <article class="metric-card danger animate-up" style="--delay: 0.4s">
        <span class="metric-label">设备风险</span>
        <strong class="metric-value">{{ overview.highRiskAlerts || overview.riskAlerts || 0 }}</strong>
        <span class="metric-sub">高风险优先，建议值班老师先处理</span>
      </article>
      <article class="metric-card animate-up" style="--delay: 0.5s">
        <span class="metric-label">实验室使用率</span>
        <strong class="metric-value">{{ usageRateText }}</strong>
        <span class="metric-sub">按当前忙碌实验室占比估算</span>
      </article>
      <article class="metric-card animate-up" style="--delay: 0.6s">
        <span class="metric-label">今日告警</span>
        <strong class="metric-value">{{ overview.alarmsToday || 0 }}</strong>
        <span class="metric-sub">来自传感器与 AI 风险联动</span>
      </article>
    </section>

    <section class="panel-grid">
      <article class="panel-card panel-span-2 animate-up" style="--delay: 0.5s">
        <div class="panel-head">
          <div>
            <h3>近 7 天趋势</h3>
            <span>预约量、告警量与借用逾期同时观察</span>
          </div>
        </div>
        <div v-if="trendRows.length" class="trend-grid">
          <div v-for="item in trendRows" :key="item.date" class="trend-col">
            <span class="trend-label">{{ item.label }}</span>
            <div class="trend-bars">
              <span class="bar reservation" :style="{ height: `${item.reservationHeight}%` }" />
              <span class="bar alarm" :style="{ height: `${item.alarmHeight}%` }" />
              <span class="bar overdue" :style="{ height: `${item.overdueHeight}%` }" />
            </div>
            <div class="trend-meta">
              <span>约 {{ item.reservations }}</span>
              <span>警 {{ item.alarms }}</span>
              <span>逾 {{ item.overdueBorrows }}</span>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无趋势数据" />
      </article>

      <article class="panel-card animate-up" style="--delay: 0.6s">
        <div class="panel-head">
          <div>
            <h3>风险提醒</h3>
            <span>{{ riskAlerts.length }} 条重点提醒</span>
          </div>
        </div>
        <div v-if="riskAlerts.length" class="risk-list">
          <button
            v-for="(item, index) in riskAlerts"
            :key="`${item.title}-${index}`"
            class="risk-item"
            type="button"
            @click="jump(item.jumpUrl)"
          >
            <div class="risk-top">
              <strong>{{ item.title || '设备风险预警' }}</strong>
              <el-tag size="small" :type="riskTagType(item.level)">{{ riskLevelText(item.level) }}</el-tag>
            </div>
            <p>{{ item.description || '-' }}</p>
          </button>
        </div>
        <el-empty v-else description="当前暂无风险提醒" />
      </article>

      <article class="panel-card panel-span-2 animate-up" style="--delay: 0.7s">
        <div class="panel-head">
          <div>
            <h3>实验室使用热度</h3>
            <span>近 7 天按预约量排序</span>
          </div>
        </div>
        <div v-if="labUsage.length" class="usage-list">
          <div v-for="item in labUsage" :key="item.labId || item.labName" class="usage-item">
            <div class="usage-copy">
              <strong>{{ item.labName }}</strong>
              <span>{{ item.status === 'busy' ? '当前忙碌' : '当前空闲' }} · 近 7 天预约 {{ item.reservationCount }} 次</span>
            </div>
            <div class="usage-track">
              <span class="usage-fill" :style="{ width: `${item.usageRate || 0}%` }" />
            </div>
            <span class="usage-side">{{ Number(item.usageRate || 0).toFixed(0) }}%</span>
          </div>
        </div>
        <el-empty v-else description="暂无实验室使用数据" />
      </article>

      <article class="panel-card animate-up" style="--delay: 0.8s">
        <div class="panel-head">
          <div>
            <h3>值班建议</h3>
            <span>按优先级排序</span>
          </div>
        </div>
        <ul class="suggest-list">
          <li>优先处理 {{ overview.pendingDoorReminders || 0 }} 条门禁待办，避免开课前遗漏开门。</li>
          <li>借用逾期 {{ overview.overdueBorrows || 0 }} 条，建议在借用审批页集中催还。</li>
          <li>高风险提醒 {{ overview.highRiskAlerts || 0 }} 条，优先联动资产与维修页排查。</li>
          <li>当前实验室实时使用率 {{ usageRateText }}，可据此安排值班巡检资源。</li>
        </ul>
      </article>
    </section>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { getOperationsBoard } from '@/api/operations'
import { resolveAdminJumpUrl } from '@/utils/admin-links'

const router = useRouter()

const loading = ref(false)
const board = ref({})

const overview = computed(() => board.value.overview || {})
const riskAlerts = computed(() => Array.isArray(board.value.risk?.alerts) ? board.value.risk.alerts : [])
const labUsage = computed(() => Array.isArray(board.value.labUsage) ? board.value.labUsage : [])
const usageRateText = computed(() => `${Number(overview.value.labUsageRate || 0).toFixed(1)}%`)

const trendRows = computed(() => {
  const rows = Array.isArray(board.value.trend7d) ? board.value.trend7d : []
  const maxReservation = Math.max(...rows.map((item) => Number(item.reservations || 0)), 1)
  const maxAlarm = Math.max(...rows.map((item) => Number(item.alarms || 0)), 1)
  const maxOverdue = Math.max(...rows.map((item) => Number(item.overdueBorrows || 0)), 1)
  return rows.map((item) => ({
    ...item,
    reservationHeight: Math.max((Number(item.reservations || 0) / maxReservation) * 100, Number(item.reservations || 0) > 0 ? 12 : 6),
    alarmHeight: Math.max((Number(item.alarms || 0) / maxAlarm) * 100, Number(item.alarms || 0) > 0 ? 12 : 6),
    overdueHeight: Math.max((Number(item.overdueBorrows || 0) / maxOverdue) * 100, Number(item.overdueBorrows || 0) > 0 ? 12 : 6)
  }))
})

function riskTagType(level) {
  if (level === 'high') return 'danger'
  if (level === 'medium') return 'warning'
  return 'info'
}

function riskLevelText(level) {
  if (level === 'high') return '高风险'
  if (level === 'medium') return '中风险'
  return '关注'
}

async function fetchBoard() {
  loading.value = true
  try {
    const response = await getOperationsBoard()
    board.value = response.data?.data || {}
  } finally {
    loading.value = false
  }
}

function jump(rawUrl) {
  const target = resolveAdminJumpUrl(rawUrl || '') || '/dashboard'
  router.push(target)
}

onMounted(() => {
  fetchBoard()
})
</script>

<style scoped lang="scss">
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

.ops-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
  animation: fadeIn 0.6s ease-out;
}

.hero-card,
.metric-card,
.panel-card {
  border-radius: 20px;
  border: none;
  background: white;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.04);
}

.hero-card {
  background:
    radial-gradient(circle at top left, rgba(59, 130, 246, 0.1), transparent 32%),
    radial-gradient(circle at bottom right, rgba(59, 130, 246, 0.05), transparent 28%),
    linear-gradient(180deg, #ffffff, #f8fafc);
}

.hero-card,
.panel-card {
  padding: 24px;
}

.hero-card,
.hero-meta,
.panel-head,
.usage-item,
.risk-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.hero-card,
.hero-meta {
  flex-wrap: wrap;
}

.eyebrow {
  display: inline-flex;
  margin-bottom: 8px;
  font-size: 13px;
  letter-spacing: 0.08em;
  color: #0e7490;
}

.hero-copy h2,
.panel-head h3,
.metric-value {
  margin: 0;
}

.hero-copy p,
.hero-meta,
.panel-head span,
.metric-label,
.metric-sub,
.usage-copy span,
.risk-item p {
  color: var(--app-text-secondary);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.metric-card {
  padding: 22px;
}

.metric-value {
  display: block;
  margin: 10px 0;
  font-size: 34px;
}

.metric-sub,
.metric-label {
  font-size: 13px;
}

.metric-card.warn .metric-value {
  color: #f59e0b;
}

.metric-card.accent .metric-value {
  color: #3b82f6;
}

.metric-card.danger .metric-value {
  color: #ef4444;
}

.panel-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.panel-span-2 {
  grid-column: span 2;
}

.trend-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 12px;
  align-items: end;
  min-height: 280px;
}

.trend-col {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
  gap: 10px;
  height: 100%;
}

.trend-bars {
  display: flex;
  align-items: end;
  justify-content: center;
  gap: 6px;
  width: 100%;
  min-height: 210px;
  padding: 12px 0;
}

.bar {
  width: 18px;
  border-radius: 999px 999px 6px 6px;
}

.bar.reservation {
  background: linear-gradient(180deg, #60a5fa, #2563eb);
}

.bar.alarm {
  background: linear-gradient(180deg, #f59e0b, #d97706);
}

.bar.overdue {
  background: linear-gradient(180deg, #ef4444, #dc2626);
}

.trend-meta,
.trend-label {
  font-size: 12px;
  color: var(--app-text-tertiary);
}

.trend-meta {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  justify-content: center;
  gap: 4px;
}

.risk-list,
.usage-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.risk-item {
  width: 100%;
  padding: 14px;
  border: none;
  border-radius: 12px;
  background: var(--app-bg);
  text-align: left;
  cursor: pointer;
  transition: background 0.2s ease;

  &:hover {
    background: #f1f5f9;
  }
}

:deep(.el-tag--danger) {
  background-color: #fee2e2 !important;
  color: #dc2626 !important;
  border-color: #fca5a5 !important;
  font-weight: 600;
}

.risk-item p {
  margin: 10px 0 0;
  line-height: 1.7;
}

.usage-item {
  gap: 16px;
}

.usage-copy {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.usage-track {
  flex: 1;
  height: 12px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.2);
  overflow: hidden;
}

.usage-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #3b82f6, #1d4ed8);
}

.usage-side {
  width: 48px;
  text-align: right;
  color: var(--app-text-tertiary);
  font-size: 13px;
}

.suggest-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin: 16px 0 0;
  padding-left: 20px;
  color: var(--app-text-secondary);
  line-height: 1.7;
}

@media (max-width: 1180px) {
  .panel-grid {
    grid-template-columns: 1fr;
  }

  .panel-span-2 {
    grid-column: span 1;
  }
}

@media (max-width: 960px) {
  .hero-card,
  .panel-head,
  .usage-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .trend-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
</style>
