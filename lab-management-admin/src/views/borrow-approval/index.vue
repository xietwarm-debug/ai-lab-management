<template>
  <div class="borrow-page">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="eyebrow">借用流程</span>
        <h2>资产借用审批</h2>
        <p>集中处理借用审批、续借审批、扫码归还、提醒催还和赔偿登记，并支持二次确认策略提醒。</p>
      </div>
      <div class="hero-actions">
        <el-button @click="resetFilters">重置</el-button>
        <el-button type="primary" :loading="loading" @click="queryList">刷新列表</el-button>
      </div>
    </section>

    <section class="panel-card">
      <div class="status-row">
        <el-radio-group v-model="statusFilter" @change="queryList">
          <el-radio-button label="pending">待审批</el-radio-button>
          <el-radio-button label="approved">已通过</el-radio-button>
          <el-radio-button label="overdue">逾期未还</el-radio-button>
          <el-radio-button label="returned">已归还</el-radio-button>
          <el-radio-button label="rejected">已驳回</el-radio-button>
          <el-radio-button label="cancelled">已取消</el-radio-button>
          <el-radio-button label="all">全部</el-radio-button>
        </el-radio-group>
      </div>
      <el-form inline>
        <el-form-item label="申请人">
          <el-input v-model="filters.userKeyword" placeholder="账号或姓名" clearable />
        </el-form-item>
        <el-form-item label="资产关键字">
          <el-input v-model="filters.equipmentKeyword" placeholder="资产编号 / 名称 / 实验室" clearable />
        </el-form-item>
        <el-form-item label="仅风险申请">
          <el-switch v-model="riskOnly" />
        </el-form-item>
      </el-form>
    </section>

    <section class="panel-grid">
      <article class="panel-card">
        <div class="panel-head">
          <div>
            <h3>扫码归还</h3>
            <span>支持二维码、条码或资产编号</span>
          </div>
          <el-button type="primary" @click="scanReturn">提交归还</el-button>
        </div>
        <el-input v-model="scanToken" placeholder="输入扫码内容" clearable />
      </article>

      <article class="panel-card">
        <div class="panel-head">
          <div>
            <h3>待审批续借</h3>
            <span>{{ renewRows.length }} 条</span>
          </div>
          <el-button text @click="loadRenewRows">刷新</el-button>
        </div>
        <div v-if="renewRows.length" class="renew-list">
          <article v-for="item in renewRows" :key="item.id" class="renew-card">
            <strong>{{ item.equipmentName || item.equipmentAssetCode || '-' }}</strong>
            <p>申请人：{{ item.applicantUserName || '-' }}</p>
            <p>当前应还：{{ item.currentExpectedReturnAt || '-' }}</p>
            <p>申请续借到：{{ item.requestedReturnAt || '-' }}</p>
            <p>原因：{{ item.reason || '-' }}</p>
            <div class="renew-actions">
              <el-button type="primary" @click="approveRenew(item)">通过</el-button>
              <el-button type="danger" plain @click="rejectRenew(item)">驳回</el-button>
            </div>
          </article>
        </div>
        <el-empty v-else description="当前没有待审批续借" />
      </article>
    </section>

    <section class="panel-card">
      <div class="panel-head">
        <div>
          <h3>借用申请列表</h3>
          <span>已加载 {{ rows.length }} / {{ total }} 条</span>
        </div>
      </div>
      <div v-if="rows.length" class="request-list">
        <article v-for="row in rows" :key="row.id" class="request-card">
          <div class="request-head">
            <div>
              <strong>{{ row.equipmentName || row.equipmentAssetCode || '-' }}</strong>
              <p>{{ row.equipmentAssetCode || '-' }} · {{ row.equipmentLabName || '-' }}</p>
            </div>
            <div class="tag-row">
              <el-tag :type="statusTagType(row)">{{ statusText(row) }}</el-tag>
              <el-tag v-if="row.riskFlag" type="danger">风险</el-tag>
              <el-tag v-if="row.secondaryConfirmRequired" type="warning">需二次确认</el-tag>
            </div>
          </div>

          <div class="info-grid">
            <span>申请账号：{{ row.applicantUserName || '-' }}</span>
            <span>申请姓名：{{ row.applicantName || '-' }}</span>
            <span>角色：{{ roleText(row.applicantRole) }}</span>
            <span>借用时间：{{ row.borrowStartAt || '-' }}</span>
            <span>应还时间：{{ row.expectedReturnAt || '-' }}</span>
            <span v-if="row.returnedAt">归还时间：{{ row.returnedAt }}</span>
          </div>

          <p class="detail-copy">用途：{{ row.purpose || '-' }}</p>
          <p v-if="row.rejectReason" class="detail-copy">驳回原因：{{ row.rejectReason }}</p>
          <p v-if="row.adminNote" class="detail-copy">管理员备注：{{ row.adminNote }}</p>
          <p v-if="row.riskReason" class="detail-copy risk-copy">风险提醒：{{ row.riskReason }}</p>
          <p v-if="row.secondaryConfirmRequired" class="detail-copy secondary-copy">二次确认：{{ secondaryReasonText(row) }}</p>

          <div class="request-actions">
            <el-button text @click="note(row)">备注</el-button>
            <el-button v-if="row.status === 'pending'" type="primary" @click="approve(row)">通过</el-button>
            <el-button v-if="row.status === 'pending'" type="danger" plain @click="reject(row)">驳回</el-button>
            <el-button v-if="row.status === 'approved' || row.isOverdue" @click="remind(row)">手动提醒</el-button>
            <el-button v-if="row.status === 'approved' || row.isOverdue" @click="aiRemind(row)">AI 提醒</el-button>
            <el-button v-if="row.status === 'approved' || row.isOverdue" @click="createCompensation(row)">赔偿登记</el-button>
            <el-button v-if="row.status === 'approved' || row.isOverdue" type="success" plain @click="markReturned(row)">标记归还</el-button>
          </div>
        </article>
      </div>
      <el-empty v-else description="暂无借用申请" />
      <div class="pager-row">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          layout="total, sizes, prev, pager, next"
          :total="total"
          :page-sizes="[10, 20, 50]"
          @current-change="fetchList"
          @size-change="handlePageSizeChange"
        />
      </div>
    </section>

    <section class="panel-card">
      <div class="panel-head">
        <div>
          <h3>赔偿记录</h3>
          <span>{{ compensationRows.length }} 条</span>
        </div>
        <el-button text @click="loadCompensations">刷新</el-button>
      </div>
      <el-table :data="compensationRows" stripe>
        <el-table-column prop="equipmentName" label="资产" min-width="180" />
        <el-table-column prop="equipmentAssetCode" label="资产编号" min-width="160" />
        <el-table-column prop="applicantUserName" label="申请人" min-width="120" />
        <el-table-column prop="amount" label="金额" min-width="100" />
        <el-table-column prop="status" label="状态" min-width="120" />
        <el-table-column prop="createdAt" label="创建时间" min-width="180" />
        <el-table-column label="操作" min-width="180">
          <template #default="{ row }">
            <el-button v-if="row.status === 'pending'" text type="success" @click="updateCompensation(row, 'paid')">标记已支付</el-button>
            <el-button v-if="row.status === 'pending'" text type="danger" @click="updateCompensation(row, 'waived')">免除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  aiRemindBorrowRequest,
  approveBorrowRenewRequest,
  approveBorrowRequest,
  createBorrowCompensation,
  getBorrowCompensations,
  getBorrowRenewRequests,
  getBorrowRequests,
  markBorrowReturned,
  noteBorrowRequest,
  rejectBorrowRenewRequest,
  rejectBorrowRequest,
  remindBorrowRequest,
  scanReturnBorrowRequest,
  updateBorrowCompensationStatus
} from '@/api/borrow'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const statusFilter = ref('pending')
const riskOnly = ref(false)
const scanToken = ref('')
const renewRows = ref([])
const compensationRows = ref([])
const filters = reactive({
  userKeyword: '',
  equipmentKeyword: ''
})

function roleText(role) {
  if (role === 'student') return '学生'
  if (role === 'teacher') return '教师'
  if (role === 'admin') return '管理员'
  return role || '-'
}

function statusText(row) {
  if (row.status === 'pending') return '待审批'
  if (row.status === 'approved' && row.isOverdue) return '逾期未还'
  if (row.status === 'approved') return '已通过'
  if (row.status === 'returned') return '已归还'
  if (row.status === 'rejected') return '已驳回'
  if (row.status === 'cancelled') return '已取消'
  return row.status || '-'
}

function statusTagType(row) {
  if (row.status === 'pending') return 'warning'
  if (row.status === 'approved' && row.isOverdue) return 'danger'
  if (row.status === 'approved' || row.status === 'returned') return 'success'
  if (row.status === 'rejected' || row.status === 'cancelled') return 'info'
  return 'info'
}

function buildParams() {
  return {
    page: page.value,
    pageSize: pageSize.value,
    status: statusFilter.value === 'all' ? '' : statusFilter.value,
    userKeyword: filters.userKeyword,
    equipmentKeyword: filters.equipmentKeyword,
    riskOnly: riskOnly.value ? 1 : ''
  }
}

function secondaryReasonText(row) {
  const reasons = Array.isArray(row?.secondaryConfirmReasons) ? row.secondaryConfirmReasons : []
  if (!reasons.length) return '需要人工复核'
  return reasons.map((item) => {
    if (item === 'global') return '全局强制复核'
    if (item === 'risk_flag') return '命中风险申请'
    if (item === 'overdue_history') return '申请人存在逾期历史'
    if (String(item).startsWith('lab:')) return `命中实验室规则 ${item.slice(4)}`
    if (String(item).startsWith('asset:')) return `命中资产关键字 ${item.slice(6)}`
    return item
  }).join('；')
}

async function fetchList() {
  loading.value = true
  try {
    const response = await getBorrowRequests(buildParams())
    rows.value = Array.isArray(response.data?.data) ? response.data.data : []
    total.value = Number(response.data?.meta?.total || 0)
  } finally {
    loading.value = false
  }
}

async function loadRenewRows() {
  const response = await getBorrowRenewRequests({ status: 'pending' })
  renewRows.value = Array.isArray(response.data?.data) ? response.data.data : []
}

async function loadCompensations() {
  const response = await getBorrowCompensations()
  compensationRows.value = Array.isArray(response.data?.data) ? response.data.data : []
}

async function queryList() {
  page.value = 1
  await Promise.all([fetchList(), loadRenewRows(), loadCompensations()])
}

function resetFilters() {
  filters.userKeyword = ''
  filters.equipmentKeyword = ''
  riskOnly.value = false
  statusFilter.value = 'pending'
  page.value = 1
  queryList()
}

function handlePageSizeChange(size) {
  pageSize.value = size
  page.value = 1
  fetchList()
}

async function scanReturn() {
  if (!String(scanToken.value || '').trim()) {
    ElMessage.warning('请输入扫码内容')
    return
  }
  await scanReturnBorrowRequest({ token: scanToken.value.trim() })
  ElMessage.success('已完成扫码归还')
  scanToken.value = ''
  await queryList()
}

async function approveRenew(row) {
  await approveBorrowRenewRequest(row.id)
  ElMessage.success('续借已通过')
  await queryList()
}

async function rejectRenew(row) {
  const { value } = await ElMessageBox.prompt('请输入续借驳回原因', '驳回续借', {
    inputPlaceholder: '可选填写'
  })
  await rejectBorrowRenewRequest(row.id, {
    rejectReason: String(value || '').trim()
  })
  ElMessage.success('续借已驳回')
  await queryList()
}

async function approve(row) {
  const message = row.secondaryConfirmRequired
    ? `该申请命中二次确认策略：${secondaryReasonText(row)}。确认继续通过吗？`
    : `确认通过借用申请 #${row.id} 吗？`
  await ElMessageBox.confirm(message, '借用审批', { type: row.secondaryConfirmRequired ? 'error' : 'warning' })
  await approveBorrowRequest(row.id, {
    confirmSecondary: row.secondaryConfirmRequired
  })
  ElMessage.success('申请已通过')
  await queryList()
}

async function reject(row) {
  const { value } = await ElMessageBox.prompt('请输入驳回原因', '借用驳回', {
    inputPlaceholder: '可选填写'
  })
  await rejectBorrowRequest(row.id, {
    rejectReason: String(value || '').trim()
  })
  ElMessage.success('申请已驳回')
  await queryList()
}

async function note(row) {
  const { value } = await ElMessageBox.prompt('请输入管理员备注', '添加备注', {
    inputValue: row.adminNote || ''
  })
  const note = String(value || '').trim()
  if (!note) return
  await noteBorrowRequest(row.id, { note })
  ElMessage.success('备注已保存')
  await queryList()
}

async function remind(row) {
  const { value } = await ElMessageBox.prompt('请输入提醒内容', '手动提醒', {
    inputPlaceholder: '可选填写'
  })
  await remindBorrowRequest(row.id, {
    message: String(value || '').trim()
  })
  ElMessage.success('提醒已发送')
  await queryList()
}

async function aiRemind(row) {
  await aiRemindBorrowRequest(row.id)
  ElMessage.success('AI 提醒已发送')
  await queryList()
}

async function createCompensation(row) {
  const { value } = await ElMessageBox.prompt('请输入赔偿金额', '赔偿登记', {
    inputPlaceholder: '例如 200'
  })
  const amount = Number(value || 0)
  if (!Number.isFinite(amount) || amount < 0) {
    ElMessage.warning('请输入有效金额')
    return
  }
  await createBorrowCompensation(row.id, {
    amount,
    damageLevel: 'normal',
    description: `借用资产 ${row.equipmentName || row.equipmentAssetCode || row.id} 赔偿登记`
  })
  ElMessage.success('赔偿单已创建')
  await loadCompensations()
}

async function markReturned(row) {
  await ElMessageBox.confirm(`确认将申请 #${row.id} 标记为已归还吗？`, '归还确认', { type: 'warning' })
  await markBorrowReturned(row.id, {})
  ElMessage.success('已标记归还')
  await queryList()
}

async function updateCompensation(row, status) {
  await updateBorrowCompensationStatus(row.id, { status })
  ElMessage.success('赔偿状态已更新')
  await loadCompensations()
}

onMounted(() => {
  queryList()
})
</script>

<style scoped lang="scss">
.borrow-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-card,
.panel-card,
.renew-card,
.request-card {
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
    radial-gradient(circle at top right, rgba(34, 197, 94, 0.16), transparent 30%),
    linear-gradient(135deg, #fbfffc 0%, #eefaf1 100%);
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
.panel-head span,
.detail-copy,
.info-grid,
.request-head p {
  color: var(--app-muted);
}

.eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: #dcfce7;
  color: #15803d;
  font-size: 12px;
  font-weight: 700;
}

.hero-actions,
.status-row,
.request-actions,
.renew-actions,
.pager-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.panel-grid {
  display: grid;
  grid-template-columns: 1.1fr 1.4fr;
  gap: 20px;
}

.panel-card {
  padding: 24px;
}

.panel-head,
.request-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.renew-list,
.request-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.renew-card,
.request-card {
  padding: 18px;
}

.renew-card p,
.request-card p {
  margin: 6px 0 0;
}

.request-head strong,
.renew-card strong {
  color: #0f172a;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
  font-size: 13px;
}

.risk-copy {
  color: #b42318;
}

.secondary-copy {
  color: #b45309;
}

.pager-row {
  margin-top: 18px;
  justify-content: flex-end;
}

@media (max-width: 1200px) {
  .panel-grid {
    grid-template-columns: 1fr;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-card,
  .panel-head,
  .request-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
