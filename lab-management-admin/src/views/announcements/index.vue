<template>
  <div class="page-wrap">
    <section class="page-head">
      <div>
        <span class="eyebrow">消息编排</span>
        <h2>公告管理</h2>
        <p>统一管理公告发布、定时上线、置顶展示和 AI 草稿生成，方便后台快速完成通知编排与触达。</p>
      </div>
      <div class="head-actions">
        <el-button :loading="loading" @click="fetchRows">刷新</el-button>
        <el-button :loading="drafting" @click="generateDraft">AI 草稿</el-button>
        <el-button type="primary" @click="openCreateDialog">发布公告</el-button>
      </div>
    </section>

    <section class="page-card">
      <el-form inline>
        <el-form-item label="状态">
          <el-select v-model="filters.status" style="width: 160px">
            <el-option label="全部" value="all" />
            <el-option label="已发布" value="published" />
            <el-option label="定时中" value="scheduled" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="resetFilters">重置筛选</el-button>
          <el-button type="primary" :loading="loading" @click="handleSearch">查询公告</el-button>
        </el-form-item>
      </el-form>

      <div class="summary-row">
        <span class="summary-text">当前共 {{ rows.length }} 条公告，已发布 {{ publishedCount }} 条，待发布 {{ scheduledCount }} 条</span>
      </div>

      <el-table v-loading="loading" :data="rows">
        <el-table-column prop="title" label="标题" min-width="240" show-overflow-tooltip />
        <el-table-column prop="publisherName" label="发布人" width="120" />
        <el-table-column prop="publishAt" label="发布时间" width="180" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'scheduled' ? 'warning' : 'success'">
              {{ row.status === 'scheduled' ? '定时中' : '已发布' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="置顶" width="90">
          <template #default="{ row }">{{ row.isPinned ? '是' : '否' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openPreview(row)">预览</el-button>
            <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
            <el-button link @click="togglePin(row)">{{ row.isPinned ? '取消置顶' : '置顶' }}</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="当前筛选条件下暂无公告数据" />
        </template>
      </el-table>
    </section>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑公告' : '发布公告'" width="760px">
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input v-model="form.title" maxlength="120" show-word-limit />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="form.content" type="textarea" :rows="10" maxlength="5000" show-word-limit />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="发布时间">
              <el-date-picker
                v-model="form.publishAt"
                type="datetime"
                value-format="YYYY-MM-DD HH:mm:ss"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="置顶">
              <el-switch v-model="form.isPinned" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="previewVisible" title="公告预览" size="560px">
      <div v-if="preview" class="preview-card">
        <div class="preview-meta">
          <el-tag size="small" :type="preview.status === 'scheduled' ? 'warning' : 'success'">
            {{ preview.status === 'scheduled' ? '定时中' : '已发布' }}
          </el-tag>
          <el-tag size="small" type="info">{{ preview.isPinned ? '已置顶' : '未置顶' }}</el-tag>
        </div>
        <h3>{{ preview.title }}</h3>
        <p class="preview-sub">发布人：{{ preview.publisherName || '-' }}</p>
        <p class="preview-sub">发布时间：{{ preview.publishAt || '-' }}</p>
        <div class="preview-content">{{ preview.content || '-' }}</div>
      </div>
      <el-empty v-else description="暂无公告内容" />
    </el-drawer>
  </div>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createAnnouncement,
  createAnnouncementDraft,
  deleteAnnouncement,
  getAdminAnnouncements,
  pinAnnouncement,
  updateAnnouncement
} from '@/api/announcements'

function formatNow() {
  const now = new Date()
  const year = now.getFullYear()
  const month = `${now.getMonth() + 1}`.padStart(2, '0')
  const day = `${now.getDate()}`.padStart(2, '0')
  const hour = `${now.getHours()}`.padStart(2, '0')
  const minute = `${now.getMinutes()}`.padStart(2, '0')
  const second = `${now.getSeconds()}`.padStart(2, '0')
  return `${year}-${month}-${day} ${hour}:${minute}:${second}`
}

const loading = ref(false)
const saving = ref(false)
const drafting = ref(false)
const rows = ref([])
const dialogVisible = ref(false)
const previewVisible = ref(false)
const preview = ref(null)

const filters = reactive({
  status: 'all'
})

const publishedCount = computed(() => rows.value.filter((item) => item.status === 'published').length)
const scheduledCount = computed(() => rows.value.filter((item) => item.status === 'scheduled').length)

const form = reactive({
  id: 0,
  title: '',
  content: '',
  publishAt: '',
  isPinned: false
})

function resetForm() {
  form.id = 0
  form.title = ''
  form.content = ''
  form.publishAt = formatNow()
  form.isPinned = false
}

function validateForm() {
  if (!form.title.trim() || !form.content.trim()) {
    ElMessage.warning('请填写标题和内容')
    return false
  }
  if (!form.publishAt) {
    ElMessage.warning('请选择发布时间')
    return false
  }
  return true
}

function openCreateDialog() {
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(row) {
  form.id = Number(row.id || 0)
  form.title = row.title || ''
  form.content = row.content || ''
  form.publishAt = row.publishAt || formatNow()
  form.isPinned = Boolean(row.isPinned)
  dialogVisible.value = true
}

function openPreview(row) {
  preview.value = row
  previewVisible.value = true
}

function handleSearch() {
  fetchRows()
}

function resetFilters() {
  filters.status = 'all'
  fetchRows()
}

async function fetchRows() {
  loading.value = true
  try {
    const response = await getAdminAnnouncements({
      status: filters.status,
      limit: 100
    })
    rows.value = response.data?.data || []
  } finally {
    loading.value = false
  }
}

async function generateDraft() {
  drafting.value = true
  try {
    if (!dialogVisible.value) {
      resetForm()
    }
    const response = await createAnnouncementDraft({
      titleHint: form.title || '实验室管理通知',
      contentHint: form.content || '请根据实验室近期安排生成一则正式公告。',
      publishAt: form.publishAt,
      isPinned: form.isPinned
    })
    const draft = response.data?.data || {}
    form.title = draft.title || form.title
    form.content = draft.content || form.content
    form.publishAt = draft.publishAtSuggestion || form.publishAt
    form.isPinned = Boolean(draft.isPinnedSuggestion)
    dialogVisible.value = true
    ElMessage.success('AI 草稿已填入编辑框')
  } finally {
    drafting.value = false
  }
}

async function submitForm() {
  if (!validateForm()) return

  saving.value = true
  try {
    const payload = {
      title: form.title.trim(),
      content: form.content.trim(),
      publishAt: form.publishAt,
      isPinned: form.isPinned
    }

    if (form.id) {
      await updateAnnouncement(form.id, payload)
      ElMessage.success('公告已更新')
    } else {
      await createAnnouncement(payload)
      ElMessage.success('公告已发布')
    }
    dialogVisible.value = false
    fetchRows()
  } finally {
    saving.value = false
  }
}

async function togglePin(row) {
  await pinAnnouncement(row.id, {
    pinned: !row.isPinned
  })
  ElMessage.success(row.isPinned ? '已取消置顶' : '已置顶')
  fetchRows()
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除公告“${row.title}”吗？`, '删除公告', { type: 'warning' })
  await deleteAnnouncement(row.id)
  ElMessage.success('公告已删除')
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
.head-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
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
.summary-text,
.preview-sub {
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

.preview-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.preview-meta {
  display: flex;
  gap: 8px;
}

.preview-card h3 {
  margin: 0;
}

.preview-content {
  line-height: 1.8;
  white-space: pre-wrap;
  padding: 16px;
  border-radius: 16px;
  background: #f8fafc;
}
</style>
