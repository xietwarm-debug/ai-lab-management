<template>
  <div class="knowledge-page">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="eyebrow">知识库管理</span>
        <h2>文档维护、索引重建与问答反馈</h2>
        <p>后台可以直接维护制度、实验室规范、借用规则和排课说明，并将结果联动给 AI 助手和知识问答。</p>
        <div class="hero-meta">
          <span>文档 {{ rows.length }} 篇</span>
          <span>启用 {{ activeCount }} 篇</span>
          <span>反馈 {{ feedbackTotal }} 条</span>
        </div>
      </div>
      <div class="hero-actions">
        <el-button :loading="loading" @click="reloadAll">刷新</el-button>
        <el-button type="primary" @click="resetForm">新建文档</el-button>
      </div>
    </section>

    <section class="panel-grid">
      <article class="panel-card editor-card">
        <div class="panel-head">
          <div>
            <h3>{{ editingId ? '编辑知识文档' : '新建知识文档' }}</h3>
            <span>保存后会自动重建该文档索引</span>
          </div>
          <div class="head-actions">
            <el-button v-if="editingId" @click="resetForm">取消编辑</el-button>
            <el-button @click="fillDemo">填入示例</el-button>
          </div>
        </div>

        <el-form label-position="top">
          <div class="form-grid">
            <el-form-item label="标题">
              <el-input v-model="form.title" maxlength="200" placeholder="例如：实验室预约管理规范" />
            </el-form-item>
            <el-form-item label="来源链接">
              <el-input v-model="form.sourceUrl" maxlength="500" placeholder="https://..." />
            </el-form-item>
            <el-form-item label="分类">
              <el-select v-model="form.category">
                <el-option v-for="item in categoryOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="适用角色">
              <el-select v-model="form.scopeRole">
                <el-option v-for="item in scopeOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="form.status">
                <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
          </div>

          <el-form-item label="正文">
            <el-input
              v-model="form.content"
              type="textarea"
              :rows="14"
              maxlength="200000"
              show-word-limit
              placeholder="粘贴制度、说明书、操作规范或 FAQ 正文"
            />
          </el-form-item>

          <div class="editor-actions">
            <el-button type="primary" :loading="saving" @click="submitForm">
              {{ editingId ? '保存并重建索引' : '创建并建立索引' }}
            </el-button>
          </div>
        </el-form>
      </article>

      <article class="panel-card ask-card">
        <div class="panel-head">
          <div>
            <h3>知识问答自测</h3>
            <span>直接验证知识库能否回答制度与规则问题</span>
          </div>
          <el-button text @click="question = defaultQuestion">恢复示例</el-button>
        </div>

        <el-input
          v-model="question"
          maxlength="160"
          placeholder="例如：实验室预约最多可提前几天？"
          @keyup.enter="runKnowledgeAsk"
        />

        <div class="ask-actions">
          <el-button type="primary" :loading="asking" @click="runKnowledgeAsk">测试检索</el-button>
          <el-button @click="goAiAssistant">去 AI 助手联动验证</el-button>
        </div>

        <div class="answer-panel">
          <template v-if="answerText">
            <p class="answer-text">{{ answerText }}</p>
            <div v-if="answerSources.length" class="source-list">
              <div v-for="(item, index) in answerSources" :key="`${item.documentId}-${item.chunkNo}-${index}`" class="source-item">
                <strong>{{ index + 1 }}. {{ item.title || '-' }}</strong>
                <span>{{ item.summary || item.content || '-' }}</span>
              </div>
            </div>

            <div class="feedback-box">
              <span class="feedback-label">这次回答是否有帮助？</span>
              <el-radio-group v-model="feedbackForm.helpful">
                <el-radio-button :label="true">有帮助</el-radio-button>
                <el-radio-button :label="false">没帮助</el-radio-button>
              </el-radio-group>
              <el-input
                v-model="feedbackForm.comment"
                type="textarea"
                :rows="3"
                maxlength="255"
                show-word-limit
                placeholder="可选：补充反馈，帮助优化知识库回答"
              />
              <el-button type="primary" :disabled="!queryLogId" :loading="feedbackSubmitting" @click="submitAskFeedback">
                提交反馈
              </el-button>
            </div>
          </template>
          <el-empty v-else description="还没有知识问答结果，先试一个制度或规范问题" />
        </div>
      </article>
    </section>

    <section class="panel-card">
      <div class="panel-head">
        <div>
          <h3>知识文档列表</h3>
          <span>支持状态筛选、内容维护、启停和重建索引</span>
        </div>
      </div>

      <el-form inline>
        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            clearable
            placeholder="标题 / 摘要 / 关键词"
            @keyup.enter="loadDocuments"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部状态" style="width: 160px">
            <el-option label="全部" value="" />
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="filters.category" clearable placeholder="全部分类" style="width: 180px">
            <el-option label="全部" value="" />
            <el-option v-for="item in categoryOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="resetDocFilters">清空</el-button>
          <el-button type="primary" :loading="loading" @click="loadDocuments">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table v-loading="loading" :data="rows">
        <el-table-column prop="title" label="标题" min-width="220" />
        <el-table-column label="分类" width="120">
          <template #default="{ row }">{{ categoryLabel(row.category) }}</template>
        </el-table-column>
        <el-table-column label="适用角色" width="120">
          <template #default="{ row }">{{ scopeLabel(row.scopeRole) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="分块" width="90">
          <template #default="{ row }">{{ row.chunkCount || 0 }}</template>
        </el-table-column>
        <el-table-column prop="summary" label="摘要" min-width="260" show-overflow-tooltip />
        <el-table-column label="更新时间" min-width="170">
          <template #default="{ row }">{{ row.updatedAt || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="editRow(row)">编辑</el-button>
            <el-button link type="primary" :loading="busyId === row.id && busyAction === 'reindex'" @click="reindexRow(row)">
              重建索引
            </el-button>
            <el-button link :loading="busyId === row.id && busyAction === 'status'" @click="toggleStatus(row)">
              {{ row.status === 'active' ? '停用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无知识文档" />
        </template>
      </el-table>
    </section>

    <section class="panel-card">
      <div class="panel-head">
        <div>
          <h3>问答反馈</h3>
          <span>收集知识问答质量反馈，便于继续补文档和调优索引</span>
        </div>
      </div>

      <el-form inline>
        <el-form-item label="反馈结果">
          <el-select v-model="feedbackFilters.helpful" clearable placeholder="全部反馈" style="width: 160px">
            <el-option label="全部" value="" />
            <el-option label="有帮助" value="1" />
            <el-option label="没帮助" value="0" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="feedbackFilters.keyword"
            clearable
            placeholder="问题 / 答案 / 反馈内容 / 用户"
            @keyup.enter="loadFeedback"
          />
        </el-form-item>
        <el-form-item>
          <el-button @click="resetFeedbackFilters">清空</el-button>
          <el-button type="primary" :loading="feedbackLoading" @click="loadFeedback">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table v-loading="feedbackLoading" :data="feedbackRows">
        <el-table-column label="反馈" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.helpful ? 'success' : 'danger'">
              {{ row.helpful ? '有帮助' : '没帮助' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="question" label="问题" min-width="220" show-overflow-tooltip />
        <el-table-column prop="answer" label="回答" min-width="320" show-overflow-tooltip />
        <el-table-column prop="comment" label="反馈说明" min-width="220" show-overflow-tooltip />
        <el-table-column label="用户" width="120">
          <template #default="{ row }">{{ row.username || '-' }}</template>
        </el-table-column>
        <el-table-column label="时间" min-width="170">
          <template #default="{ row }">{{ row.createdAt || row.askedAt || '-' }}</template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无知识问答反馈" />
        </template>
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import {
  askKnowledgeQuestion,
  createKnowledgeDocument,
  getKnowledgeDocumentDetail,
  getKnowledgeDocuments,
  getKnowledgeFeedbackList,
  reindexKnowledgeDocument,
  submitKnowledgeFeedback,
  updateKnowledgeDocument,
  updateKnowledgeDocumentStatus
} from '@/api/knowledge'

const router = useRouter()

const defaultQuestion = '实验室预约最多可提前几天？'

const categoryOptions = [
  { label: '规则制度', value: 'rule' },
  { label: '设备说明', value: 'manual' },
  { label: '安全规范', value: 'safety' },
  { label: '课程文档', value: 'course' },
  { label: '报修知识', value: 'repair' },
  { label: '常见问题', value: 'faq' },
  { label: '其他', value: 'other' }
]

const scopeOptions = [
  { label: '全员可见', value: 'all' },
  { label: '仅学生', value: 'student' },
  { label: '仅教师', value: 'teacher' },
  { label: '仅管理员', value: 'admin' }
]

const statusOptions = [
  { label: '草稿', value: 'draft' },
  { label: '启用', value: 'active' },
  { label: '停用', value: 'disabled' }
]

const loading = ref(false)
const feedbackLoading = ref(false)
const saving = ref(false)
const asking = ref(false)
const feedbackSubmitting = ref(false)
const busyId = ref(0)
const busyAction = ref('')
const editingId = ref(0)

const rows = ref([])
const feedbackRows = ref([])
const feedbackTotal = ref(0)

const filters = reactive({
  keyword: '',
  status: '',
  category: ''
})

const feedbackFilters = reactive({
  helpful: '',
  keyword: ''
})

const form = reactive({
  title: '',
  category: 'rule',
  scopeRole: 'all',
  status: 'active',
  sourceUrl: '',
  content: ''
})

const question = ref(defaultQuestion)
const answerText = ref('')
const answerSources = ref([])
const queryLogId = ref(0)
const feedbackForm = reactive({
  helpful: true,
  comment: ''
})

const activeCount = computed(() => rows.value.filter((item) => item.status === 'active').length)

function categoryLabel(value) {
  return categoryOptions.find((item) => item.value === value)?.label || '其他'
}

function scopeLabel(value) {
  return scopeOptions.find((item) => item.value === value)?.label || '全员可见'
}

function statusLabel(value) {
  return statusOptions.find((item) => item.value === value)?.label || '草稿'
}

function statusTagType(value) {
  if (value === 'active') return 'success'
  if (value === 'disabled') return 'danger'
  return 'warning'
}

function resetForm() {
  editingId.value = 0
  form.title = ''
  form.category = 'rule'
  form.scopeRole = 'all'
  form.status = 'active'
  form.sourceUrl = ''
  form.content = ''
}

function resetDocFilters() {
  filters.keyword = ''
  filters.status = ''
  filters.category = ''
  loadDocuments()
}

function resetFeedbackFilters() {
  feedbackFilters.helpful = ''
  feedbackFilters.keyword = ''
  loadFeedback()
}

function fillDemo() {
  form.title = '实验室预约管理规范'
  form.category = 'rule'
  form.scopeRole = 'all'
  form.status = 'active'
  form.sourceUrl = ''
  form.content = [
    '实验室预约开放时间为每日 08:00 至 22:00。',
    '',
    '学生最多可提前 7 天提交预约申请；超过 7 天的申请不予受理。',
    '',
    '高峰时段预约需要管理员审批。若与课程任务冲突，课程任务优先。'
  ].join('\n')
}

async function loadDocuments() {
  loading.value = true
  try {
    const response = await getKnowledgeDocuments({
      keyword: filters.keyword || undefined,
      status: filters.status || undefined,
      category: filters.category || undefined
    })
    rows.value = Array.isArray(response.data?.data) ? response.data.data : []
  } finally {
    loading.value = false
  }
}

async function loadFeedback() {
  feedbackLoading.value = true
  try {
    const response = await getKnowledgeFeedbackList({
      helpful: feedbackFilters.helpful || undefined,
      keyword: feedbackFilters.keyword || undefined,
      page: 1,
      pageSize: 20
    })
    feedbackRows.value = Array.isArray(response.data?.data) ? response.data.data : []
    feedbackTotal.value = Number(response.data?.meta?.total || feedbackRows.value.length || 0)
  } finally {
    feedbackLoading.value = false
  }
}

async function reloadAll() {
  await Promise.all([loadDocuments(), loadFeedback()])
}

async function editRow(row) {
  const response = await getKnowledgeDocumentDetail(row.id)
  const data = response.data?.data || {}
  editingId.value = Number(data.id || row.id || 0)
  form.title = String(data.title || '')
  form.category = String(data.category || 'rule')
  form.scopeRole = String(data.scopeRole || 'all')
  form.status = String(data.status || 'draft')
  form.sourceUrl = String(data.sourceUrl || '')
  form.content = String(data.content || '')
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function submitForm() {
  if (!String(form.title || '').trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  if (!String(form.content || '').trim()) {
    ElMessage.warning('请填写正文')
    return
  }

  saving.value = true
  try {
    const payload = {
      title: String(form.title || '').trim(),
      category: form.category,
      scopeRole: form.scopeRole,
      status: form.status,
      sourceUrl: String(form.sourceUrl || '').trim(),
      content: String(form.content || '').trim()
    }
    if (editingId.value) {
      await updateKnowledgeDocument(editingId.value, payload)
      ElMessage.success('知识文档已更新')
    } else {
      await createKnowledgeDocument(payload)
      ElMessage.success('知识文档已创建')
    }
    resetForm()
    await loadDocuments()
  } finally {
    saving.value = false
  }
}

async function reindexRow(row) {
  busyId.value = Number(row.id || 0)
  busyAction.value = 'reindex'
  try {
    await reindexKnowledgeDocument(row.id)
    ElMessage.success('索引已重建')
    await loadDocuments()
  } finally {
    busyId.value = 0
    busyAction.value = ''
  }
}

async function toggleStatus(row) {
  busyId.value = Number(row.id || 0)
  busyAction.value = 'status'
  try {
    const nextStatus = row.status === 'active' ? 'disabled' : 'active'
    await updateKnowledgeDocumentStatus(row.id, { status: nextStatus })
    ElMessage.success('文档状态已更新')
    await loadDocuments()
  } finally {
    busyId.value = 0
    busyAction.value = ''
  }
}

async function runKnowledgeAsk() {
  const query = String(question.value || '').trim()
  if (!query) {
    ElMessage.warning('请输入问题')
    return
  }
  asking.value = true
  try {
    const response = await askKnowledgeQuestion({ question: query })
    const data = response.data?.data || {}
    answerText.value = String(data.answer || '')
    answerSources.value = Array.isArray(data.sources) ? data.sources : []
    queryLogId.value = Number(data.queryLogId || 0)
    feedbackForm.helpful = true
    feedbackForm.comment = ''
    if (!data.matched) {
      answerText.value = ''
      answerSources.value = []
      queryLogId.value = 0
      ElMessage.info('当前知识库还没有命中该问题')
      return
    }
    ElMessage.success('知识问答已返回结果')
  } finally {
    asking.value = false
  }
}

async function submitAskFeedback() {
  if (!queryLogId.value) return
  feedbackSubmitting.value = true
  try {
    await submitKnowledgeFeedback({
      queryLogId: queryLogId.value,
      helpful: feedbackForm.helpful,
      comment: String(feedbackForm.comment || '').trim()
    })
    ElMessage.success('反馈已提交')
    await loadFeedback()
  } finally {
    feedbackSubmitting.value = false
  }
}

function goAiAssistant() {
  router.push({
    path: '/ai-assistant',
    query: {
      tab: 'knowledge',
      question: question.value || defaultQuestion
    }
  })
}

onMounted(() => {
  reloadAll()
})
</script>

<style scoped lang="scss">
.knowledge-page {
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

.hero-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 28px;
  background:
    radial-gradient(circle at top right, rgba(14, 165, 233, 0.14), transparent 34%),
    linear-gradient(135deg, #fbfdff 0%, #eff6ff 100%);
}

.hero-copy,
.hero-meta,
.hero-actions,
.head-actions,
.editor-actions,
.ask-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.hero-copy {
  flex-direction: column;
}

.hero-card h2,
.panel-head h3 {
  margin: 0;
}

.eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(14, 165, 233, 0.12);
  color: #0369a1;
  font-size: 12px;
  font-weight: 700;
}

.hero-card p,
.hero-meta,
.panel-head span,
.answer-text,
.feedback-label,
.source-item span {
  margin: 0;
  color: var(--app-muted);
}

.panel-grid,
.form-grid {
  display: grid;
  gap: 20px;
}

.panel-grid {
  grid-template-columns: minmax(0, 1.25fr) minmax(360px, 0.9fr);
}

.panel-card {
  padding: 24px;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.form-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.editor-card :deep(.el-select),
.editor-card :deep(.el-input),
.ask-card :deep(.el-input) {
  width: 100%;
}

.ask-card,
.editor-card,
.answer-panel,
.feedback-box,
.source-item {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.source-list {
  display: grid;
  gap: 12px;
}

.source-item {
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.feedback-box {
  padding: 16px;
  border-radius: 18px;
  background: rgba(219, 234, 254, 0.24);
}

@media (max-width: 1200px) {
  .panel-grid,
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
