<template>
  <div class="page-wrap">
    <section class="page-head">
      <div>
        <span class="eyebrow">数据洞察</span>
        <h2>报表中心</h2>
        <p>集中查看预约趋势、实验室利用率、设备故障、用户活跃度和公告触达情况，并支持按时间区间导出分析结果。</p>
      </div>
      <div class="head-actions">
        <el-button :loading="loading" @click="resetFilters">重置区间</el-button>
        <el-button :loading="loading" @click="fetchReport">刷新报表</el-button>
        <el-button @click="exportReport('csv')">导出 CSV</el-button>
        <el-button type="primary" @click="exportReport('excel')">导出 Excel</el-button>
      </div>
    </section>

    <section class="page-card">
      <el-form inline class="filter-form">
        <el-form-item label="开始日期">
          <el-date-picker v-model="filters.startDate" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="filters.endDate" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item>
          <el-button :loading="loading" type="primary" @click="fetchReport">查询报表</el-button>
        </el-form-item>
      </el-form>

      <div class="summary-bar">
        <span>统计区间：{{ reportRange.startDate || '-' }} 至 {{ reportRange.endDate || '-' }}</span>
        <span>统计天数：{{ reportRange.days || 0 }} 天</span>
        <span>生成时间：{{ report.generatedAt || '-' }}</span>
      </div>

      <div class="metric-grid">
        <article v-for="item in metricCards" :key="item.key" class="metric-card">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <small>{{ item.sub }}</small>
        </article>
      </div>
    </section>

    <section class="section-grid">
      <article class="panel-card">
        <div class="panel-head">
          <h3>预约摘要</h3>
          <span>核心预约指标</span>
        </div>
        <div class="kv-grid">
          <div class="kv-item">
            <span>预约总数</span>
            <strong>{{ reservationSummary.total || 0 }}</strong>
          </div>
          <div class="kv-item">
            <span>待审批</span>
            <strong>{{ reservationSummary.pending || 0 }}</strong>
          </div>
          <div class="kv-item">
            <span>已通过</span>
            <strong>{{ reservationSummary.approved || 0 }}</strong>
          </div>
          <div class="kv-item">
            <span>已驳回</span>
            <strong>{{ reservationSummary.rejected || 0 }}</strong>
          </div>
          <div class="kv-item">
            <span>取消预约</span>
            <strong>{{ reservationSummary.cancelled || 0 }}</strong>
          </div>
          <div class="kv-item">
            <span>预约用户数</span>
            <strong>{{ reservationSummary.uniqueUsers || 0 }}</strong>
          </div>
        </div>
      </article>

      <article class="panel-card">
        <div class="panel-head">
          <h3>实验室利用率</h3>
          <span>总体利用情况</span>
        </div>
        <div class="kv-grid">
          <div class="kv-item">
            <span>实验室总数</span>
            <strong>{{ labSummary.totalLabs || 0 }}</strong>
          </div>
          <div class="kv-item">
            <span>可用时段</span>
            <strong>{{ labSummary.totalAvailableSlots || 0 }}</strong>
          </div>
          <div class="kv-item">
            <span>已使用时段</span>
            <strong>{{ labSummary.totalUsedSlots || 0 }}</strong>
          </div>
          <div class="kv-item">
            <span>整体利用率</span>
            <strong>{{ formatRate(labSummary.overallRate) }}</strong>
          </div>
        </div>
      </article>

      <article class="panel-card">
        <div class="panel-head">
          <h3>热门实验室</h3>
          <span>按预约量排序</span>
        </div>
        <div v-if="topLabs.length" class="rank-list">
          <div v-for="(item, index) in topLabs" :key="`${item.labName}-${index}`" class="rank-item">
            <span class="rank-index">{{ index + 1 }}</span>
            <div class="rank-content">
              <strong>{{ item.labName || '-' }}</strong>
              <span>总预约 {{ item.total || 0 }}，批准时段 {{ item.approvedSlots || 0 }}</span>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无热门实验室数据" />
      </article>

      <article class="panel-card">
        <div class="panel-head">
          <h3>设备故障类型</h3>
          <span>近一周期报修分布</span>
        </div>
        <div v-if="issueTypeRows.length" class="stack-list">
          <div v-for="item in issueTypeRows" :key="item.issueType" class="stack-item">
            <div class="stack-text">
              <strong>{{ item.issueType || '未分类' }}</strong>
              <span>{{ item.count || 0 }} 单</span>
            </div>
            <div class="stack-track">
              <span class="stack-fill" :style="{ width: `${item.width}%` }" />
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无设备故障数据" />
      </article>

      <article class="panel-card panel-span-2">
        <div class="panel-head">
          <h3>实验室利用率明细</h3>
          <span>TOP 20</span>
        </div>
        <el-table :data="labRows" empty-text="暂无实验室利用率数据" stripe>
          <el-table-column prop="labName" label="实验室" min-width="180" />
          <el-table-column prop="usedSlots" label="已用时段" min-width="120" />
          <el-table-column prop="availableSlots" label="可用时段" min-width="120" />
          <el-table-column label="利用率" min-width="120">
            <template #default="{ row }">
              {{ formatRate(row.rate) }}
            </template>
          </el-table-column>
        </el-table>
      </article>

      <article class="panel-card">
        <div class="panel-head">
          <h3>报修效率</h3>
          <span>维修流程表现</span>
        </div>
        <div class="kv-grid">
          <div class="kv-item">
            <span>工单总数</span>
            <strong>{{ repairSummary.total || 0 }}</strong>
          </div>
          <div class="kv-item">
            <span>已完成</span>
            <strong>{{ repairSummary.completed || 0 }}</strong>
          </div>
          <div class="kv-item">
            <span>完成率</span>
            <strong>{{ formatRate(repairSummary.completionRate) }}</strong>
          </div>
          <div class="kv-item">
            <span>24 小时内完成</span>
            <strong>{{ repairSummary.within24hCount || 0 }}</strong>
          </div>
          <div class="kv-item">
            <span>平均响应</span>
            <strong>{{ formatMinutes(repairSummary.avgResponseMinutes) }}</strong>
          </div>
          <div class="kv-item">
            <span>平均完结</span>
            <strong>{{ formatMinutes(repairSummary.avgCompleteMinutes) }}</strong>
          </div>
        </div>
      </article>

      <article class="panel-card">
        <div class="panel-head">
          <h3>用户活跃概况</h3>
          <span>按角色拆解</span>
        </div>
        <div class="kv-grid">
          <div class="kv-item">
            <span>总用户数</span>
            <strong>{{ userActivitySummary.totalUsers || 0 }}</strong>
          </div>
          <div class="kv-item">
            <span>活跃用户</span>
            <strong>{{ userActivitySummary.activeUsers || 0 }}</strong>
          </div>
          <div class="kv-item">
            <span>活跃率</span>
            <strong>{{ formatRate(userActivitySummary.activityRate) }}</strong>
          </div>
          <div class="kv-item">
            <span>登录活跃</span>
            <strong>{{ userActivitySummary.loginActiveUsers || 0 }}</strong>
          </div>
        </div>
        <div v-if="userRoleRows.length" class="stack-list compact-stack">
          <div v-for="item in userRoleRows" :key="item.role" class="stack-item">
            <div class="stack-text">
              <strong>{{ getRoleText(item.role) }}</strong>
              <span>{{ item.active || 0 }} / {{ item.total || 0 }}</span>
            </div>
            <div class="stack-track">
              <span class="stack-fill" :style="{ width: `${item.width}%` }" />
            </div>
          </div>
        </div>
      </article>

      <article class="panel-card panel-span-2">
        <div class="panel-head">
          <h3>公告触达明细</h3>
          <span>近一周期已发布公告</span>
        </div>
        <div class="kv-grid brief-grid">
          <div class="kv-item">
            <span>已发布公告</span>
            <strong>{{ announcementSummary.publishedCount || 0 }}</strong>
          </div>
          <div class="kv-item">
            <span>活跃受众</span>
            <strong>{{ announcementSummary.activeAudienceUsers || 0 }}</strong>
          </div>
          <div class="kv-item">
            <span>唯一阅读用户</span>
            <strong>{{ announcementSummary.uniqueReaders || 0 }}</strong>
          </div>
          <div class="kv-item">
            <span>触达率</span>
            <strong>{{ formatRate(announcementSummary.reachRate) }}</strong>
          </div>
        </div>
        <el-table :data="announcementRows" empty-text="暂无公告触达数据" stripe>
          <el-table-column prop="title" label="公告标题" min-width="240" />
          <el-table-column prop="publishAt" label="发布时间" min-width="180" />
          <el-table-column prop="readUsers" label="阅读人数" min-width="120" />
          <el-table-column label="阅读率" min-width="120">
            <template #default="{ row }">
              {{ formatRate(row.readRate) }}
            </template>
          </el-table-column>
        </el-table>
      </article>
    </section>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { exportReportFile, getReportCenter } from '@/api/reports'

function extractFilename(headerValue, fallbackName) {
  const source = String(headerValue || '')
  const utf8Match = source.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1])
    } catch (error) {
      return utf8Match[1]
    }
  }

  const plainMatch = source.match(/filename=\"?([^\";]+)\"?/i)
  return plainMatch?.[1] || fallbackName
}

function formatYmd(date) {
  const current = date instanceof Date ? date : new Date(date)
  const year = current.getFullYear()
  const month = `${current.getMonth() + 1}`.padStart(2, '0')
  const day = `${current.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

function createDefaultRange() {
  const now = new Date()
  return {
    endDate: formatYmd(now),
    startDate: formatYmd(new Date(now.getTime() - 29 * 24 * 60 * 60 * 1000))
  }
}

const loading = ref(false)
const filters = reactive(createDefaultRange())

const report = ref({
  generatedAt: '',
  range: { startDate: '', endDate: '', days: 0 },
  reservation: { summary: {}, topLabs: [] },
  labUtilization: { summary: {}, labs: [] },
  equipmentFailure: { summary: {}, byIssueType: [] },
  repairEfficiency: { summary: {} },
  courseTaskCompletion: { summary: {} },
  userActivity: { summary: {}, byRole: [] },
  announcementReach: { summary: {}, items: [] }
})

const reportRange = computed(() => report.value.range || {})
const reservationSummary = computed(() => report.value.reservation?.summary || {})
const labSummary = computed(() => report.value.labUtilization?.summary || {})
const repairSummary = computed(() => report.value.repairEfficiency?.summary || {})
const userActivitySummary = computed(() => report.value.userActivity?.summary || {})
const announcementSummary = computed(() => report.value.announcementReach?.summary || {})
const topLabs = computed(() => (
  Array.isArray(report.value.reservation?.topLabs) ? report.value.reservation.topLabs : []
))
const labRows = computed(() => (
  Array.isArray(report.value.labUtilization?.labs) ? report.value.labUtilization.labs : []
))
const announcementRows = computed(() => (
  Array.isArray(report.value.announcementReach?.items) ? report.value.announcementReach.items : []
))

const issueTypeRows = computed(() => {
  const rows = Array.isArray(report.value.equipmentFailure?.byIssueType)
    ? report.value.equipmentFailure.byIssueType
    : []
  const maxCount = Math.max(...rows.map((item) => Number(item.count || 0)), 1)
  return rows.map((item) => ({
    ...item,
    width: Math.max((Number(item.count || 0) / maxCount) * 100, Number(item.count || 0) > 0 ? 10 : 0)
  }))
})

const userRoleRows = computed(() => {
  const rows = Array.isArray(report.value.userActivity?.byRole)
    ? report.value.userActivity.byRole
    : []
  return rows.map((item) => ({
    ...item,
    width: Math.max(Number(item.activityRate || 0) * 100, Number(item.active || 0) > 0 ? 10 : 0)
  }))
})

const metricCards = computed(() => [
  {
    key: 'reservation-total',
    label: '预约总量',
    value: reservationSummary.value.total || 0,
    sub: `批准时段 ${reservationSummary.value.approvedSlots || 0}`
  },
  {
    key: 'lab-rate',
    label: '实验室利用率',
    value: formatRate(labSummary.value.overallRate),
    sub: `已使用 ${labSummary.value.totalUsedSlots || 0} / 可用 ${labSummary.value.totalAvailableSlots || 0}`
  },
  {
    key: 'repair-rate',
    label: '报修完成率',
    value: formatRate(repairSummary.value.completionRate),
    sub: `24h 内完成 ${repairSummary.value.within24hCount || 0}`
  },
  {
    key: 'announcement-rate',
    label: '公告触达率',
    value: formatRate(announcementSummary.value.reachRate),
    sub: `阅读用户 ${announcementSummary.value.uniqueReaders || 0}`
  }
])

function formatRate(value) {
  const num = Number(value || 0)
  return `${Math.round(num * 10000) / 100}%`
}

function formatMinutes(value) {
  const num = Number(value || 0)
  if (!num) {
    return '0 分钟'
  }
  if (num >= 60) {
    return `${(num / 60).toFixed(1)} 小时`
  }
  return `${Math.round(num)} 分钟`
}

function getRoleText(role) {
  if (role === 'admin') return '管理员'
  if (role === 'teacher') return '教师'
  if (role === 'student') return '学生'
  return role || '未知角色'
}

function validateRange() {
  if (filters.startDate > filters.endDate) {
    ElMessage.warning('开始日期不能大于结束日期')
    return false
  }
  return true
}

function resetFilters() {
  Object.assign(filters, createDefaultRange())
  fetchReport()
}

async function fetchReport() {
  if (!validateRange()) {
    return
  }

  loading.value = true
  try {
    const response = await getReportCenter({
      startDate: filters.startDate,
      endDate: filters.endDate
    })
    report.value = response.data?.data || report.value
  } finally {
    loading.value = false
  }
}

async function exportReport(format) {
  if (!validateRange()) {
    return
  }

  const response = await exportReportFile({
    startDate: filters.startDate,
    endDate: filters.endDate,
    format
  })
  const fallbackName = `admin_report_center_${filters.startDate}_${filters.endDate}.${format === 'excel' ? 'xls' : 'csv'}`
  const blob = response.data instanceof Blob
    ? response.data
    : new Blob([response.data], {
        type: format === 'excel' ? 'application/vnd.ms-excel' : 'text/csv;charset=utf-8'
      })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  const fileName = extractFilename(response.headers?.['content-disposition'], fallbackName)
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

onMounted(() => {
  fetchReport()
})
</script>

<style scoped lang="scss">
.page-wrap {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-head,
.page-card,
.panel-card {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 24px;
  background: var(--app-surface);
  box-shadow: var(--app-shadow);
}

.page-head,
.head-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.page-head {
  position: relative;
  overflow: hidden;
  padding: 24px;
  background:
    radial-gradient(circle at top right, rgba(15, 118, 110, 0.16), transparent 36%),
    linear-gradient(135deg, #ffffff, #f5fbfa);
}

.page-head::after {
  content: '';
  position: absolute;
  right: -36px;
  bottom: -84px;
  width: 220px;
  height: 220px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(45, 212, 191, 0.18), rgba(45, 212, 191, 0));
}

.page-card,
.panel-card {
  padding: 24px;
}

.page-head h2,
.panel-head h3 {
  margin: 8px 0 10px;
}

.page-head p,
.summary-bar,
.panel-head span,
.metric-card span,
.metric-card small,
.kv-item span,
.stack-text span,
.rank-content span {
  color: var(--app-muted);
  line-height: 1.7;
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

.head-actions {
  position: relative;
  z-index: 1;
  flex-wrap: wrap;
}

.filter-form {
  margin-bottom: 8px;
}

.summary-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 18px;
  font-size: 13px;
}

.metric-grid,
.section-grid,
.kv-grid {
  display: grid;
  gap: 16px;
}

.metric-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.metric-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 20px;
  border-radius: 20px;
  background: linear-gradient(180deg, #fbfffe 0%, #f1f5f9 100%);
}

.metric-card strong {
  font-size: 30px;
}

.section-grid {
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

.kv-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.brief-grid {
  margin-bottom: 16px;
}

.kv-item,
.stack-item,
.rank-item {
  padding: 14px 16px;
  border-radius: 18px;
  background: #f8fafc;
}

.kv-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.kv-item strong {
  font-size: 24px;
}

.stack-list,
.rank-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stack-text {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.stack-track {
  height: 8px;
  border-radius: 999px;
  overflow: hidden;
  background: #e2e8f0;
}

.stack-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #0f766e 0%, #2dd4bf 100%);
}

.compact-stack {
  margin-top: 16px;
}

.rank-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.rank-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--app-primary-soft);
  color: #115e59;
  font-weight: 700;
}

.rank-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

@media (max-width: 1200px) {
  .metric-grid,
  .section-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .page-head,
  .head-actions,
  .summary-bar,
  .metric-grid,
  .section-grid,
  .kv-grid {
    grid-template-columns: 1fr;
  }

  .page-head,
  .head-actions,
  .stack-text,
  .rank-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .panel-span-2 {
    grid-column: span 1;
  }
}
</style>
