<template>
  <div class="page-container lostfound-page">
    <!-- 顶部 Hero 区 (带入场动画，专属暖橘/琥珀色调) -->
    <section class="hero-card overview-section is-warning-theme">
      <div class="hero-content">
        <div class="hero-copy">
          <span class="eyebrow">失物招领后台</span>
          <h1 class="page-title">认领审核与状态流转</h1>
          <p class="page-desc">集中处理失物登记、认领审核、状态流转和搜索筛选，让后台能够快速完成认领闭环。</p>
          <div class="hero-meta">
            <span class="meta-item"><el-icon><Document /></el-icon> 当前结果 {{ rows.length }} 条</span>
            <span class="meta-item text-warning"><el-icon><WarningFilled /></el-icon> 待审核认领 {{ pendingClaimCount }} 条</span>
            <span class="meta-item text-primary"><el-icon><Compass /></el-icon> 进行中 {{ openCount }} 条</span>
          </div>
        </div>
        <div class="hero-actions">
          <el-button @click="resetFilters" class="hover-lift">重置筛选</el-button>
          <el-button type="warning" plain :loading="loading" @click="fetchRows" :icon="RefreshRight" class="hover-lift">
            刷新数据
          </el-button>
        </div>
      </div>
      <div class="hero-decoration"></div>
    </section>

    <!-- 数据指标区 (交错入场动画) -->
    <section class="stats-grid metric-grid">
      <article class="stat-card is-warning" :class="{ 'has-unread': pendingClaimCount > 0 }">
        <div class="stat-info">
          <span class="stat-label">待审核认领</span>
          <span v-if="pendingClaimCount > 0" class="unread-badge">急需处理</span>
        </div>
        <strong class="stat-value text-warning">{{ pendingClaimCount }}</strong>
        <span class="stat-sub">来自拾到物品的认领申请</span>
      </article>
      <article class="stat-card is-primary">
        <div class="stat-info">
          <span class="stat-label">进行中</span>
        </div>
        <strong class="stat-value text-primary">{{ openCount }}</strong>
        <span class="stat-sub">仍可继续认领或结案</span>
      </article>
      <article class="stat-card is-success">
        <div class="stat-info">
          <span class="stat-label">已解决</span>
        </div>
        <strong class="stat-value text-success">{{ closedCount }}</strong>
        <span class="stat-sub">已完成结案或认领通过</span>
      </article>
      <article class="stat-card is-info">
        <div class="stat-info">
          <span class="stat-label">当前焦点</span>
        </div>
        <strong class="stat-value">{{ focusId || '-' }}</strong>
        <span class="stat-sub">来自待办中心时会自动定位</span>
      </article>
    </section>

    <!-- 搜索与筛选区 -->
    <section class="panel-card filter-card panel-fade-in">
      <div class="panel-head border-bottom">
        <div class="head-left">
          <el-icon class="head-icon text-primary"><Filter /></el-icon>
          <div>
            <h3>搜索与筛选</h3>
            <span class="sub-text">支持状态、类型、认领状态和关键词组合过滤</span>
          </div>
        </div>
      </div>

      <el-form label-position="top" class="custom-form mt-4">
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="关键词">
              <el-input
                v-model="filters.keyword"
                placeholder="标题 / 描述 / 地点 / 发布人"
                clearable
                :prefix-icon="Search"
                @keyup.enter="applyFilters"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="状态">
              <el-select v-model="filters.status" clearable placeholder="全部状态">
                <el-option label="全部" value="" />
                <el-option label="进行中" value="open" />
                <el-option label="已解决" value="closed" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="类型">
              <el-select v-model="filters.type" clearable placeholder="全部类型">
                <el-option label="全部" value="" />
                <el-option label="失物" value="lost" />
                <el-option label="拾到" value="found" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="认领状态">
              <el-select v-model="filters.claimApplyStatus" clearable placeholder="全部认领状态">
                <el-option label="全部" value="" />
                <el-option label="待审核" value="pending" />
                <el-option label="已通过" value="approved" />
                <el-option label="已驳回" value="rejected" />
                <el-option label="无申请" value="none" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="8">
            <el-form-item label="结案学号">
              <el-input v-model="filters.studentId" clearable placeholder="精确匹配结案学号" @keyup.enter="applyFilters" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="8">
            <el-form-item label="结案姓名">
              <el-input v-model="filters.studentName" clearable placeholder="匹配结案姓名" @keyup.enter="applyFilters" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="8">
            <el-form-item label="结案班级">
              <el-input v-model="filters.studentClass" clearable placeholder="匹配结案班级" @keyup.enter="applyFilters" />
            </el-form-item>
          </el-col>
        </el-row>
        <div class="action-row">
          <el-button @click="resetFilters">清空条件</el-button>
          <el-button type="primary" :loading="loading" @click="applyFilters" class="hover-lift" :icon="Search">执行搜索</el-button>
        </div>
      </el-form>
    </section>

    <!-- 加载骨架屏 -->
    <section v-if="loading" class="panel-card panel-fade-in">
      <el-skeleton :rows="6" animated />
    </section>

    <!-- 列表展示区 -->
    <template v-else>
      <transition-group name="list" tag="section" class="list-grid" v-if="rows.length > 0">
        <article
          v-for="item in rows"
          :id="`lostfound-item-${item.id}`"
          :key="item.id"
          class="item-card message-card"
          :class="{ 'is-focused': item.id === focusId, 'is-closed': item.status === 'closed' }"
        >
          <div class="item-head">
            <div class="head-content">
              <div class="item-title-row">
                <el-tag size="small" effect="light" class="custom-tag" :type="item.type === 'found' ? 'success' : 'warning'">
                  {{ item.type === 'found' ? '拾到' : '失物' }}
                </el-tag>
                <h3 class="msg-title">{{ item.title || '-' }}</h3>
              </div>
              <p class="msg-desc mt-1">发布者: {{ item.owner || '-' }} · {{ item.createdAt || '-' }}</p>
            </div>
            <el-tag size="small" effect="light" class="custom-tag" :type="item.status === 'closed' ? 'info' : 'primary'">
              {{ item.status === 'closed' ? '已解决' : '进行中' }}
            </el-tag>
          </div>

          <div class="item-body">
            <div class="item-copy">
              <div class="info-row"><el-icon><Location /></el-icon> <span><strong>地点：</strong>{{ item.location || '-' }}</span></div>
              <div class="info-row"><el-icon><Phone /></el-icon> <span><strong>联系：</strong>{{ item.contact || '-' }}</span></div>
              <p v-if="item.description" class="detail-text mt-2">{{ item.description }}</p>
              
              <div v-if="item.status === 'closed' && (item.claimStudentId || item.claimName || item.claimClass)" class="closed-info mt-2">
                <strong><el-icon><CircleCheck /></el-icon> 结案信息：</strong>
                {{ item.claimStudentId || '-' }} / {{ item.claimName || '-' }} / {{ item.claimClass || '-' }}
              </div>
            </div>
            
            <div v-if="item.imageUrl" class="thumb-wrap">
              <el-image 
                :src="resolveImage(item.imageUrl)" 
                :preview-src-list="[resolveImage(item.imageUrl)]"
                fit="cover" 
                class="thumb-image"
                hide-on-click-modal
              />
            </div>
          </div>

          <!-- 认领审核面板 -->
          <div v-if="item.type === 'found' && item.claimApplyStatus" class="claim-panel" :class="`is-${item.claimApplyStatus}`">
            <div class="claim-head">
              <strong><el-icon><User /></el-icon> 认领申请</strong>
              <el-tag size="small" effect="light" class="custom-tag" :type="claimTagType(item.claimApplyStatus)">
                {{ claimStatusLabel(item.claimApplyStatus) }}
              </el-tag>
            </div>
            <div class="claim-details">
              <p><span>申请账号：</span>{{ item.claimApplyUser || '-' }}</p>
              <p><span>申请信息：</span>{{ item.claimApplyStudentId || '-' }} / {{ item.claimApplyName || '-' }} / {{ item.claimApplyClass || '-' }}</p>
              <p v-if="item.claimApplyReason" class="reason-text"><span>说明：</span>{{ item.claimApplyReason }}</p>
              
              <div v-if="item.claimReviewedBy" class="review-info mt-2">
                <p>审核人：{{ item.claimReviewedBy }} · {{ item.claimReviewedAt || '-' }}</p>
                <p v-if="item.claimReviewNote">备注：{{ item.claimReviewNote }}</p>
              </div>
            </div>
          </div>

          <!-- 操作行 -->
          <div class="item-actions action-row">
            <template v-if="item.type === 'found' && item.claimApplyStatus === 'pending'">
              <el-button type="success" plain size="small" @click="approveClaim(item)" class="hover-lift">通过认领</el-button>
              <el-button type="danger" plain size="small" @click="rejectClaim(item)" class="hover-lift">驳回认领</el-button>
            </template>
            
            <el-button
              v-if="item.status === 'open' && !(item.type === 'found' && item.claimApplyStatus === 'pending')"
              size="small" type="primary" plain class="hover-lift"
              @click="closeItem(item)"
            >
              标记已解决
            </el-button>
            
            <el-button v-if="item.status === 'closed'" size="small" @click="reopenItem(item)" class="hover-lift">
              重新打开
            </el-button>
            
            <el-popconfirm title="删除后不可恢复，确定继续吗？" @confirm="removeItem(item)">
              <template #reference>
                <el-button type="danger" link size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </div>
        </article>
      </transition-group>

      <section v-if="rows.length === 0" class="panel-card empty-card panel-fade-in">
        <el-empty description="当前筛选条件下暂无失物招领记录" :image-size="120" />
      </section>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { Document, WarningFilled, Compass, RefreshRight, Filter, Search, Location, Phone, CircleCheck, User } from '@element-plus/icons-vue'

// 假设的 API
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
  keyword: '', status: '', type: '', claimApplyStatus: '', studentId: '', studentName: '', studentClass: ''
})

const pendingClaimCount = computed(() => rows.value.filter((item) => item.claimApplyStatus === 'pending').length)
const openCount = computed(() => rows.value.filter((item) => item.status === 'open').length)
const closedCount = computed(() => rows.value.filter((item) => item.status === 'closed').length)

// --- 业务与工具函数保持原样 ---
function toInt(value, fallback = 0) {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? Math.round(numeric) : fallback
}

function claimStatusLabel(status) {
  if (status === 'pending') return '待审核'
  if (status === 'approved') return '已通过'
  if (status === 'rejected') return '已驳回'
  return '无'
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
    keyword: filters.keyword || undefined, status: filters.status || undefined, type: filters.type || undefined,
    claimApplyStatus: filters.claimApplyStatus || undefined, studentId: filters.studentId || undefined,
    studentName: filters.studentName || undefined, studentClass: filters.studentClass || undefined,
    focusId: focusId.value || undefined
  }
}

async function fetchRows() {
  loading.value = true
  try {
    const response = await getLostFoundList(buildQuery()).catch(() => ({ data: [] })) // Fallback mock
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
  if (element) { element.scrollIntoView({ behavior: 'smooth', block: 'center' }) }
}

async function applyFilters() {
  await router.replace({ path: route.path, query: buildQuery() })
  await fetchRows()
}

async function resetFilters() {
  Object.keys(filters).forEach(k => filters[k] = '')
  focusId.value = 0
  await router.replace({ path: route.path, query: {} })
  await fetchRows()
}

async function approveClaim(item) {
  try {
    const { value } = await ElMessageBox.prompt(`确认通过“${item.title || '-'}”的认领申请？`, '通过认领', {
      inputPlaceholder: '可选：审核备注', confirmButtonText: '通过', cancelButtonText: '取消'
    })
    await reviewLostFoundClaim(item.id, { action: 'approve', note: String(value || '').trim() })
    ElMessage.success('认领已通过')
    await fetchRows()
  } catch (error) { /* cancelled */ }
}

async function rejectClaim(item) {
  try {
    const { value } = await ElMessageBox.prompt(`请填写“${item.title || '-'}”的驳回原因`, '驳回认领', {
      inputPlaceholder: '驳回原因', confirmButtonText: '驳回', cancelButtonText: '取消',
      inputValidator: (val) => (String(val || '').trim() ? true : '请填写驳回原因')
    })
    await reviewLostFoundClaim(item.id, { action: 'reject', note: String(value || '').trim() })
    ElMessage.success('认领已驳回')
    await fetchRows()
  } catch (error) { /* cancelled */ }
}

async function closeItem(item) {
  try {
    const { value } = await ElMessageBox.prompt('请按“学号,姓名,班级”填写结案信息', `标记“${item.title || '-'}”已解决`, {
      inputPlaceholder: '例如：20230001,张三,计科 1 班', confirmButtonText: '确认结案', cancelButtonText: '取消',
      inputValidator: (val) => {
        const parts = String(val || '').split(',').map((p) => p.trim()).filter(Boolean)
        return parts.length >= 3 ? true : '请填写完整的学号、姓名、班级'
      }
    })
    const [claimStudentId, claimName, claimClass] = String(value || '').split(',').map((p) => p.trim()).filter(Boolean)
    await updateLostFoundStatus(item.id, { status: 'closed', claimStudentId, claimName, claimClass })
    ElMessage.success('记录已标记为已解决')
    await fetchRows()
  } catch (error) { /* cancelled */ }
}

async function reopenItem(item) {
  try {
    await ElMessageBox.confirm(`确认重新打开“${item.title || '-'}”吗？这会清空原结案和认领结果。`, '重新打开', { type: 'warning' })
    await updateLostFoundStatus(item.id, { status: 'open' })
    ElMessage.success('记录已重新打开')
    await fetchRows()
  } catch (error) { /* cancelled */ }
}

async function removeItem(item) {
  try {
    await deleteLostFoundItem(item.id)
    ElMessage.success('记录已删除')
    await fetchRows()
  } catch (error) { /* handled by global interceptor */ }
}

watch(() => route.query, () => { syncFiltersFromRoute() }, { deep: true, immediate: true })

onMounted(() => { fetchRows() })
</script>

<style scoped lang="scss">
// 设计系统核心变量
$bg-color: #f8fafc;
$card-bg: #ffffff;
$text-main: #0f172a;
$text-regular: #475569;
$text-light: #94a3b8;
$border-color: #e2e8f0;
$primary: #3b82f6;
$danger: #ef4444;
$warning: #f59e0b;
$warning-light: #fffbeb;
$success: #10b981;
$info: #64748b;
$radius-lg: 16px;
$radius-md: 12px;
$shadow-soft: 0 10px 30px rgba(0, 0, 0, 0.03);
$shadow-hover: 0 15px 35px rgba(59, 130, 246, 0.06);

// --- 入场动画 Keyframes ---
@keyframes fadeSlideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes pulseBorder {
  0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4); border-color: $primary; }
  70% { box-shadow: 0 0 0 10px rgba(59, 130, 246, 0); border-color: rgba(59, 130, 246, 0.3); }
  100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); border-color: $border-color; }
}

.page-container {
  padding: 32px; background-color: $bg-color; min-height: 100vh;
  box-sizing: border-box; display: flex; flex-direction: column; gap: 24px;
}

// 文本与工具类
.text-warning { color: $warning !important; }
.text-primary { color: $primary !important; }
.text-success { color: $success !important; }
.mt-1 { margin-top: 4px; }
.mt-2 { margin-top: 8px; }
.mt-4 { margin-top: 16px; }
.hover-lift { transition: transform 0.2s ease; &:hover { transform: translateY(-1px); } }
.panel-fade-in {
  animation: fadeSlideUp 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both;
  &:nth-child(n+1) { animation-delay: 0.1s; }
  &:nth-child(n+2) { animation-delay: 0.15s; }
}

/* --- 面板基础 --- */
.panel-card {
  background: $card-bg; border-radius: $radius-lg; padding: 24px;
  box-shadow: $shadow-soft; border: 1px solid transparent; transition: all 0.3s;
}

/* --- Hero 区域 (失物招领专属琥珀/暖橘色主题) --- */
.hero-card {
  position: relative; display: flex; justify-content: space-between; align-items: flex-end;
  padding: 32px; border-radius: $radius-lg; box-shadow: $shadow-soft; overflow: hidden;
  animation: fadeSlideUp 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both;

  &.is-warning-theme {
    background: radial-gradient(circle at top right, rgba(245, 158, 11, 0.1), transparent 60%),
                linear-gradient(135deg, #ffffff 0%, #fffbf2 100%);
    border: 1px solid rgba(245, 158, 11, 0.15);
  }

  .hero-decoration {
    position: absolute; right: 0; top: 0; width: 300px; height: 100%; pointer-events: none;
    background-image: radial-gradient(#f59e0b 1px, transparent 1px); background-size: 20px 20px;
    opacity: 0.08; mask-image: linear-gradient(to left, white, transparent);
  }

  .hero-content {
    position: relative; z-index: 1; display: flex; justify-content: space-between;
    align-items: flex-end; width: 100%; flex-wrap: wrap; gap: 24px;
  }

  .eyebrow {
    display: inline-flex; width: fit-content; padding: 6px 12px; border-radius: 999px;
    background: rgba(245, 158, 11, 0.15); color: #d97706; font-size: 13px; font-weight: 700;
    margin-bottom: 12px; letter-spacing: 0.05em;
  }

  .page-title { font-size: 28px; font-weight: 700; color: $text-main; margin: 0 0 12px 0; }
  .page-desc { color: $text-regular; font-size: 14px; margin: 0 0 16px 0; max-width: 600px; line-height: 1.6; }
  
  .hero-meta {
    display: flex; gap: 16px; color: $text-light; font-size: 13px; font-weight: 500;
    .meta-item { display: flex; align-items: center; gap: 4px; }
  }
}

/* --- 指标卡片 --- */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }

.stat-card {
  background: $card-bg; border-radius: $radius-lg; padding: 20px 24px; box-shadow: $shadow-soft;
  position: relative; overflow: hidden; transition: transform 0.2s ease, box-shadow 0.2s ease;
  
  @for $i from 1 through 4 {
    &:nth-child(#{$i}) { animation: fadeSlideUp 0.5s cubic-bezier(0.2, 0.8, 0.2, 1) #{$i * 0.05}s both; }
  }

  &::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; opacity: 0.8; }
  &.is-warning::before { background-color: $warning; }
  &.is-primary::before { background-color: $primary; }
  &.is-success::before { background-color: $success; }
  &.is-info::before { background-color: $info; }

  &:hover { transform: translateY(-2px); box-shadow: $shadow-hover; }

  .stat-info {
    display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;
    .stat-label { font-size: 14px; color: $text-regular; font-weight: 500; }
    .unread-badge { font-size: 12px; padding: 2px 8px; border-radius: 12px; background: #fffbeb; color: $warning; }
  }

  .stat-value { font-size: 32px; font-weight: 700; color: $text-main; line-height: 1; font-family: 'Inter', sans-serif; display: block; margin-bottom: 8px;}
  .stat-sub { color: $text-light; font-size: 13px; }
}

/* --- 面板头部与搜索栏 --- */
.panel-head {
  display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;
  &.border-bottom { padding-bottom: 16px; border-bottom: 1px solid $border-color; margin-bottom: 0; }

  .head-left {
    display: flex; align-items: center; gap: 12px;
    .head-icon { font-size: 24px; }
    h3 { font-size: 18px; font-weight: 600; color: $text-main; margin: 0 0 4px 0; }
    .sub-text { font-size: 13px; color: $text-light; margin: 0; }
  }
}

:deep(.custom-form) {
  .el-form-item__label { font-weight: 500; color: $text-regular; padding-bottom: 4px; }
  .el-input__wrapper, .el-select__wrapper {
    background-color: #f8fafc; border-radius: 8px; box-shadow: 0 0 0 1px $border-color inset; transition: all 0.2s;
    &:hover { box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.5) inset; }
    &.is-focus { background-color: #fff; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) inset, 0 0 0 1px $primary inset !important; }
  }
}
.action-row { display: flex; justify-content: flex-end; gap: 12px; margin-top: 16px; }

/* --- 列表与卡片设计 (FLIP) --- */
.list-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px; position: relative; }

.message-card {
  background: $card-bg; border-radius: $radius-lg; padding: 24px;
  display: flex; flex-direction: column; gap: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.02); transition: all 0.3s ease;
  border: 1px solid $border-color;

  &:hover { box-shadow: $shadow-hover; border-color: rgba(59, 130, 246, 0.2); }

  &.is-focused { animation: pulseBorder 2s ease-out; }
  &.is-closed { opacity: 0.7; background: #f8fafc; border-color: transparent; }

  .item-head {
    display: flex; justify-content: space-between; align-items: flex-start;
    .head-content { flex: 1; }
    .item-title-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .msg-title { font-size: 16px; font-weight: 600; color: $text-main; margin: 0; line-height: 1.4; }
    .msg-desc { font-size: 13px; color: $text-light; margin: 0; }
  }

  .item-body {
    display: grid; grid-template-columns: 1fr 140px; gap: 20px;
    .item-copy { 
      font-size: 14px; color: $text-regular; line-height: 1.6;
      .info-row { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; color: $text-main; }
      .detail-text { color: $text-regular; background: #f8fafc; padding: 10px 12px; border-radius: 8px; }
      .closed-info { background: #ecfdf5; color: #065f46; padding: 8px 12px; border-radius: 8px; font-size: 13px; }
    }
  }

  .thumb-wrap {
    width: 140px; height: 100px; border-radius: $radius-md; overflow: hidden;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.05);
    .thumb-image { width: 100%; height: 100%; object-fit: cover; }
  }

  .claim-panel {
    background: #f8fafc; border-radius: $radius-md; padding: 16px;
    border-left: 4px solid $border-color;
    &.is-pending { background: $warning-light; border-left-color: $warning; }
    &.is-approved { background: #ecfdf5; border-left-color: $success; }
    &.is-rejected { background: #fef2f2; border-left-color: $danger; }

    .claim-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; strong { display: flex; align-items: center; gap: 4px; color: $text-main; font-size: 14px; } }
    .claim-details {
      font-size: 13px; color: $text-regular; line-height: 1.6;
      p { margin: 0 0 4px 0; span { color: $text-light; } }
      .reason-text { color: $text-main; background: rgba(255,255,255,0.6); padding: 6px 10px; border-radius: 6px; margin-top: 6px; }
      .review-info { padding-top: 8px; border-top: 1px dashed $border-color; color: $text-light; }
    }
  }

  .item-actions { margin-top: auto; padding-top: 8px; }
}

:deep(.custom-tag) { border-radius: 6px; font-weight: 500; border: none; }

/* --- Vue Transition Group 丝滑过渡动画 (FLIP) --- */
.list-move, .list-enter-active, .list-leave-active { transition: all 0.5s cubic-bezier(0.2, 0.8, 0.2, 1); }
.list-enter-from, .list-leave-to { opacity: 0; transform: translateY(20px) scale(0.98); }
.list-leave-active { position: absolute; left: 0; right: 0; z-index: 0; }

@media (max-width: 1200px) {
  .list-grid { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .hero-content { flex-direction: column; align-items: flex-start; }
  .message-card .item-body { grid-template-columns: 1fr; }
  .thumb-wrap { width: 100%; height: 180px; }
}
</style>
