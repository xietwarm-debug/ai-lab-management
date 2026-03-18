<template>
  <div class="audit-page">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="eyebrow">留痕与追踪</span>
        <h2>审计日志</h2>
        <p>按动作、操作人、对象类型和日期筛选关键操作，便于排查误操作与导出归档。</p>
      </div>
      <div class="hero-actions">
        <el-button @click="resetFilters">重置</el-button>
        <el-button type="primary" :loading="loading" @click="queryLogs">查询</el-button>
        <el-button @click="exportLogs">导出 CSV</el-button>
      </div>
    </section>

    <section class="panel-card">
      <el-form inline>
        <el-form-item label="动作">
          <el-select v-model="filters.action" clearable style="width: 240px">
            <el-option v-for="item in actionOptions" :key="item.value || 'all'" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作人">
          <el-input v-model="filters.operator" placeholder="用户名" clearable />
        </el-form-item>
        <el-form-item label="对象类型">
          <el-select v-model="filters.targetType" clearable style="width: 180px">
            <el-option v-for="item in targetTypes" :key="item.value || 'all'" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="filters.startDate" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="filters.endDate" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
      </el-form>
    </section>

    <section class="panel-card">
      <div class="table-head">
        <div>
          <h3>日志列表</h3>
          <span>已加载 {{ rows.length }} / {{ total }} 条</span>
        </div>
      </div>
      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="createdAt" label="时间" min-width="180" />
        <el-table-column prop="action" label="动作" min-width="220" />
        <el-table-column prop="operatorName" label="操作人" min-width="130" />
        <el-table-column prop="operatorRole" label="角色" min-width="100" />
        <el-table-column prop="targetType" label="对象类型" min-width="120" />
        <el-table-column prop="targetId" label="对象 ID" min-width="120" />
        <el-table-column prop="ip" label="IP" min-width="140" />
        <el-table-column label="详情" min-width="320">
          <template #default="{ row }">
            <pre class="detail-pre">{{ formatDetail(row.detail) }}</pre>
          </template>
        </el-table-column>
      </el-table>
      <div class="pager-row">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          layout="total, sizes, prev, pager, next"
          :total="total"
          :page-sizes="[20, 50, 100]"
          @current-change="fetchLogs"
          @size-change="handlePageSizeChange"
        />
      </div>
    </section>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { getAuditExportUrl, getAuditLogs } from '@/api/audit'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const filters = reactive({
  action: '',
  operator: '',
  targetType: '',
  startDate: '',
  endDate: ''
})

const targetTypes = [
  { label: '全部类型', value: '' },
  { label: '预约', value: 'reservation' },
  { label: '用户', value: 'user' },
  { label: '实验室', value: 'lab' },
  { label: '资产借用', value: 'borrow_request' },
  { label: '门禁提醒', value: 'door_open_reminders' },
  { label: '失物', value: 'lostfound' },
  { label: '认证', value: 'auth' }
]

const actionOptions = [
  { label: '全部动作', value: '' },
  { label: '用户改角色', value: 'admin.user.set_role' },
  { label: '用户删除', value: 'admin.user.delete' },
  { label: '实验室创建', value: 'admin.lab.create' },
  { label: '实验室更新', value: 'admin.lab.update' },
  { label: '实验室删除', value: 'admin.lab.delete' },
  { label: '预约通过', value: 'admin.reservation.approve' },
  { label: '预约驳回', value: 'admin.reservation.reject' },
  { label: '批量通过', value: 'admin.reservation.batch_approve' },
  { label: '课表导入', value: 'admin.schedule.import' },
  { label: '模板启用', value: 'admin.schedule.template.activate' },
  { label: '模板删除', value: 'admin.schedule.template.delete' },
  { label: '借用审批通过', value: 'admin.borrow_request.approve' },
  { label: '借用审批驳回', value: 'admin.borrow_request.reject' },
  { label: '登录成功', value: 'auth.login.success' },
  { label: '登录失败', value: 'auth.login.failed' }
]

function validateRange() {
  if (filters.startDate && filters.endDate && filters.startDate > filters.endDate) {
    ElMessage.warning('开始日期不能大于结束日期')
    return false
  }
  return true
}

function buildParams() {
  return {
    page: page.value,
    pageSize: pageSize.value,
    action: filters.action,
    operator: filters.operator,
    targetType: filters.targetType,
    startDate: filters.startDate,
    endDate: filters.endDate
  }
}

function formatDetail(detail) {
  if (!detail || typeof detail !== 'object' || Array.isArray(detail)) return '-'
  try {
    return JSON.stringify(detail, null, 2)
  } catch (error) {
    return '-'
  }
}

async function fetchLogs() {
  if (!validateRange()) return
  loading.value = true
  try {
    const response = await getAuditLogs(buildParams())
    rows.value = Array.isArray(response.data?.data) ? response.data.data : []
    total.value = Number(response.data?.meta?.total || 0)
  } finally {
    loading.value = false
  }
}

function queryLogs() {
  page.value = 1
  fetchLogs()
}

function resetFilters() {
  filters.action = ''
  filters.operator = ''
  filters.targetType = ''
  filters.startDate = ''
  filters.endDate = ''
  page.value = 1
  pageSize.value = 50
  fetchLogs()
}

function handlePageSizeChange(size) {
  pageSize.value = size
  page.value = 1
  fetchLogs()
}

function exportLogs() {
  if (!validateRange()) return
  const url = getAuditExportUrl({
    action: filters.action,
    operator: filters.operator,
    targetType: filters.targetType,
    startDate: filters.startDate,
    endDate: filters.endDate,
    limit: total.value > 0 ? Math.min(total.value, 5000) : 2000
  })
  window.open(url, '_blank', 'noopener,noreferrer')
}

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped lang="scss">
.audit-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-card,
.panel-card {
  border: 1px solid var(--app-border);
  border-radius: 24px;
  background: var(--app-surface);
  box-shadow: var(--app-shadow);
}

.hero-card,
.table-head,
.hero-actions,
.pager-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.hero-card {
  padding: 28px;
  background:
    radial-gradient(circle at top right, rgba(251, 191, 36, 0.16), transparent 30%),
    linear-gradient(135deg, #fffcf5 0%, #fff8eb 100%);
}

.hero-copy {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hero-card h2,
.table-head h3 {
  margin: 0;
}

.hero-card p,
.table-head span {
  color: var(--app-muted);
}

.eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: #fef3c7;
  color: #b45309;
  font-size: 12px;
  font-weight: 700;
}

.panel-card {
  padding: 24px;
}

.detail-pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  color: #475569;
}

.pager-row {
  margin-top: 18px;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .hero-card,
  .hero-actions,
  .table-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
