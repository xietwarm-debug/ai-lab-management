<template>
  <div class="lostfound-page">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="eyebrow">失物招领后台</span>
        <h2>认领审核与状态流转</h2>
        <p>复用现有失物招领后端与移动端能力，在后台集中处理认领申请、结案流转和搜索筛选。</p>
        <div class="hero-meta">
          <span>当前结果 {{ rows.length }} 条</span>
          <span>待审核认领 {{ pendingClaimCount }} 条</span>
          <span>进行中 {{ openCount }} 条</span>
        </div>
      </div>
      <div class="hero-actions">
        <el-button :loading="loading" @click="fetchRows">刷新</el-button>
        <el-button type="primary" @click="resetFilters">重置筛选</el-button>
      </div>
    </section>

    <section class="metric-grid">
      <article class="metric-card">
        <span class="metric-label">待审核认领</span>
        <strong class="metric-value warning">{{ pendingClaimCount }}</strong>
        <span class="metric-sub">来自拾到物品的认领申请</span>
      </article>
      <article class="metric-card">
        <span class="metric-label">进行中</span>
        <strong class="metric-value">{{ openCount }}</strong>
        <span class="metric-sub">仍可继续认领或结案</span>
      </article>
      <article class="metric-card">
        <span class="metric-label">已解决</span>
        <strong class="metric-value success">{{ closedCount }}</strong>
        <span class="metric-sub">已完成结案或认领通过</span>
      </article>
      <article class="metric-card">
        <span class="metric-label">当前焦点</span>
        <strong class="metric-value">{{ focusId || '-' }}</strong>
        <span class="metric-sub">来自待办中心时会自动定位</span>
      </article>
    </section>

    <section class="panel-card filter-card">
      <div class="panel-head">
        <div>
          <h3>搜索与筛选</h3>
          <span>支持状态、类型、认领状态和关键词组合过滤</span>
        </div>
      </div>

      <el-form label-position="top">
        <div class="filter-grid">
          <el-form-item label="关键词">
            <el-input
              v-model="filters.keyword"
              placeholder="标题 / 描述 / 地点 / 发布人 / 认领信息"
              clearable
              @keyup.enter="applyFilters"
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="filters.status" clearable placeholder="全部状态">
              <el-option label="全部" value="" />
              <el-option label="进行中" value="open" />
              <el-option label="已解决" value="closed" />
            </el-select>
          </el-form-item>
          <el-form-item label="类型">
            <el-select v-model="filters.type" clearable placeholder="全部类型">
              <el-option label="全部" value="" />
              <el-option label="失物" value="lost" />
              <el-option label="拾到" value="found" />
            </el-select>
          </el-form-item>
          <el-form-item label="认领状态">
            <el-select v-model="filters.claimApplyStatus" clearable placeholder="全部认领状态">
              <el-option label="全部" value="" />
              <el-option label="待审核" value="pending" />
              <el-option label="已通过" value="approved" />
              <el-option label="已驳回" value="rejected" />
              <el-option label="无认领申请" value="none" />
            </el-select>
          </el-form-item>
          <el-form-item label="学号">
            <el-input v-model="filters.studentId" clearable placeholder="结案学号" @keyup.enter="applyFilters" />
          </el-form-item>
          <el-form-item label="姓名">
            <el-input v-model="filters.studentName" clearable placeholder="结案姓名" @keyup.enter="applyFilters" />
          </el-form-item>
          <el-form-item label="班级">
            <el-input v-model="filters.studentClass" clearable placeholder="结案班级" @keyup.enter="applyFilters" />
          </el-form-item>
        </div>

        <div class="filter-actions">
          <el-button @click="resetFilters">清空</el-button>
          <el-button type="primary" :loading="loading" @click="applyFilters">搜索</el-button>
        </div>
      </el-form>
    </section>

    <section v-if="loading" class="panel-card">
      <el-skeleton :rows="6" animated />
    </section>

    <section v-else class="list-grid">
      <article
        v-for="item in rows"
        :id="`lostfound-item-${item.id}`"
        :key="item.id"
        class="item-card"
        :class="{ 'item-card--focus': item.id === focusId }"
      >
        <div class="item-head">
          <div>
            <div class="item-title-row">
              <h3>{{ item.title || '-' }}</h3>
              <el-tag size="small" :type="item.type === 'found' ? 'success' : 'warning'">
                {{ item.type === 'found' ? '拾到' : '失物' }}
              </el-tag>
            </div>
            <p class="item-meta">发布者 {{ item.owner || '-' }} · {{ item.createdAt || '-' }}</p>
          </div>
          <el-tag size="small" :type="item.status === 'closed' ? 'success' : 'warning'">
            {{ item.status === 'closed' ? '已解决' : '进行中' }}
          </el-tag>
        </div>

        <div class="item-body">
          <div class="item-copy">
            <p><strong>地点：</strong>{{ item.location || '-' }}</p>
            <p><strong>联系方式：</strong>{{ item.contact || '-' }}</p>
            <p v-if="item.description"><strong>描述：</strong>{{ item.description }}</p>
            <p v-if="item.status === 'closed' && (item.claimStudentId || item.claimName || item.claimClass)">
              <strong>结案信息：</strong>{{ item.claimStudentId || '-' }} / {{ item.claimName || '-' }} / {{ item.claimClass || '-' }}
            </p>
          </div>
          <div v-if="item.imageUrl" class="thumb-wrap">
            <img :src="resolveImage(item.imageUrl)" :alt="item.title || 'lostfound'" class="thumb-image">
          </div>
        </div>

        <div v-if="item.type === 'found' && item.claimApplyStatus" class="claim-panel">
          <div class="claim-head">
            <strong>认领申请</strong>
            <el-tag size="small" :type="claimTagType(item.claimApplyStatus)">
              {{ claimStatusLabel(item.claimApplyStatus) }}
            </el-tag>
          </div>
          <p>申请人账号：{{ item.claimApplyUser || '-' }}</p>
          <p>申请信息：{{ item.claimApplyStudentId || '-' }} / {{ item.claimApplyName || '-' }} / {{ item.claimApplyClass || '-' }}</p>
          <p v-if="item.claimApplyReason">申请说明：{{ item.claimApplyReason }}</p>
          <p v-if="item.claimReviewedBy">审核人：{{ item.claimReviewedBy }} · {{ item.claimReviewedAt || '-' }}</p>
          <p v-if="item.claimReviewNote">审核备注：{{ item.claimReviewNote }}</p>
        </div>

        <div class="action-row">
          <el-button
            v-if="item.type === 'found' && item.claimApplyStatus === 'pending'"
            type="primary"
            @click="approveClaim(item)"
          >
            通过认领
          </el-button>
          <el-button
            v-if="item.type === 'found' && item.claimApplyStatus === 'pending'"
            @click="rejectClaim(item)"
          >
            驳回认领
          </el-button>
          <el-button
            v-if="item.status === 'open' && !(item.type === 'found' && item.claimApplyStatus === 'pending')"
            @click="closeItem(item)"
          >
            标记已解决
          </el-button>
          <el-button
            v-if="item.status === 'closed'"
            @click="reopenItem(item)"
          >
            重新打开
          </el-button>
          <el-popconfirm title="删除后不可恢复，确定继续吗？" @confirm="removeItem(item)">
            <template #reference>
              <el-button type="danger" plain>删除记录</el-button>
            </template>
          </el-popconfirm>
        </div>
      </article>

      <section v-if="rows.length === 0" class="panel-card empty-card">
        <el-empty description="当前筛选条件下暂无失物招领记录" />
      </section>
    </section>
  </div>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { buildApiUrl } from '@/utils/request'
import {
  deleteLostFoundItem,
  getLostFoundList,
  reviewLostFoundClaim,
  updateLostFoundStatus
} from '@/api/lostfound'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const rows = ref([])
const focusId = ref(0)
const filters = reactive({
  keyword: '',
  status: '',
  type: '',
  claimApplyStatus: '',
  studentId: '',
  studentName: '',
  studentClass: ''
})

const pendingClaimCount = computed(() => rows.value.filter((item) => item.claimApplyStatus === 'pending').length)
const openCount = computed(() => rows.value.filter((item) => item.status === 'open').length)
const closedCount = computed(() => rows.value.filter((item) => item.status === 'closed').length)

function toInt(value, fallback = 0) {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? Math.round(numeric) : fallback
}

function claimStatusLabel(status) {
  if (status === 'pending') return '待审核'
  if (status === 'approved') return '已通过'
  if (status === 'rejected') return '已驳回'
  return '未知'
}

function claimTagType(status) {
  if (status === 'pending') return 'warning'
  if (status === 'approved') return 'success'
  if (status === 'rejected') return 'danger'
  return 'info'
}

function resolveImage(url) {
  const raw = String(url || '').trim()
  if (!raw) return ''
  return /^https?:\/\//i.test(raw) ? raw : buildApiUrl(raw)
}

function syncFiltersFromRoute() {
  filters.keyword = String(route.query.keyword || '').trim()
  filters.status = String(route.query.status || '').trim()
  filters.type = String(route.query.type || '').trim()
  filters.claimApplyStatus = String(route.query.claimApplyStatus || '').trim()
  filters.studentId = String(route.query.studentId || '').trim()
  filters.studentName = String(route.query.studentName || '').trim()
  filters.studentClass = String(route.query.studentClass || '').trim()
  focusId.value = toInt(route.query.focusId, 0)
}

function buildQuery() {
  return {
    keyword: filters.keyword || undefined,
    status: filters.status || undefined,
    type: filters.type || undefined,
    claimApplyStatus: filters.claimApplyStatus || undefined,
    studentId: filters.studentId || undefined,
    studentName: filters.studentName || undefined,
    studentClass: filters.studentClass || undefined,
    focusId: focusId.value || undefined
  }
}

async function fetchRows() {
  loading.value = true
  try {
    const response = await getLostFoundList(buildQuery())
    rows.value = Array.isArray(response.data) ? response.data : []
    await nextTick()
    scrollToFocusedItem()
  } finally {
    loading.value = false
  }
}

function scrollToFocusedItem() {
  if (!focusId.value) return
  const element = document.getElementById(`lostfound-item-${focusId.value}`)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

async function applyFilters() {
  await router.replace({
    path: route.path,
    query: buildQuery()
  })
  await fetchRows()
}

async function resetFilters() {
  filters.keyword = ''
  filters.status = ''
  filters.type = ''
  filters.claimApplyStatus = ''
  filters.studentId = ''
  filters.studentName = ''
  filters.studentClass = ''
  focusId.value = 0
  await router.replace({ path: route.path, query: {} })
  await fetchRows()
}

async function approveClaim(item) {
  try {
    const { value } = await ElMessageBox.prompt(`确认通过“${item.title || '-'}”的认领申请？`, '通过认领', {
      inputPlaceholder: '可选：审核备注',
      confirmButtonText: '通过',
      cancelButtonText: '取消'
    })
    await reviewLostFoundClaim(item.id, {
      action: 'approve',
      note: String(value || '').trim()
    })
    ElMessage.success('认领已通过')
    await fetchRows()
  } catch (error) {
    // cancelled
  }
}

async function rejectClaim(item) {
  try {
    const { value } = await ElMessageBox.prompt(`请填写“${item.title || '-'}”的驳回原因`, '驳回认领', {
      inputPlaceholder: '驳回原因',
      confirmButtonText: '驳回',
      cancelButtonText: '取消',
      inputValidator: (value) => (String(value || '').trim() ? true : '请填写驳回原因')
    })
    await reviewLostFoundClaim(item.id, {
      action: 'reject',
      note: String(value || '').trim()
    })
    ElMessage.success('认领已驳回')
    await fetchRows()
  } catch (error) {
    // cancelled
  }
}

async function closeItem(item) {
  try {
    const { value } = await ElMessageBox.prompt('请按“学号,姓名,班级”填写结案信息', `标记“${item.title || '-'}”已解决`, {
      inputPlaceholder: '例如：20230001,张三,计科 1 班',
      confirmButtonText: '确认结案',
      cancelButtonText: '取消',
      inputValidator: (value) => {
        const parts = String(value || '').split(',').map((part) => part.trim()).filter(Boolean)
        return parts.length >= 3 ? true : '请填写完整的学号、姓名、班级'
      }
    })
    const [claimStudentId, claimName, claimClass] = String(value || '').split(',').map((part) => part.trim()).filter(Boolean)
    await updateLostFoundStatus(item.id, {
      status: 'closed',
      claimStudentId,
      claimName,
      claimClass
    })
    ElMessage.success('记录已标记为已解决')
    await fetchRows()
  } catch (error) {
    // cancelled
  }
}

async function reopenItem(item) {
  try {
    await ElMessageBox.confirm(`确认重新打开“${item.title || '-'}”吗？这会清空原结案和认领结果。`, '重新打开', {
      type: 'warning'
    })
    await updateLostFoundStatus(item.id, {
      status: 'open'
    })
    ElMessage.success('记录已重新打开')
    await fetchRows()
  } catch (error) {
    // cancelled
  }
}

async function removeItem(item) {
  await deleteLostFoundItem(item.id)
  ElMessage.success('记录已删除')
  await fetchRows()
}

watch(
  () => route.query,
  () => {
    syncFiltersFromRoute()
  },
  { deep: true, immediate: true }
)

onMounted(() => {
  fetchRows()
})
</script>

<style scoped lang="scss">
.lostfound-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-card,
.metric-card,
.panel-card,
.item-card {
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
    radial-gradient(circle at top right, rgba(249, 115, 22, 0.12), transparent 34%),
    linear-gradient(135deg, #fffdf9 0%, #fff7ed 100%);
}

.hero-copy,
.hero-meta,
.hero-actions,
.filter-actions,
.action-row,
.item-title-row,
.claim-head {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.hero-copy {
  flex-direction: column;
}

.hero-card h2,
.panel-head h3,
.item-card h3 {
  margin: 0;
}

.eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(249, 115, 22, 0.12);
  color: #c2410c;
  font-size: 12px;
  font-weight: 700;
}

.hero-card p,
.hero-meta,
.metric-sub,
.metric-label,
.panel-head span,
.item-meta,
.item-copy p,
.claim-panel p {
  margin: 0;
  color: var(--app-muted);
}

.metric-grid,
.filter-grid,
.list-grid {
  display: grid;
  gap: 20px;
}

.metric-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.metric-card {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-value {
  font-size: 32px;
}

.metric-value.warning {
  color: #d97706;
}

.metric-value.success {
  color: #16a34a;
}

.panel-card,
.item-card {
  padding: 24px;
}

.panel-head,
.item-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.filter-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.filter-card :deep(.el-select),
.filter-card :deep(.el-input) {
  width: 100%;
}

.filter-actions {
  justify-content: flex-end;
}

.list-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.item-card {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.item-card--focus {
  border-color: rgba(59, 130, 246, 0.5);
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.12);
}

.item-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 180px;
  gap: 16px;
}

.item-copy {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.thumb-wrap {
  overflow: hidden;
  border-radius: 18px;
  min-height: 140px;
  background: #f8fafc;
}

.thumb-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.claim-panel {
  padding: 16px;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.24);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.empty-card {
  grid-column: 1 / -1;
}

@media (max-width: 1200px) {
  .metric-grid,
  .filter-grid,
  .list-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .hero-card,
  .item-head,
  .item-body {
    grid-template-columns: 1fr;
    flex-direction: column;
  }

  .metric-grid,
  .filter-grid,
  .list-grid {
    grid-template-columns: 1fr;
  }

  .item-body {
    display: flex;
  }
}
</style>
