<template>
  <div class="page-wrap">
    <section class="page-head">
      <div>
        <span class="eyebrow">维护工单</span>
        <h2>报修工单管理</h2>
        <p>统一跟进报修工单的查询、分派、处理和完结流转，方便后台及时掌握设备与实验室维护进度。</p>
      </div>
      <div class="head-actions">
        <el-button @click="resetFilters">重置筛选</el-button>
        <el-button :loading="loading" @click="fetchRows">刷新工单</el-button>
      </div>
    </section>

    <section class="page-card">
      <el-form inline>
        <el-form-item label="状态">
          <el-select v-model="filters.status" style="width: 160px">
            <el-option label="全部" value="" />
            <el-option label="已提交" value="submitted" />
            <el-option label="已受理" value="accepted" />
            <el-option label="处理中" value="processing" />
            <el-option label="已完成" value="completed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="工单号 / 描述 / 设备 / 提交人" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-button @click="resetFilters">重置筛选</el-button>
          <el-button type="primary" :loading="loading" @click="handleSearch">查询工单</el-button>
        </el-form-item>
      </el-form>

      <div class="summary-row">
        <span class="summary-text">当前共 {{ total }} 条工单，处理中 {{ activeCount }} 条</span>
      </div>

      <el-table v-loading="loading" :data="rows">
        <el-table-column prop="orderNo" label="工单号" min-width="170" />
        <el-table-column prop="labName" label="实验室" min-width="140" />
        <el-table-column prop="equipmentName" label="设备" min-width="160" />
        <el-table-column prop="submitterName" label="提交人" width="110" />
        <el-table-column prop="issueType" label="故障类型" width="120" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="问题描述" min-width="260" show-overflow-tooltip />
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button
              v-if="nextStatus(row.status)"
              link
              type="success"
              @click="advanceStatus(row)"
            >
              标记为{{ statusLabel(nextStatus(row.status)) }}
            </el-button>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="当前筛选条件下暂无工单数据" />
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

    <el-drawer v-model="detailVisible" title="工单详情" size="560px">
      <div v-loading="detailLoading" class="detail-body">
        <el-descriptions v-if="detail" :column="1" border>
          <el-descriptions-item label="工单号">{{ detail.orderNo || '-' }}</el-descriptions-item>
          <el-descriptions-item label="实验室">{{ detail.labName || '-' }}</el-descriptions-item>
          <el-descriptions-item label="设备">{{ detail.equipmentName || '-' }}</el-descriptions-item>
          <el-descriptions-item label="资产编号">{{ detail.assetCode || '-' }}</el-descriptions-item>
          <el-descriptions-item label="提交人">{{ detail.submitterName || '-' }}</el-descriptions-item>
          <el-descriptions-item label="受理人">{{ detail.assigneeName || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ statusLabel(detail.status) }}</el-descriptions-item>
          <el-descriptions-item label="故障类型">{{ detail.issueType || '-' }}</el-descriptions-item>
          <el-descriptions-item label="问题描述">{{ detail.description || '-' }}</el-descriptions-item>
          <el-descriptions-item label="提交时间">{{ detail.submittedAt || '-' }}</el-descriptions-item>
          <el-descriptions-item label="受理时间">{{ detail.acceptedAt || '-' }}</el-descriptions-item>
          <el-descriptions-item label="处理开始">{{ detail.processingAt || '-' }}</el-descriptions-item>
          <el-descriptions-item label="完成时间">{{ detail.completedAt || '-' }}</el-descriptions-item>
        </el-descriptions>

        <section v-if="detail" class="detail-section">
          <h3>处理时长</h3>
          <div class="duration-grid">
            <article class="duration-card">
              <span>响应耗时</span>
              <strong>{{ minuteText(detail.durations?.responseMinutes) }}</strong>
            </article>
            <article class="duration-card">
              <span>处理耗时</span>
              <strong>{{ minuteText(detail.durations?.processingMinutes) }}</strong>
            </article>
            <article class="duration-card">
              <span>总耗时</span>
              <strong>{{ minuteText(detail.durations?.totalMinutes) }}</strong>
            </article>
          </div>
        </section>

        <section v-if="detail" class="detail-section">
          <h3>AI 辅助信息</h3>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="AI 判断类型">{{ detail.ai?.issueType || '-' }}</el-descriptions-item>
            <el-descriptions-item label="AI 优先级">{{ detail.ai?.priority || '-' }}</el-descriptions-item>
            <el-descriptions-item label="AI 摘要">{{ detail.ai?.summary || '-' }}</el-descriptions-item>
            <el-descriptions-item label="可能原因">{{ listText(detail.ai?.possibleCauses) }}</el-descriptions-item>
            <el-descriptions-item label="建议动作">{{ listText(detail.ai?.suggestions) }}</el-descriptions-item>
            <el-descriptions-item label="置信度">{{ detail.ai?.confidence ?? '-' }}</el-descriptions-item>
          </el-descriptions>
        </section>

        <section v-if="detail" class="detail-section">
          <h3>附件</h3>
          <el-table :data="detail.attachments || []" size="small">
            <el-table-column prop="name" label="名称" min-width="180" />
            <el-table-column prop="fileType" label="类型" width="100" />
            <el-table-column prop="createdAt" label="上传时间" min-width="150" />
            <template #empty>
              <el-empty description="暂无附件" :image-size="70" />
            </template>
          </el-table>
        </section>

        <el-empty v-if="!detail && !detailLoading" description="暂无工单详情" />
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { getRepairOrderDetail, getRepairOrders, updateRepairOrderStatus } from '@/api/repairs'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const loading = ref(false)
const detailLoading = ref(false)
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const detailVisible = ref(false)
const detail = ref(null)
const activeCount = computed(() => rows.value.filter((item) => ['submitted', 'accepted', 'processing'].includes(item.status)).length)

const filters = reactive({
  status: '',
  keyword: ''
})

function statusLabel(status) {
  if (status === 'accepted') return '已受理'
  if (status === 'processing') return '处理中'
  if (status === 'completed') return '已完成'
  if (status === 'cancelled') return '已取消'
  return '已提交'
}

function statusType(status) {
  if (status === 'completed') return 'success'
  if (status === 'processing') return 'warning'
  if (status === 'accepted') return 'primary'
  if (status === 'cancelled') return 'info'
  return ''
}

function nextStatus(status) {
  if (status === 'submitted') return 'accepted'
  if (status === 'accepted') return 'processing'
  if (status === 'processing') return 'completed'
  return ''
}

function minuteText(value) {
  if (value === undefined || value === null || value === '') return '-'
  return `${value} 分钟`
}

function listText(items) {
  return Array.isArray(items) && items.length ? items.join('；') : '-'
}

function buildParams() {
  return {
    page: page.value,
    pageSize: pageSize.value,
    status: filters.status,
    keyword: filters.keyword
  }
}

function handleSearch() {
  page.value = 1
  fetchRows()
}

async function fetchRows() {
  loading.value = true
  try {
    const response = await getRepairOrders(buildParams())
    rows.value = response.data?.data || []
    total.value = response.data?.meta?.total || 0
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.status = ''
  filters.keyword = ''
  handleSearch()
}

function handlePageSizeChange(size) {
  pageSize.value = size
  page.value = 1
  fetchRows()
}

async function openDetail(row) {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    const response = await getRepairOrderDetail(row.id)
    detail.value = response.data?.data || null
  } finally {
    detailLoading.value = false
  }
}

async function advanceStatus(row) {
  const targetStatus = nextStatus(row.status)
  if (!targetStatus) return
  await ElMessageBox.confirm(`确认将工单推进到“${statusLabel(targetStatus)}”吗？`, '工单流转', { type: 'warning' })
  await updateRepairOrderStatus(row.id, {
    status: targetStatus,
    assigneeName: authStore.username
  })
  ElMessage.success(`工单已更新为${statusLabel(targetStatus)}`)
  if (detail.value?.id === row.id) {
    await openDetail(row)
  }
  fetchRows()
}

onMounted(() => {
  fetchRows()
})
</script>

<style scoped lang="scss">
.page-wrap {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-head,
.page-card {
  padding: 24px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 24px;
  box-shadow: var(--app-shadow);
}

.page-head {
  position: relative;
  overflow: hidden;
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

.page-card {
  background: var(--app-surface);
}

.page-head,
.head-actions,
.pager-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.head-actions {
  position: relative;
  z-index: 1;
  flex-wrap: wrap;
}

.page-head h2 {
  margin: 8px 0 10px;
  font-size: 30px;
}

.page-head p,
.summary-text {
  margin: 0;
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

.summary-row {
  margin: 6px 0 16px;
}

.pager-row {
  margin-top: 18px;
  justify-content: flex-end;
}

.detail-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.detail-section h3 {
  margin: 0 0 12px;
}

.duration-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.duration-card {
  padding: 16px;
  border-radius: 16px;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.duration-card span {
  color: var(--app-muted);
}

.duration-card strong {
  font-size: 22px;
}

@media (max-width: 960px) {
  .duration-grid {
    grid-template-columns: 1fr;
  }
}
</style>
