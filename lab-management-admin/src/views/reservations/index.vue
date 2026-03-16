<template>
  <div class="reservation-page">
    <section class="page-toolbar">
      <div class="toolbar-copy">
        <h2>预约审批管理</h2>
        <p>复用 `/reservations`、审批接口和 AI 建议接口，支持管理员与教师角色。</p>
      </div>
      <div class="toolbar-actions">
        <el-button @click="resetFilters">重置筛选</el-button>
        <el-button type="primary" :loading="loading" @click="fetchRows">刷新列表</el-button>
      </div>
    </section>

    <section class="filter-card">
      <el-form inline>
        <el-form-item label="状态">
          <el-select v-model="filters.status" style="width: 160px">
            <el-option label="全部" value="" />
            <el-option label="待审批" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已驳回" value="rejected" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="实验室">
          <el-input v-model="filters.labKeyword" placeholder="实验室名称" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item v-if="isAdmin" label="预约人">
          <el-input v-model="filters.userKeyword" placeholder="用户名" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="filters.dateFrom" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="filters.dateTo" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item>
          <el-button @click="resetFilters">重置筛选</el-button>
          <el-button type="primary" :loading="loading" @click="handleSearch">查询列表</el-button>
        </el-form-item>
      </el-form>
    </section>

    <section class="table-card">
      <div class="table-actions">
        <div class="summary-text">当前共 {{ total }} 条预约记录，待审批 {{ pendingCount }} 条</div>
        <el-button
          v-if="selectedIds.length"
          type="success"
          @click="handleBatchApprove"
        >
          批量通过 {{ selectedIds.length }} 项
        </el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="rows"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="48" :selectable="selectableRow" />
        <el-table-column prop="labName" label="实验室" min-width="150" />
        <el-table-column prop="user" label="预约人" min-width="110" />
        <el-table-column label="日期 / 时段" min-width="220">
          <template #default="{ row }">
            <div>{{ row.date }}</div>
            <div class="cell-sub">{{ row.time }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="用途" min-width="220" show-overflow-tooltip />
        <el-table-column label="审批角色" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="row.reviewRole === 'teacher' ? 'warning' : 'info'">
              {{ reviewRoleText(row.reviewRole) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <div class="action-row">
              <el-button link type="primary" @click="viewDetail(row)">详情</el-button>
              <el-button
                v-if="row.status === 'pending'"
                link
                type="success"
                @click="handleApprove(row)"
              >
                通过
              </el-button>
              <el-button
                v-if="row.status === 'pending'"
                link
                type="danger"
                @click="handleReject(row)"
              >
                驳回
              </el-button>
              <el-button
                v-if="row.status === 'pending'"
                link
                @click="showAiDialog(row)"
              >
                AI 建议
              </el-button>
              <el-button
                v-if="isAdmin"
                link
                @click="handleNote(row)"
              >
                备注
              </el-button>
            </div>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="当前筛选条件下暂无预约记录" />
        </template>
      </el-table>

      <div class="pager-row">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          layout="total, sizes, prev, pager, next"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          @current-change="fetchRows"
          @size-change="handlePageSizeChange"
        />
      </div>
    </section>

    <el-drawer v-model="detailVisible" title="预约详情" size="520px">
      <el-descriptions v-if="detail" :column="1" border>
        <el-descriptions-item label="预约编号">{{ detail.id }}</el-descriptions-item>
        <el-descriptions-item label="实验室">{{ detail.labName || '-' }}</el-descriptions-item>
        <el-descriptions-item label="实验室 ID">{{ detail.labId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="预约人">{{ detail.user || '-' }}</el-descriptions-item>
        <el-descriptions-item label="日期">{{ detail.date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="时间">{{ detail.time || '-' }}</el-descriptions-item>
        <el-descriptions-item label="用途">{{ detail.reason || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ statusLabel(detail.status) }}</el-descriptions-item>
        <el-descriptions-item label="审批角色">{{ reviewRoleText(detail.reviewRole) }}</el-descriptions-item>
        <el-descriptions-item label="审批策略">{{ detail.reviewPolicy || '-' }}</el-descriptions-item>
        <el-descriptions-item label="提交时间">{{ detail.createdAt || '-' }}</el-descriptions-item>
        <el-descriptions-item label="驳回原因">{{ detail.rejectReason || '-' }}</el-descriptions-item>
        <el-descriptions-item label="管理员备注">{{ detail.adminNote || '-' }}</el-descriptions-item>
      </el-descriptions>
      <el-empty v-else description="暂无详情数据" />
    </el-drawer>

    <el-dialog v-model="aiVisible" title="AI 审批建议" width="640px">
      <div v-if="aiSuggestion" v-loading="aiLoading" class="ai-card">
        <p><strong>结论：</strong>{{ aiDecisionText(aiSuggestion.decision) }}</p>
        <p><strong>评分：</strong>{{ aiSuggestion.score ?? '-' }}</p>
        <p><strong>摘要：</strong>{{ aiSuggestion.summary || '-' }}</p>
        <p><strong>支持理由：</strong>{{ listText(aiSuggestion.reasons) }}</p>
        <p><strong>风险提示：</strong>{{ listText(aiSuggestion.risks) }}</p>
        <p><strong>建议动作：</strong>{{ listText(aiSuggestion.nextActions) }}</p>
        <p><strong>辅助指标：</strong>{{ aiMetricText(aiSuggestion.metrics) }}</p>
      </div>
      <el-empty v-else-if="!aiLoading" description="暂无 AI 建议" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  addReservationNote,
  approveReservation,
  batchApproveReservations,
  getReservationAiSuggestion,
  getReservationDetail,
  getReservationList,
  rejectReservation
} from '@/api/reservations'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const isAdmin = computed(() => authStore.role === 'admin')
const loading = ref(false)
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const selectedIds = ref([])
const detailVisible = ref(false)
const detail = ref(null)
const aiVisible = ref(false)
const aiLoading = ref(false)
const aiSuggestion = ref(null)
const pendingCount = computed(() => rows.value.filter((item) => item.status === 'pending').length)

const filters = reactive({
  status: 'pending',
  labKeyword: '',
  userKeyword: '',
  dateFrom: '',
  dateTo: ''
})

function statusLabel(status) {
  if (status === 'approved') return '已通过'
  if (status === 'rejected') return '已驳回'
  if (status === 'cancelled') return '已取消'
  return '待审批'
}

function statusTagType(status) {
  if (status === 'approved') return 'success'
  if (status === 'rejected') return 'danger'
  if (status === 'cancelled') return 'info'
  return 'warning'
}

function aiDecisionText(decision) {
  if (decision === 'approve') return '建议通过'
  if (decision === 'reject') return '建议驳回'
  return '建议人工复核'
}

function reviewRoleText(reviewRole) {
  return reviewRole === 'teacher' ? '教师审批' : '管理员审批'
}

function listText(items) {
  return Array.isArray(items) && items.length ? items.join('；') : '-'
}

function aiMetricText(metrics) {
  if (!metrics || typeof metrics !== 'object') return '-'
  const pairs = Object.entries(metrics)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([key, value]) => `${key}: ${value}`)
  return pairs.join('；') || '-'
}

function selectableRow(row) {
  return row.status === 'pending'
}

function validateDateRange() {
  if (!filters.dateFrom || !filters.dateTo) return true
  if (filters.dateFrom <= filters.dateTo) return true
  ElMessage.warning('开始日期不能大于结束日期')
  return false
}

function buildParams() {
  return {
    page: page.value,
    pageSize: pageSize.value,
    status: filters.status,
    labKeyword: filters.labKeyword,
    userKeyword: isAdmin.value ? filters.userKeyword : '',
    dateFrom: filters.dateFrom,
    dateTo: filters.dateTo
  }
}

function handleSearch() {
  page.value = 1
  fetchRows()
}

async function fetchRows() {
  if (!validateDateRange()) return
  loading.value = true
  try {
    const response = await getReservationList(buildParams())
    rows.value = response.data?.data || []
    total.value = response.data?.meta?.total || 0
    selectedIds.value = []
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.status = 'pending'
  filters.labKeyword = ''
  filters.userKeyword = ''
  filters.dateFrom = ''
  filters.dateTo = ''
  handleSearch()
}

function handleSelectionChange(selection) {
  selectedIds.value = selection.map((item) => Number(item.id)).filter((id) => id > 0)
}

function handlePageSizeChange(size) {
  pageSize.value = size
  page.value = 1
  fetchRows()
}

async function handleApprove(row) {
  await ElMessageBox.confirm(`确认通过 ${row.user} 的这条预约吗？`, '预约审批', {
    type: 'warning'
  })
  await approveReservation(row.id)
  ElMessage.success('预约已通过')
  fetchRows()
}

async function handleReject(row) {
  const { value } = await ElMessageBox.prompt('请输入驳回原因', '预约驳回', {
    inputPlaceholder: '例如：时间冲突、用途不完整',
    inputValidator: (inputValue) => Boolean(String(inputValue || '').trim()),
    inputErrorMessage: '请填写驳回原因'
  })
  await rejectReservation(row.id, {
    rejectReason: String(value || '').trim()
  })
  ElMessage.success('预约已驳回')
  fetchRows()
}

async function handleBatchApprove() {
  if (!selectedIds.value.length) return
  await ElMessageBox.confirm(`确认批量通过 ${selectedIds.value.length} 条预约吗？`, '批量审批', {
    type: 'warning'
  })
  const response = await batchApproveReservations(selectedIds.value)
  const data = response.data?.data || {}
  const lines = [`成功 ${data.count || 0} 条`]
  if (data.conflictIds?.length) lines.push(`冲突 ${data.conflictIds.length} 条`)
  if (data.invalidStatusIds?.length) lines.push(`状态不符 ${data.invalidStatusIds.length} 条`)
  if (data.invalidScheduleIds?.length) lines.push(`时间规则不符 ${data.invalidScheduleIds.length} 条`)
  if (data.notFoundIds?.length) lines.push(`记录不存在 ${data.notFoundIds.length} 条`)
  if (data.busyIds?.length) lines.push(`并发占用 ${data.busyIds.length} 条`)
  if (data.forbiddenIds?.length) lines.push(`无审批权限 ${data.forbiddenIds.length} 条`)
  ElMessage.success(lines.join('，'))
  fetchRows()
}

async function handleNote(row) {
  const { value } = await ElMessageBox.prompt('请输入管理员备注', '添加备注', {
    inputPlaceholder: '补充审批说明',
    inputValue: row.adminNote || ''
  })
  await addReservationNote(row.id, {
    note: String(value || '').trim()
  })
  ElMessage.success('备注已保存')
  fetchRows()
}

async function viewDetail(row) {
  const response = await getReservationDetail(row.id)
  detail.value = response.data?.data || null
  detailVisible.value = true
}

async function showAiDialog(row) {
  aiVisible.value = true
  aiLoading.value = true
  aiSuggestion.value = null
  try {
    const response = await getReservationAiSuggestion(row.id)
    aiSuggestion.value = response.data?.data?.suggestion || null
  } finally {
    aiLoading.value = false
  }
}

onMounted(() => {
  fetchRows()
})
</script>

<style scoped lang="scss">
.reservation-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-toolbar,
.filter-card,
.table-card {
  padding: 24px;
  border: 1px solid var(--app-border);
  border-radius: 24px;
  background: var(--app-surface);
  box-shadow: var(--app-shadow);
}

.page-toolbar,
.table-actions,
.toolbar-actions,
.pager-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.toolbar-copy h2 {
  margin: 0 0 8px;
}

.toolbar-copy p,
.summary-text,
.cell-sub {
  margin: 0;
  color: var(--app-muted);
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 10px;
}

.pager-row {
  margin-top: 18px;
  justify-content: flex-end;
}

.ai-card {
  min-height: 120px;
  line-height: 1.8;
}

@media (max-width: 960px) {
  .page-toolbar,
  .table-actions {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
