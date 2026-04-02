<template>
  <section class="panel-card list-card">
    <div class="panel-head">
      <div class="head-title">
        <h3>未命中问题池</h3>
        <p class="sub-text">集中查看知识库没命中的问题，按频次和状态持续补齐知识内容。</p>
      </div>
      <div class="head-actions">
        <el-button class="custom-btn-plain" :loading="loading" @click="loadRows">刷新问题池</el-button>
        <el-button @click="goKnowledgeBase">去知识库补充</el-button>
      </div>
    </div>

    <div class="summary-grid">
      <article class="summary-card">
        <span class="summary-label">总问题组</span>
        <strong class="summary-value">{{ summary.total || 0 }}</strong>
      </article>
      <article class="summary-card is-pending">
        <span class="summary-label">待处理</span>
        <strong class="summary-value">{{ summary.pending || 0 }}</strong>
      </article>
      <article class="summary-card is-resolved">
        <span class="summary-label">已补充</span>
        <strong class="summary-value">{{ summary.resolved || 0 }}</strong>
      </article>
      <article class="summary-card is-ignored">
        <span class="summary-label">已忽略</span>
        <strong class="summary-value">{{ summary.ignored || 0 }}</strong>
      </article>
    </div>

    <div class="filter-bar">
      <el-form inline class="filter-form">
        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            clearable
            placeholder="问题内容 / 提问人"
            class="filter-input-long"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="filters.role" clearable placeholder="全部角色" class="filter-select">
            <el-option label="全部" value="" />
            <el-option label="学生" value="student" />
            <el-option label="教师" value="teacher" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="来源">
          <el-select v-model="filters.sourceScene" clearable placeholder="全部来源" class="filter-select">
            <el-option label="全部" value="" />
            <el-option label="知识库测试" value="knowledge" />
            <el-option label="AI 助手" value="agent" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.processStatus" clearable placeholder="全部状态" class="filter-select">
            <el-option label="全部" value="" />
            <el-option label="待处理" value="pending" />
            <el-option label="已补充" value="resolved" />
            <el-option label="已忽略" value="ignored" />
          </el-select>
        </el-form-item>
        <el-form-item class="filter-actions">
          <el-button @click="resetFilters">清空</el-button>
          <el-button type="primary" :loading="loading" @click="handleSearch">查询</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-table
      v-loading="loading"
      :data="rows"
      class="custom-table"
      :header-cell-style="{ background: '#f8fafc', color: '#64748b', fontWeight: 600 }"
    >
      <el-table-column prop="question" label="问题" min-width="280" show-overflow-tooltip />
      <el-table-column label="重复次数" width="110" align="center">
        <template #default="{ row }">
          <el-badge :value="row.repeatCount || 1" />
        </template>
      </el-table-column>
      <el-table-column label="角色" width="100">
        <template #default="{ row }">{{ roleLabel(row.role) }}</template>
      </el-table-column>
      <el-table-column label="来源" width="120">
        <template #default="{ row }">{{ sourceSceneLabel(row.sourceScene) }}</template>
      </el-table-column>
      <el-table-column label="未命中原因" width="130">
        <template #default="{ row }">
          <el-tag effect="light" size="small">{{ missReasonLabel(row.missReason) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag size="small" :type="statusTagType(row.processStatus)">{{ processStatusLabel(row.processStatus) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="最近提问" min-width="170">
        <template #default="{ row }">{{ row.lastAskedAt || '-' }}</template>
      </el-table-column>
      <el-table-column label="已关联文档" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ row.resolvedDocumentTitle || '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row)">详情</el-button>
          <el-button link type="primary" @click="goKnowledgeBase(row)">去补知识</el-button>
          <el-button
            v-if="row.processStatus !== 'ignored'"
            link
            type="danger"
            :loading="actionLoadingGroupKey === row.groupKey && actionLoadingType === 'ignored'"
            @click="quickUpdateStatus(row, 'ignored')"
          >
            忽略
          </el-button>
          <el-button
            v-if="row.processStatus !== 'pending'"
            link
            :loading="actionLoadingGroupKey === row.groupKey && actionLoadingType === 'pending'"
            @click="quickUpdateStatus(row, 'pending')"
          >
            恢复待处理
          </el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="当前筛选条件下暂无未命中问题" :image-size="100" />
      </template>
    </el-table>

    <div class="pager-row">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        layout="total, sizes, prev, pager, next"
        :total="total"
        :page-sizes="[10, 20, 50]"
        @current-change="loadRows"
        @size-change="handlePageSizeChange"
      />
    </div>

    <el-drawer v-model="detailVisible" title="未命中问题详情" size="620px">
      <div v-loading="detailLoading" class="detail-body">
        <template v-if="detail">
          <section class="detail-card">
            <div class="detail-top">
              <h4>{{ detail.question || activeRow?.question || '未命名问题' }}</h4>
              <el-tag :type="statusTagType(detail.processStatus)">{{ processStatusLabel(detail.processStatus) }}</el-tag>
            </div>
            <p class="detail-meta">
              已收集 {{ detail.examples?.length || 0 }} 条近似提问记录
              <span v-if="detail.resolvedBy">，最近处理人：{{ detail.resolvedBy }}</span>
              <span v-if="detail.resolvedAt">，处理时间：{{ detail.resolvedAt }}</span>
            </p>
          </section>

          <section class="detail-card">
            <div class="detail-section-head">
              <h5>处理动作</h5>
              <span class="muted-text">可选地关联一篇已启用知识文档，方便后续追踪。</span>
            </div>
            <el-select
              v-model="detailForm.resolvedDocumentId"
              filterable
              clearable
              placeholder="选择已补充的知识文档（可选）"
              class="detail-doc-select"
              :loading="knowledgeOptionsLoading"
              @visible-change="handleKnowledgeSelectVisible"
            >
              <el-option
                v-for="item in knowledgeOptions"
                :key="item.id"
                :label="item.title"
                :value="item.id"
              />
            </el-select>
            <div class="detail-actions">
              <el-button
                type="primary"
                :loading="actionLoadingGroupKey === activeGroupKey && actionLoadingType === 'resolved'"
                @click="submitResolved"
              >
                标记已补充
              </el-button>
              <el-button
                :loading="actionLoadingGroupKey === activeGroupKey && actionLoadingType === 'pending'"
                @click="submitStatus('pending')"
              >
                标记待处理
              </el-button>
              <el-button
                type="danger"
                plain
                :loading="actionLoadingGroupKey === activeGroupKey && actionLoadingType === 'ignored'"
                @click="submitStatus('ignored')"
              >
                标记忽略
              </el-button>
            </div>
            <div v-if="detail.resolvedDocument" class="resolved-doc-card">
              <span class="resolved-doc-label">当前关联文档</span>
              <strong>{{ detail.resolvedDocument.title }}</strong>
              <span class="muted-text">状态：{{ detail.resolvedDocument.status || '-' }}</span>
            </div>
          </section>

          <section class="detail-card">
            <div class="detail-section-head">
              <h5>最近提问样例</h5>
            </div>
            <div class="example-list">
              <article v-for="item in detail.examples || []" :key="item.id" class="example-item">
                <div class="example-top">
                  <strong>{{ item.question }}</strong>
                  <span>{{ item.createdAt || '-' }}</span>
                </div>
                <div class="example-meta">
                  <span>{{ roleLabel(item.role) }}</span>
                  <span>{{ sourceSceneLabel(item.sourceScene) }}</span>
                  <span>{{ item.username || '匿名用户' }}</span>
                  <span>{{ missReasonLabel(item.missReason) }}</span>
                </div>
              </article>
            </div>
          </section>
        </template>
        <el-empty v-else description="暂无详情" :image-size="90" />
      </div>
    </el-drawer>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import {
  getKnowledgeDocuments,
  getUnmatchedKnowledgeQuestionDetail,
  getUnmatchedKnowledgeQuestions,
  updateUnmatchedKnowledgeQuestionStatus
} from '@/api/knowledge'

const router = useRouter()
const loading = ref(false)
const detailLoading = ref(false)
const detailVisible = ref(false)
const knowledgeOptionsLoading = ref(false)
const actionLoadingGroupKey = ref('')
const actionLoadingType = ref('')
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const detail = ref(null)
const activeRow = ref(null)
const activeGroupKey = ref('')
const knowledgeOptions = ref([])
const summary = reactive({
  total: 0,
  pending: 0,
  resolved: 0,
  ignored: 0
})
const filters = reactive({
  keyword: '',
  role: '',
  sourceScene: '',
  processStatus: ''
})
const detailForm = reactive({
  resolvedDocumentId: null
})

function roleLabel(role) {
  if (role === 'teacher') return '教师'
  if (role === 'admin') return '管理员'
  return '学生'
}

function sourceSceneLabel(scene) {
  if (scene === 'agent') return 'AI 助手'
  if (scene === 'knowledge') return '知识库测试'
  return '其他'
}

function missReasonLabel(reason) {
  if (reason === 'low_score') return '相关度偏低'
  if (reason === 'no_document') return '暂无文档'
  return '未分类'
}

function processStatusLabel(status) {
  if (status === 'resolved') return '已补充'
  if (status === 'ignored') return '已忽略'
  return '待处理'
}

function statusTagType(status) {
  if (status === 'resolved') return 'success'
  if (status === 'ignored') return 'info'
  return 'warning'
}

function buildParams() {
  return {
    page: page.value,
    pageSize: pageSize.value,
    keyword: filters.keyword || undefined,
    role: filters.role || undefined,
    sourceScene: filters.sourceScene || undefined,
    processStatus: filters.processStatus || undefined
  }
}

async function loadRows() {
  loading.value = true
  try {
    const response = await getUnmatchedKnowledgeQuestions(buildParams())
    rows.value = Array.isArray(response.data?.data) ? response.data.data : []
    total.value = Number(response.data?.meta?.total || 0)
    const payload = response.data?.summary || {}
    summary.total = Number(payload.total || 0)
    summary.pending = Number(payload.pending || 0)
    summary.resolved = Number(payload.resolved || 0)
    summary.ignored = Number(payload.ignored || 0)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadRows()
}

function resetFilters() {
  filters.keyword = ''
  filters.role = ''
  filters.sourceScene = ''
  filters.processStatus = ''
  handleSearch()
}

function handlePageSizeChange(size) {
  pageSize.value = size
  page.value = 1
  loadRows()
}

async function ensureKnowledgeOptions() {
  if (knowledgeOptions.value.length || knowledgeOptionsLoading.value) return
  knowledgeOptionsLoading.value = true
  try {
    const response = await getKnowledgeDocuments({ status: 'active' })
    const docs = Array.isArray(response.data?.data) ? response.data.data : []
    knowledgeOptions.value = docs.map((item) => ({
      id: Number(item.id || 0),
      title: String(item.title || '').trim() || `文档 ${item.id}`
    }))
  } finally {
    knowledgeOptionsLoading.value = false
  }
}

async function openDetail(row) {
  activeRow.value = row
  activeGroupKey.value = String(row?.groupKey || '').trim()
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  detailForm.resolvedDocumentId = row?.resolvedDocumentId || null
  try {
    await ensureKnowledgeOptions()
    const response = await getUnmatchedKnowledgeQuestionDetail(activeGroupKey.value)
    detail.value = response.data?.data || null
    detailForm.resolvedDocumentId = detail.value?.resolvedDocument?.id || row?.resolvedDocumentId || null
  } finally {
    detailLoading.value = false
  }
}

async function submitStatus(processStatus) {
  if (!activeGroupKey.value) return
  actionLoadingGroupKey.value = activeGroupKey.value
  actionLoadingType.value = processStatus
  try {
    await updateUnmatchedKnowledgeQuestionStatus({
      groupKey: activeGroupKey.value,
      processStatus,
      resolvedDocumentId: processStatus === 'resolved' ? detailForm.resolvedDocumentId || undefined : undefined
    })
    ElMessage.success(`已更新为${processStatusLabel(processStatus)}`)
    await Promise.all([loadRows(), openDetail(activeRow.value)])
  } finally {
    actionLoadingGroupKey.value = ''
    actionLoadingType.value = ''
  }
}

async function quickUpdateStatus(row, processStatus) {
  actionLoadingGroupKey.value = String(row?.groupKey || '').trim()
  actionLoadingType.value = processStatus
  try {
    await updateUnmatchedKnowledgeQuestionStatus({
      groupKey: row.groupKey,
      processStatus
    })
    ElMessage.success(`已更新为${processStatusLabel(processStatus)}`)
    await loadRows()
    if (detailVisible.value && activeGroupKey.value === row.groupKey) {
      await openDetail(row)
    }
  } finally {
    actionLoadingGroupKey.value = ''
    actionLoadingType.value = ''
  }
}

function submitResolved() {
  submitStatus('resolved')
}

function handleKnowledgeSelectVisible(visible) {
  if (visible) {
    ensureKnowledgeOptions()
  }
}

function goKnowledgeBase(row = null) {
  router.push({
    path: '/ai-knowledge-center',
    query: {
      tab: 'knowledge',
      from: 'miss',
      keyword: row?.question || filters.keyword || undefined
    }
  })
}

onMounted(() => {
  loadRows()
})
</script>

<style scoped lang="scss">
.head-actions,
.detail-top,
.detail-actions,
.example-top,
.example-meta,
.pager-row {
  display: flex;
  align-items: center;
}

.head-actions,
.detail-actions,
.example-meta {
  gap: 10px;
  flex-wrap: wrap;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.filter-bar {
  margin-bottom: 18px;
}

.filter-select {
  width: 160px;
}

.filter-input-long {
  width: 260px;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 18px;
  border-radius: 16px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
}

.summary-card.is-pending {
  background: linear-gradient(180deg, rgba(255, 251, 235, 0.98), rgba(255, 255, 255, 0.98));
}

.summary-card.is-resolved {
  background: linear-gradient(180deg, rgba(240, 253, 244, 0.98), rgba(255, 255, 255, 0.98));
}

.summary-card.is-ignored {
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.98), rgba(255, 255, 255, 0.98));
}

.summary-label,
.sub-text,
.muted-text,
.detail-meta,
.example-meta,
.resolved-doc-label {
  color: #64748b;
}

.summary-value {
  color: #0f172a;
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}

.pager-row {
  margin-top: 18px;
  justify-content: flex-end;
}

.detail-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-card {
  padding: 18px;
  border-radius: 18px;
  background: #f8fafc;
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.detail-top,
.detail-section-head,
.example-top {
  justify-content: space-between;
  gap: 12px;
}

.detail-top h4,
.detail-section-head h5 {
  margin: 0;
  color: #0f172a;
}

.detail-meta {
  margin: 10px 0 0;
  line-height: 1.7;
}

.detail-doc-select {
  width: 100%;
  margin-bottom: 14px;
}

.resolved-doc-card {
  margin-top: 14px;
  padding: 14px 16px;
  border-radius: 14px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.example-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.example-item {
  padding: 14px 16px;
  border-radius: 14px;
  background: #ffffff;
}

.example-top strong {
  color: #0f172a;
}

@media (max-width: 960px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .head-actions,
  .detail-top,
  .detail-section-head,
  .example-top,
  .pager-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
