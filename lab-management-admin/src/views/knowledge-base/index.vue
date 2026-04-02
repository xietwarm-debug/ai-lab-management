<template>
  <div class="knowledge-page">
    <section class="hero-card">
      <div>
        <span class="hero-tag">AI 知识库管理</span>
        <h2>上传文件后，AI 助手即可直接检索回答</h2>
        <p>支持 PDF、DOCX、XLSX、CSV、TXT、MD。上传后会自动抽取正文、建立索引，并供 AI 助手与知识问答检索使用。</p>
      </div>
      <div class="hero-stats">
        <div class="stat-item"><strong>{{ rows.length }}</strong><span>文档总数</span></div>
        <div class="stat-item"><strong>{{ activeCount }}</strong><span>启用文档</span></div>
        <div class="stat-item"><strong>{{ fileDocCount }}</strong><span>文件型文档</span></div>
        <div v-if="!props.hideFeedbackSection" class="stat-item"><strong>{{ feedbackTotal }}</strong><span>反馈数量</span></div>
      </div>
    </section>

    <section class="panel-grid">
      <article class="panel-card">
        <div class="panel-head">
          <div>
            <h3>知识入库</h3>
            <p>文件上传适合设备说明书、制度 PDF、表格资料。文本录入适合 FAQ、流程说明和补充修订。</p>
          </div>
          <div class="head-actions">
            <el-button :loading="loading" @click="reloadAll">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button type="primary" @click="resetAllForms">
              <el-icon><Plus /></el-icon>
              新建
            </el-button>
          </div>
        </div>

        <el-tabs v-model="editorMode">
          <el-tab-pane label="文件上传" name="upload">
            <el-form label-position="top">
              <div class="form-grid">
                <el-form-item label="文档标题">
                  <el-input v-model="uploadForm.title" maxlength="200" placeholder="不填则默认使用文件名" />
                </el-form-item>
                <el-form-item label="文档分类">
                  <el-select v-model="uploadForm.category">
                    <el-option v-for="item in categoryOptions" :key="item.value" :label="item.label" :value="item.value" />
                  </el-select>
                </el-form-item>
                <el-form-item label="适用角色">
                  <el-select v-model="uploadForm.scopeRole">
                    <el-option v-for="item in scopeOptions" :key="item.value" :label="item.label" :value="item.value" />
                  </el-select>
                </el-form-item>
                <el-form-item label="状态">
                  <el-select v-model="uploadForm.status">
                    <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
                  </el-select>
                </el-form-item>
              </div>

              <el-upload
                ref="uploadRef"
                v-model:file-list="uploadFileList"
                drag
                action="#"
                :auto-upload="false"
                :limit="1"
                accept=".pdf,.docx,.xlsx,.csv,.txt,.md"
                :on-change="handleUploadChange"
                :on-remove="handleUploadRemove"
                :on-exceed="handleUploadExceed"
              >
                <el-icon class="upload-icon"><UploadFilled /></el-icon>
                <div class="el-upload__text">拖拽到这里，或 <em>点击选择文件</em></div>
                <template #tip>
                  <div class="upload-tip">上传后会自动提取正文并建立索引，AI 助手可直接使用。</div>
                </template>
              </el-upload>

              <div v-if="uploadState.file" class="selected-file">
                <div>
                  <div class="file-name">{{ uploadState.file.name }}</div>
                  <div class="file-meta">{{ sourceTypeLabelByName(uploadState.file.name) }} · {{ formatFileSize(uploadState.file.size || 0) }}</div>
                </div>
                <el-button link type="danger" @click="resetUploadForm">移除</el-button>
              </div>

              <div class="actions">
                <el-button @click="resetUploadForm">清空</el-button>
                <el-button type="primary" :loading="uploading" @click="submitUpload">上传并建立索引</el-button>
              </div>
            </el-form>
          </el-tab-pane>

          <el-tab-pane label="文本录入" name="text">
            <el-alert
              v-if="editingId && editingSourceType !== 'text'"
              type="info"
              :closable="false"
              show-icon
              title="当前文档来自上传文件，你正在编辑系统抽取后的文本内容。"
              class="mb-16"
            />
            <el-form label-position="top">
              <div class="form-grid">
                <el-form-item label="文档标题">
                  <el-input v-model="form.title" maxlength="200" placeholder="例如：惠普电脑使用说明" />
                </el-form-item>
                <el-form-item label="来源链接">
                  <el-input v-model="form.sourceUrl" maxlength="500" placeholder="可选：原文件地址或资料链接" />
                </el-form-item>
                <el-form-item label="文档分类">
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
              <el-form-item label="正文内容">
                <el-input v-model="form.content" type="textarea" :rows="14" maxlength="200000" show-word-limit placeholder="可直接录入制度、FAQ、说明书文本。" />
              </el-form-item>
              <div class="actions">
                <el-button v-if="editingId" @click="resetTextForm">取消编辑</el-button>
                <el-button @click="fillDemo">填入示例</el-button>
                <el-button type="primary" :loading="saving" @click="submitForm">{{ editingId ? '保存并重建索引' : '创建并建立索引' }}</el-button>
              </div>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </article>

      <article class="panel-card">
        <div class="panel-head">
          <div>
            <h3>知识问答自测</h3>
            <p>先验证上传资料是否能命中，再去 AI 助手做真实联动。</p>
          </div>
          <el-button link type="primary" @click="question = defaultQuestion">恢复示例</el-button>
        </div>
        <el-input v-model="question" maxlength="160" placeholder="例如：惠普电脑开机黑屏时先检查什么？" @keyup.enter="runKnowledgeAsk">
          <template #append>
            <el-button type="primary" :loading="asking" @click="runKnowledgeAsk">测试检索</el-button>
          </template>
        </el-input>
        <div class="quick-tags">
          <el-tag v-for="item in quickQuestions" :key="item" class="quick-tag" effect="plain" @click="question = item">{{ item }}</el-tag>
        </div>
        <el-button class="assistant-btn" plain @click="goAiAssistant">
          去 AI 助手联动验证
          <el-icon><ArrowRight /></el-icon>
        </el-button>

        <div class="answer-box" :class="{ active: answerText }">
          <template v-if="answerText">
            <div class="answer-text">{{ answerText }}</div>
            <div v-if="answerSources.length" class="source-list">
              <div v-for="(item, index) in answerSources" :key="`${item.documentId}-${item.chunkNo}-${index}`" class="source-item">
                <div class="source-title"><span>{{ index + 1 }}</span><strong>{{ item.title || '未命中文档标题' }}</strong></div>
                <p>{{ item.summary || item.content || '暂无摘要' }}</p>
              </div>
            </div>
            <div class="feedback-box">
              <div class="feedback-head">
                <span>这次回答是否有帮助？</span>
                <el-radio-group v-model="feedbackForm.helpful" size="small">
                  <el-radio-button :label="true">有帮助</el-radio-button>
                  <el-radio-button :label="false">没帮助</el-radio-button>
                </el-radio-group>
              </div>
              <el-input v-model="feedbackForm.comment" type="textarea" :rows="2" maxlength="255" placeholder="可选：补充反馈，帮助优化知识库质量" />
              <div class="actions">
                <el-button type="primary" size="small" :disabled="!queryLogId" :loading="feedbackSubmitting" @click="submitAskFeedback">提交反馈</el-button>
              </div>
            </div>
          </template>
          <el-empty v-else description="还没有检索结果，可以先上传说明书，再试一个设备故障问题。" :image-size="120" />
        </div>
      </article>
    </section>

    <section class="panel-card">
      <div class="panel-head">
        <div>
          <h3>当前知识文件与文档</h3>
          <p>可查看目前都有哪些文件、来源类型、索引分块与更新时间。</p>
        </div>
      </div>
      <div class="filters">
        <el-form inline>
          <el-form-item label="关键字">
            <el-input v-model="filters.keyword" clearable placeholder="标题 / 摘要 / 关键词" @keyup.enter="loadDocuments" />
          </el-form-item>
          <el-form-item label="分类">
            <el-select v-model="filters.category" clearable placeholder="全部分类">
              <el-option label="全部" value="" />
              <el-option v-for="item in categoryOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="来源">
            <el-select v-model="filters.sourceType" clearable placeholder="全部来源">
              <el-option label="全部" value="" />
              <el-option v-for="item in sourceTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="filters.status" clearable placeholder="全部状态">
              <el-option label="全部" value="" />
              <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button @click="resetDocFilters">清空</el-button>
            <el-button type="primary" :loading="loading" @click="loadDocuments">查询</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table v-loading="loading" :data="rows">
        <el-table-column prop="title" label="标题" min-width="220" />
        <el-table-column label="来源" width="110">
          <template #default="{ row }"><el-tag effect="plain">{{ sourceTypeLabel(row.sourceType) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="文件 / 链接" min-width="240">
          <template #default="{ row }">
            <div class="link-cell">
              <span class="file-name">{{ row.fileName || row.title }}</span>
              <el-button v-if="row.sourceUrl" link type="primary" @click="openSource(row)">打开原文件</el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="分类" width="120">
          <template #default="{ row }">{{ categoryLabel(row.category) }}</template>
        </el-table-column>
        <el-table-column label="角色" width="110">
          <template #default="{ row }">{{ scopeLabel(row.scopeRole) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }"><el-tag :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="分块" width="90" align="center">
          <template #default="{ row }"><el-badge :value="row.chunkCount || 0" /></template>
        </el-table-column>
        <el-table-column prop="summary" label="摘要" min-width="240" show-overflow-tooltip />
        <el-table-column label="更新时间" min-width="170">
          <template #default="{ row }">{{ row.updatedAt || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" @click="editRow(row)">编辑</el-button>
              <el-button link type="primary" :loading="busyId === row.id && busyAction === 'reindex'" @click="reindexRow(row)">重建索引</el-button>
              <el-button link :type="row.status === 'active' ? 'danger' : 'success'" :loading="busyId === row.id && busyAction === 'status'" @click="toggleStatus(row)">
                {{ row.status === 'active' ? '停用' : '启用' }}
              </el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty><el-empty description="暂无知识文档" :image-size="100" /></template>
      </el-table>
    </section>

    <section v-if="!props.hideFeedbackSection" class="panel-card">
      <div class="panel-head">
        <div>
          <h3>检索反馈</h3>
          <p>用于判断哪些资料已覆盖，哪些问题还需要继续补文档。</p>
        </div>
      </div>
      <div class="filters">
        <el-form inline>
          <el-form-item label="反馈结果">
            <el-select v-model="feedbackFilters.helpful" clearable placeholder="全部">
              <el-option label="全部" value="" />
              <el-option label="有帮助" value="1" />
              <el-option label="没帮助" value="0" />
            </el-select>
          </el-form-item>
          <el-form-item label="关键字">
            <el-input v-model="feedbackFilters.keyword" clearable placeholder="问题 / 回答 / 用户 / 反馈内容" @keyup.enter="loadFeedback" />
          </el-form-item>
          <el-form-item>
            <el-button @click="resetFeedbackFilters">清空</el-button>
            <el-button type="primary" :loading="feedbackLoading" @click="loadFeedback">查询</el-button>
          </el-form-item>
        </el-form>
      </div>
      <el-table v-loading="feedbackLoading" :data="feedbackRows">
        <el-table-column label="结果" width="110">
          <template #default="{ row }"><el-tag :type="row.helpful ? 'success' : 'danger'">{{ row.helpful ? '有帮助' : '没帮助' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="question" label="问题" min-width="220" show-overflow-tooltip />
        <el-table-column prop="answer" label="回答" min-width="280" show-overflow-tooltip />
        <el-table-column prop="comment" label="反馈说明" min-width="220" show-overflow-tooltip />
        <el-table-column label="用户" width="120">
          <template #default="{ row }">{{ row.username || '-' }}</template>
        </el-table-column>
        <el-table-column label="时间" min-width="160">
          <template #default="{ row }">{{ row.createdAt || row.askedAt || '-' }}</template>
        </el-table-column>
        <template #empty><el-empty description="暂无检索反馈" :image-size="100" /></template>
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowRight, Plus, Refresh, UploadFilled } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { askKnowledgeQuestion, createKnowledgeDocument, getKnowledgeDocumentDetail, getKnowledgeDocuments, getKnowledgeFeedbackList, reindexKnowledgeDocument, submitKnowledgeFeedback, updateKnowledgeDocument, updateKnowledgeDocumentStatus, uploadKnowledgeDocument } from '@/api/knowledge'

const props = defineProps({ hideFeedbackSection: { type: Boolean, default: false } })
const router = useRouter()
const uploadRef = ref(null)
const defaultQuestion = '惠普电脑开机黑屏时先检查什么？'
const categoryOptions = [{ label: '规则制度', value: 'rule' }, { label: '设备说明', value: 'manual' }, { label: '安全规范', value: 'safety' }, { label: '课程文档', value: 'course' }, { label: '报修知识', value: 'repair' }, { label: '常见问题', value: 'faq' }, { label: '其他', value: 'other' }]
const scopeOptions = [{ label: '全员可见', value: 'all' }, { label: '仅学生', value: 'student' }, { label: '仅教师', value: 'teacher' }, { label: '仅管理员', value: 'admin' }]
const statusOptions = [{ label: '草稿', value: 'draft' }, { label: '启用', value: 'active' }, { label: '停用', value: 'disabled' }]
const sourceTypeOptions = [{ label: '文本录入', value: 'text' }, { label: 'Markdown', value: 'markdown' }, { label: 'CSV', value: 'csv' }, { label: 'Word', value: 'word' }, { label: 'Excel', value: 'excel' }, { label: 'PDF', value: 'pdf' }]
const quickQuestions = ['实验室预约最早可以提前多久提交？', '惠普电脑开机黑屏时先检查什么？', '设备报修工单一般多久响应？']

const editorMode = ref('upload')
const loading = ref(false)
const feedbackLoading = ref(false)
const saving = ref(false)
const uploading = ref(false)
const asking = ref(false)
const feedbackSubmitting = ref(false)
const busyId = ref(0)
const busyAction = ref('')
const editingId = ref(0)
const editingSourceType = ref('text')
const rows = ref([])
const feedbackRows = ref([])
const feedbackTotal = ref(0)
const uploadFileList = ref([])
const filters = reactive({ keyword: '', category: '', sourceType: '', status: '' })
const feedbackFilters = reactive({ helpful: '', keyword: '' })
const uploadForm = reactive({ title: '', category: 'manual', scopeRole: 'all', status: 'active' })
const uploadState = reactive({ file: null })
const form = reactive({ title: '', category: 'rule', scopeRole: 'all', status: 'active', sourceUrl: '', content: '' })
const question = ref(defaultQuestion)
const answerText = ref('')
const answerSources = ref([])
const queryLogId = ref(0)
const feedbackForm = reactive({ helpful: true, comment: '' })

const activeCount = computed(() => rows.value.filter(item => item.status === 'active').length)
const fileDocCount = computed(() => rows.value.filter(item => item.sourceType && item.sourceType !== 'text').length)
const categoryLabel = value => categoryOptions.find(item => item.value === value)?.label || '其他'
const scopeLabel = value => scopeOptions.find(item => item.value === value)?.label || '全员可见'
const statusLabel = value => statusOptions.find(item => item.value === value)?.label || '草稿'
const statusTagType = value => value === 'active' ? 'success' : value === 'disabled' ? 'danger' : 'info'
const sourceTypeLabel = value => sourceTypeOptions.find(item => item.value === value)?.label || '文本录入'
function sourceTypeLabelByName(fileName) {
  const lower = String(fileName || '').toLowerCase()
  if (lower.endsWith('.pdf')) return 'PDF'
  if (lower.endsWith('.docx')) return 'Word'
  if (lower.endsWith('.xlsx')) return 'Excel'
  if (lower.endsWith('.csv')) return 'CSV'
  if (lower.endsWith('.md')) return 'Markdown'
  return '文本'
}
function formatFileSize(size) {
  const value = Number(size || 0)
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}
function resetUploadForm() {
  uploadForm.title = ''
  uploadForm.category = 'manual'
  uploadForm.scopeRole = 'all'
  uploadForm.status = 'active'
  uploadState.file = null
  uploadFileList.value = []
  uploadRef.value?.clearFiles?.()
}
function resetTextForm() {
  editingId.value = 0
  editingSourceType.value = 'text'
  form.title = ''
  form.category = 'rule'
  form.scopeRole = 'all'
  form.status = 'active'
  form.sourceUrl = ''
  form.content = ''
}
function resetAllForms() {
  resetUploadForm()
  resetTextForm()
  editorMode.value = 'upload'
}
function resetDocFilters() {
  filters.keyword = ''
  filters.category = ''
  filters.sourceType = ''
  filters.status = ''
  loadDocuments()
}
function resetFeedbackFilters() {
  feedbackFilters.helpful = ''
  feedbackFilters.keyword = ''
  loadFeedback()
}
function fillDemo() {
  form.title = '惠普台式机基础使用说明'
  form.category = 'manual'
  form.scopeRole = 'all'
  form.status = 'active'
  form.sourceUrl = ''
  form.content = ['一、开机前检查电源线、显示器电源线与视频线是否连接牢固。', '二、若出现黑屏，请先确认主机电源灯、显示器指示灯与键盘灯状态。', '三、若主机运行但显示器无信号，优先检查 HDMI 或 DP 连接线，必要时重新插拔。', '四、若连续两次重启后仍无法进入系统，请提交报修并记录设备编号。'].join('\n')
}
function handleUploadChange(uploadFile, fileList) {
  const latest = fileList[fileList.length - 1]
  uploadFileList.value = latest ? [latest] : []
  uploadState.file = latest?.raw || null
}
function handleUploadRemove() {
  uploadState.file = null
}
function handleUploadExceed(files) {
  const latest = files[files.length - 1]
  uploadRef.value?.clearFiles?.()
  uploadFileList.value = []
  uploadState.file = latest || null
  ElMessage.info('一次只能上传一个文件，已替换为最新选择的文件')
}
async function loadDocuments() {
  loading.value = true
  try {
    const response = await getKnowledgeDocuments({ keyword: filters.keyword || undefined, category: filters.category || undefined, sourceType: filters.sourceType || undefined, status: filters.status || undefined })
    rows.value = Array.isArray(response.data?.data) ? response.data.data : []
  } finally {
    loading.value = false
  }
}
async function loadFeedback() {
  feedbackLoading.value = true
  try {
    const response = await getKnowledgeFeedbackList({ helpful: feedbackFilters.helpful || undefined, keyword: feedbackFilters.keyword || undefined, page: 1, pageSize: 20 })
    feedbackRows.value = Array.isArray(response.data?.data) ? response.data.data : []
    feedbackTotal.value = Number(response.data?.meta?.total || feedbackRows.value.length || 0)
  } finally {
    feedbackLoading.value = false
  }
}
async function reloadAll() {
  await loadDocuments()
  if (!props.hideFeedbackSection) await loadFeedback()
}
async function submitUpload() {
  if (!uploadState.file) {
    ElMessage.warning('请先选择一个文件')
    return
  }
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', uploadState.file)
    formData.append('title', String(uploadForm.title || '').trim())
    formData.append('category', uploadForm.category)
    formData.append('scopeRole', uploadForm.scopeRole)
    formData.append('status', uploadForm.status)
    await uploadKnowledgeDocument(formData)
    ElMessage.success('文件已上传并建立知识索引')
    resetUploadForm()
    await loadDocuments()
  } finally {
    uploading.value = false
  }
}
async function editRow(row) {
  const response = await getKnowledgeDocumentDetail(row.id)
  const data = response.data?.data || {}
  editingId.value = Number(data.id || row.id || 0)
  editingSourceType.value = String(data.sourceType || 'text')
  form.title = String(data.title || '')
  form.category = String(data.category || 'rule')
  form.scopeRole = String(data.scopeRole || 'all')
  form.status = String(data.status || 'draft')
  form.sourceUrl = String(data.sourceUrl || '')
  form.content = String(data.content || '')
  editorMode.value = 'text'
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
async function submitForm() {
  if (!String(form.title || '').trim()) return ElMessage.warning('请填写标题')
  if (!String(form.content || '').trim()) return ElMessage.warning('请填写正文内容')
  saving.value = true
  try {
    const payload = { title: String(form.title || '').trim(), category: form.category, scopeRole: form.scopeRole, status: form.status, sourceUrl: String(form.sourceUrl || '').trim(), content: String(form.content || '').trim() }
    if (editingId.value) {
      await updateKnowledgeDocument(editingId.value, payload)
      ElMessage.success('知识文档已更新')
    } else {
      await createKnowledgeDocument(payload)
      ElMessage.success('知识文档已创建')
    }
    resetTextForm()
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
  if (!query) return ElMessage.warning('请输入问题')
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
      return ElMessage.info('当前知识库还没有命中这个问题')
    }
    ElMessage.success('已返回知识库检索结果')
  } finally {
    asking.value = false
  }
}
async function submitAskFeedback() {
  if (!queryLogId.value) return
  feedbackSubmitting.value = true
  try {
    await submitKnowledgeFeedback({ queryLogId: queryLogId.value, helpful: feedbackForm.helpful, comment: String(feedbackForm.comment || '').trim() })
    ElMessage.success('反馈已提交')
    if (!props.hideFeedbackSection) await loadFeedback()
  } finally {
    feedbackSubmitting.value = false
  }
}
function openSource(row) {
  if (row?.sourceUrl) window.open(row.sourceUrl, '_blank')
}
function goAiAssistant() {
  router.push({ path: '/ai-assistant', query: { tab: 'knowledge', question: question.value || defaultQuestion } })
}
onMounted(() => { reloadAll() })
</script>

<style scoped lang="scss">
.knowledge-page { display:flex; flex-direction:column; gap:24px; padding:24px; background:#f6f8fc; min-height:100vh; }
.hero-card,.panel-card { background:#fff; border-radius:24px; box-shadow:0 12px 34px rgba(15,23,42,.06); }
.hero-card { display:flex; justify-content:space-between; gap:24px; padding:32px; background:linear-gradient(135deg,#eef5ff 0%,#fff 60%); }
.hero-card h2,.panel-head h3 { margin:0 0 10px; color:#0f172a; }
.hero-card p,.panel-head p { margin:0; color:#64748b; line-height:1.7; }
.hero-tag { display:inline-flex; padding:6px 12px; border-radius:999px; background:#dbeafe; color:#2563eb; font-size:13px; font-weight:600; }
.hero-stats { display:flex; flex-wrap:wrap; gap:12px; }
.stat-item { min-width:112px; padding:14px 16px; border-radius:18px; background:rgba(255,255,255,.82); }
.stat-item strong { display:block; font-size:24px; color:#0f172a; }
.stat-item span { color:#64748b; font-size:13px; }
.panel-grid { display:grid; grid-template-columns:1.2fr 1fr; gap:24px; }
.panel-card { padding:28px; }
.panel-head,.feedback-head,.head-actions,.row-actions,.actions { display:flex; align-items:center; gap:12px; }
.panel-head { justify-content:space-between; margin-bottom:18px; align-items:flex-start; }
.head-actions,.actions { justify-content:flex-end; }
.form-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:0 18px; }
.upload-icon { font-size:30px; color:#3b82f6; }
.upload-tip,.file-meta { color:#64748b; font-size:13px; }
.selected-file,.answer-box,.feedback-box { margin-top:14px; padding:16px; border-radius:18px; }
.selected-file { display:flex; justify-content:space-between; align-items:center; border:1px solid #e2e8f0; background:#f8fafc; }
.file-name { color:#0f172a; font-weight:600; word-break:break-all; }
.mb-16,.filters,.quick-tags { margin-bottom:16px; }
.quick-tags { display:flex; flex-wrap:wrap; gap:10px; margin-top:16px; }
.quick-tag { cursor:pointer; }
.assistant-btn { margin-bottom:16px; }
.answer-box { min-height:360px; border:1px dashed #cbd5e1; background:#f8fafc; }
.answer-box.active { border-style:solid; border-color:#dbeafe; background:#fff; }
.answer-text { padding:16px; border-radius:16px; background:#eff6ff; color:#1e3a8a; line-height:1.8; }
.source-list { display:flex; flex-direction:column; gap:12px; margin-top:16px; }
.source-item { padding:14px 16px; border-radius:16px; background:#f8fafc; }
.source-title { display:flex; align-items:center; gap:10px; margin-bottom:8px; }
.source-title span { width:22px; height:22px; line-height:22px; text-align:center; border-radius:50%; background:#dbeafe; color:#2563eb; font-size:12px; font-weight:700; }
.source-item p,.link-cell { color:#475569; }
.feedback-head { justify-content:space-between; margin-bottom:12px; }
.filters { margin-bottom:18px; }
.link-cell { display:flex; flex-direction:column; gap:4px; }
@media (max-width: 1200px) { .panel-grid { grid-template-columns:1fr; } .hero-card { flex-direction:column; } }
@media (max-width: 768px) { .knowledge-page { padding:16px; } .hero-card,.panel-card { padding:20px; border-radius:20px; } .form-grid { grid-template-columns:1fr; } .panel-head,.feedback-head,.selected-file,.head-actions,.actions { flex-direction:column; align-items:stretch; } }
</style>
