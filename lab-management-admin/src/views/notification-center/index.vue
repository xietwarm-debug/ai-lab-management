<template>
  <div class="page-container">
    <!-- 顶部概览与控制区 -->
    <div class="overview-section">
      <div class="header-row">
        <div class="title-area">
          <span class="eyebrow">统一消息流</span>
          <h1 class="page-title">通知中心</h1>
          <p class="page-desc">
            把公告、借用提醒、预约审批、门禁提醒和异常预警汇总到一处，支持已读未读、类型筛选和批量处理。
            <span class="update-time">最近刷新 {{ lastUpdated || '-' }}</span>
          </p>
        </div>
        <div class="action-area">
          <el-button @click="markShownAsRead" :disabled="!filteredItems.length" :icon="Check">标记当前已读</el-button>
          <el-button type="primary" :loading="loading" @click="fetchAll" :icon="RefreshRight">刷新消息流</el-button>
        </div>
      </div>

      <!-- 数据指标卡片网格 -->
      <div class="stats-grid">
        <div 
          v-for="item in metricCards" 
          :key="item.key" 
          class="stat-card"
          :class="[`is-${item.colorType}`, { 'has-unread': item.unread > 0 }]"
        >
          <div class="stat-info">
            <span class="stat-label">{{ item.label }}</span>
            <span v-if="item.unread > 0" class="unread-badge">未读 {{ item.unread }}</span>
          </div>
          <div class="stat-value">{{ item.value }}</div>
        </div>
      </div>
    </div>

    <!-- 列表控制栏 -->
    <div class="control-bar">
      <div class="filter-group">
        <el-radio-group v-model="typeFilter" size="large" class="custom-radio">
          <el-radio-button v-for="item in typeOptions" :key="item.value" :label="item.value">
            {{ item.label }}
          </el-radio-button>
        </el-radio-group>

        <el-divider direction="vertical" />

        <el-radio-group v-model="readFilter" size="large" class="custom-radio light-radio">
          <el-radio-button label="all">全部</el-radio-button>
          <el-radio-button label="unread">未读</el-radio-button>
          <el-radio-button label="read">已读</el-radio-button>
        </el-radio-group>
      </div>

      <div class="search-group">
        <el-input
          v-model="keyword"
          placeholder="搜索标题、消息内容、实验室或申请人"
          :prefix-icon="Search"
          clearable
          class="custom-search"
        />
      </div>
    </div>

    <!-- 批量操作栏 -->
    <div class="batch-bar">
      <span class="select-info">已选 <strong>{{ selectedIds.length }}</strong> 条</span>
      <div class="batch-actions">
        <el-button link @click="toggleSelectAll">
          {{ isAllShownSelected ? '取消全选' : '全选当前列表' }}
        </el-button>
        <el-button link @click="markBatch(true)" :disabled="!selectedIds.length">批量已读</el-button>
        <el-button link @click="markBatch(false)" :disabled="!selectedIds.length">批量未读</el-button>
        <el-button
          size="small"
          type="primary"
          plain
          :loading="batchProcessing"
          :disabled="!selectedProcessableCount"
          @click="processSelected"
        >
          批量处理 {{ selectedProcessableCount }} 条
        </el-button>
      </div>
    </div>

    <!-- 消息列表区 -->
    <transition-group name="list" tag="div" class="message-list" v-if="filteredItems.length">
      <div 
        v-for="item in filteredItems" 
        :key="item.id" 
        class="message-card"
        :class="{ 'is-read': isRead(item), 'is-selected': isSelected(item.id) }"
      >
        <div class="card-left">
          <el-checkbox class="msg-checkbox" :model-value="isSelected(item.id)" @change="toggleSelect(item.id)" />
          <div class="msg-content">
            <div class="msg-header">
              <el-tag :type="item.tagType" size="small" effect="light" class="custom-tag">
                {{ item.typeLabel }}
              </el-tag>
              <h3 class="msg-title">{{ item.title }}</h3>
              <span v-if="!isRead(item)" class="status-dot"></span>
              
              <!-- 级别/状态 Badge -->
              <span class="severity-badge" :class="`badge-${item.statusType}`">
                {{ item.statusLabel }}
              </span>
            </div>
            <p class="msg-desc">{{ item.subtitle }}</p>
            <p class="msg-detail">{{ item.message }}</p>
          </div>
        </div>

        <div class="card-right">
          <div class="msg-time">{{ item.createdAt || '-' }}</div>
          <div class="msg-actions">
            <el-button link type="info" class="hover-btn" @click="goItem(item)">查看详情</el-button>
            <el-button link type="primary" class="hover-btn" @click="toggleRead(item)">
              {{ isRead(item) ? '标记未读' : '标记已读' }}
            </el-button>
            <el-button
              v-if="item.processable"
              link
              type="primary"
              :loading="processingIds[item.id]"
              @click="processItem(item)"
            >
              {{ item.processLabel }}
            </el-button>
          </div>
        </div>
      </div>
    </transition-group>
    
    <transition name="fade">
      <div v-if="!filteredItems.length" class="empty-state">
        <el-empty description="当前筛选条件下暂无消息" />
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Check, RefreshRight, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

// 假设这些是你实际项目中的 API 和 Store
import { getAdminAnnouncements, updateAnnouncement } from '@/api/announcements'
import { getAdminAiRiskAlerts } from '@/api/ai'
import { approveBorrowRequest, getBorrowRequests, remindBorrowRequest } from '@/api/borrow'
import { approveReservation, getReservationList } from '@/api/reservations'
import { confirmDoorReminderOpen, getDoorRemindersToday } from '@/api/schedule'
import { useAuthStore } from '@/stores/auth'
import { resolveAdminJumpUrl } from '@/utils/admin-links'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const batchProcessing = ref(false)
const lastUpdated = ref('')
const allItems = ref([])
const selectedIds = ref([])
const keyword = ref('')
const typeFilter = ref('all')
const readFilter = ref('all')
const readState = ref({})
const processingIds = reactive({})

const typeOptions = [
  { value: 'all', label: '全部' },
  { value: 'announcement', label: '公告' },
  { value: 'reservation', label: '预约审批' },
  { value: 'asset_borrow', label: '借用提醒' },
  { value: 'door_reminder', label: '门禁提醒' },
  { value: 'risk_alert', label: '异常预警' }
]

const storageKey = computed(() => `admin_notification_center_${authStore.username || 'default'}`)

const filteredItems = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return allItems.value.filter((item) => {
    if (typeFilter.value !== 'all' && item.type !== typeFilter.value) return false
    const read = isRead(item)
    if (readFilter.value === 'read' && !read) return false
    if (readFilter.value === 'unread' && read) return false
    if (!text) return true
    const haystack = [item.title, item.subtitle, item.message, item.statusLabel]
      .join(' ')
      .toLowerCase()
    return haystack.includes(text)
  })
})

const unreadTotal = computed(() => allItems.value.filter((item) => !isRead(item)).length)
const isAllShownSelected = computed(() => (
  filteredItems.value.length > 0 && filteredItems.value.every((item) => selectedIds.value.includes(item.id))
))
const selectedItems = computed(() => allItems.value.filter((item) => selectedIds.value.includes(item.id)))
const selectedProcessableCount = computed(() => selectedItems.value.filter((item) => item.processable).length)

// 【UI优化】增强了 metricCards 数据结构，加入了 UI 颜色标识 colorType 和 unread 计数
const metricCards = computed(() => {
  const build = (type, label, colorType) => {
    const rows = allItems.value.filter((item) => item.type === type)
    const unreadCount = rows.filter((item) => !isRead(item)).length
    return {
      key: type,
      label,
      value: rows.length,
      unread: unreadCount,
      colorType: colorType
    }
  }
  return [
    { key: 'all', label: '消息总量', value: allItems.value.length, unread: unreadTotal.value, colorType: 'primary' },
    build('announcement', '公告消息', 'info'),
    build('reservation', '预约审批', 'info'),
    build('asset_borrow', '借用提醒', 'warning'),
    build('door_reminder', '门禁提醒', 'info'),
    build('risk_alert', '异常预警', 'danger')
  ]
})

function nowText() {
  const date = new Date()
  const pad = (value) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function toTimeValue(value) {
  const normalized = String(value || '').trim().replace(' ', 'T')
  const numeric = Date.parse(normalized)
  return Number.isFinite(numeric) ? numeric : 0
}

function compareDesc(a, b) {
  return toTimeValue(b.createdAt) - toTimeValue(a.createdAt)
}

function loadReadState() {
  try {
    const raw = localStorage.getItem(storageKey.value)
    readState.value = raw ? JSON.parse(raw) : {}
  } catch (error) {
    readState.value = {}
  }
}

function saveReadState() {
  localStorage.setItem(storageKey.value, JSON.stringify(readState.value))
}

function isRead(item) {
  return Boolean(readState.value[item.id])
}

function setRead(item, read) {
  if (read) {
    readState.value = {
      ...readState.value,
      [item.id]: { readAt: nowText() }
    }
  } else {
    const nextState = { ...readState.value }
    delete nextState[item.id]
    readState.value = nextState
  }
  saveReadState()
}

function isSelected(id) {
  return selectedIds.value.includes(id)
}

function toggleSelect(id) {
  if (isSelected(id)) {
    selectedIds.value = selectedIds.value.filter((item) => item !== id)
    return
  }
  selectedIds.value = [...selectedIds.value, id]
}

function toggleSelectAll() {
  if (isAllShownSelected.value) {
    const shownIds = new Set(filteredItems.value.map((item) => item.id))
    selectedIds.value = selectedIds.value.filter((id) => !shownIds.has(id))
    return
  }
  const merged = new Set([...selectedIds.value, ...filteredItems.value.map((item) => item.id)])
  selectedIds.value = Array.from(merged)
}

function markBatch(read) {
  selectedItems.value.forEach((item) => {
    setRead(item, read)
  })
}

function markShownAsRead() {
  filteredItems.value.forEach((item) => {
    setRead(item, true)
  })
}

function toggleRead(item) {
  setRead(item, !isRead(item))
}

// === 数据拼装逻辑保持原样 ===
function toAnnouncementItem(row) {
  return {
    id: `announcement-${row.id}`,
    type: 'announcement',
    typeLabel: '公告',
    tagType: 'primary',
    title: row.title || `公告 #${row.id}`,
    subtitle: `${row.publisherName || '-'} · ${row.publishAt || '-'}`,
    message: row.status === 'scheduled' ? '定时公告待发布，可在消息流中直接处理。' : '公告已发布。',
    statusLabel: row.status === 'scheduled' ? '待发布' : '已发布',
    statusType: row.status === 'scheduled' ? 'warning' : 'success',
    createdAt: row.publishAt || row.createdAt || '',
    jumpUrl: '/announcements',
    processable: row.status === 'scheduled',
    processLabel: '立即发布',
    raw: row
  }
}

function toReservationItem(row) {
  return {
    id: `reservation-${row.id}`,
    type: 'reservation',
    typeLabel: '预约审批',
    tagType: 'warning',
    title: `${row.labName || '实验室'} 预约待审批`,
    subtitle: `${row.user || '-'} · ${row.date || '-'} ${row.time || ''}`.trim(),
    message: row.reason || '该预约申请正在等待后台审核。',
    statusLabel: row.status === 'pending' ? '待审核' : row.status || '-',
    statusType: 'warning',
    createdAt: row.createdAt || '',
    jumpUrl: '/reservations',
    processable: row.status === 'pending',
    processLabel: '通过预约',
    raw: row
  }
}

function toBorrowItem(row) {
  const overdue = Boolean(row.isOverdue) || row.status === 'overdue'
  return {
    id: `asset-borrow-${row.id}-${overdue ? 'overdue' : row.status}`,
    type: 'asset_borrow',
    typeLabel: '借用提醒',
    tagType: overdue ? 'danger' : 'success',
    title: overdue ? '借用逾期未归还' : '借用申请待处理',
    subtitle: `${row.equipmentName || row.equipmentAssetCode || '-'} · ${row.applicantName || row.applicantUserName || '-'}`,
    message: overdue
      ? `应归还时间 ${row.expectedReturnAt || '-'}，建议尽快发送催还提醒。`
      : `${row.purpose || '该申请正在等待借用审批。'}`,
    statusLabel: overdue ? '已逾期' : row.status === 'pending' ? '待审批' : row.status || '-',
    statusType: overdue ? 'danger' : 'warning',
    createdAt: row.updatedAt || row.createdAt || '',
    jumpUrl: '/borrow-approval',
    processable: overdue || row.status === 'pending',
    processLabel: overdue ? '发送催还' : '通过借用',
    raw: row
  }
}

function toDoorItem(row) {
  return {
    id: `door-reminder-${row.id}`,
    type: 'door_reminder',
    typeLabel: '门禁提醒',
    tagType: 'info',
    title: `${row.labName || '-'} 开门提醒`,
    subtitle: `${row.courseName || '-'} · ${row.occurrenceDate || '-'} ${row.periodText || ''}`.trim(),
    message: `${row.teacherName || '-'} / ${row.className || '-'}，当前门禁状态 ${row.doorStatus || 'pending'}。`,
    statusLabel: row.doorStatus === 'pending' ? '待处理' : row.doorStatus || '-',
    statusType: row.doorStatus === 'pending' ? 'warning' : 'success',
    createdAt: row.remindAt || row.startAt || '',
    jumpUrl: '/schedule-manage',
    processable: row.doorStatus === 'pending',
    processLabel: '确认开门',
    raw: row
  }
}

function toRiskItem(row, index) {
  return {
    id: `risk-alert-${index}-${row.title}`,
    type: 'risk_alert',
    typeLabel: '异常预警',
    tagType: 'danger',
    title: row.title || '设备风险预警',
    subtitle: `风险分 ${row.score || 0} · 等级 ${row.level || '-'}`,
    message: row.description || '请及时查看风险详情并安排处理。',
    statusLabel: row.level === 'high' ? '高风险' : row.level === 'medium' ? '中风险' : '关注',
    statusType: row.level === 'high' ? 'danger' : row.level === 'medium' ? 'warning' : 'info',
    createdAt: lastUpdated.value || nowText(),
    jumpUrl: resolveAdminJumpUrl(row.jumpUrl || '') || '/equipments',
    processable: false,
    processLabel: '',
    raw: row
  }
}

async function fetchAll() {
  loading.value = true
  try {
    const [
      announcementResp,
      reservationResp,
      borrowPendingResp,
      borrowOverdueResp,
      doorResp,
      riskResp
    ] = await Promise.all([
      getAdminAnnouncements({ status: 'scheduled', limit: 30 }),
      getReservationList({ status: 'pending', page: 1, pageSize: 30 }),
      getBorrowRequests({ status: 'pending', page: 1, pageSize: 30 }),
      getBorrowRequests({ status: 'overdue', page: 1, pageSize: 30 }),
      getDoorRemindersToday(),
      getAdminAiRiskAlerts()
    ])

    const announcementRows = Array.isArray(announcementResp.data?.data) ? announcementResp.data.data : []
    const reservationRows = Array.isArray(reservationResp.data?.data) ? reservationResp.data.data : []
    const borrowPendingRows = Array.isArray(borrowPendingResp.data?.data) ? borrowPendingResp.data.data : []
    const borrowOverdueRows = Array.isArray(borrowOverdueResp.data?.data) ? borrowOverdueResp.data.data : []
    const doorRows = Array.isArray(doorResp.data?.data?.list) ? doorResp.data.data.list : []
    const riskRows = Array.isArray(riskResp.data?.data?.alerts) ? riskResp.data.data.alerts : []

    allItems.value = [
      ...announcementRows.map(toAnnouncementItem),
      ...reservationRows.map(toReservationItem),
      ...borrowPendingRows.map(toBorrowItem),
      ...borrowOverdueRows.map(toBorrowItem),
      ...doorRows.filter((item) => item.doorStatus === 'pending').map(toDoorItem),
      ...riskRows.map((item, index) => toRiskItem(item, index))
    ].sort(compareDesc)
    
    lastUpdated.value = nowText()
    selectedIds.value = selectedIds.value.filter((id) => allItems.value.some((item) => item.id === id))
  } catch (error) {
    console.error('Fetch error:', error)
  } finally {
    loading.value = false
  }
}

async function executeProcess(item) {
  if (item.type === 'announcement') {
    const raw = item.raw || {}
    await updateAnnouncement(raw.id, {
      title: raw.title || '',
      content: raw.content || '',
      publishAt: nowText(),
      isPinned: Boolean(raw.isPinned)
    })
    return '公告已立即发布'
  }
  if (item.type === 'reservation') {
    await approveReservation(item.raw.id)
    return '预约已通过'
  }
  if (item.type === 'asset_borrow') {
    if (item.statusLabel === '已逾期') {
      await remindBorrowRequest(item.raw.id, {
        message: `请尽快归还 ${item.raw.equipmentName || item.raw.equipmentAssetCode || '借用设备'}。`
      })
      return '已发送催还提醒'
    }
    await approveBorrowRequest(item.raw.id)
    return '借用申请已通过'
  }
  if (item.type === 'door_reminder') {
    await confirmDoorReminderOpen(item.raw.id, {
      note: '通知中心批量确认开门'
    })
    return '门禁提醒已确认'
  }
  return ''
}

async function processItem(item) {
  if (!item.processable) return
  processingIds[item.id] = true
  try {
    const message = await executeProcess(item)
    setRead(item, true)
    if (message) ElMessage.success(message)
    await fetchAll()
  } catch(e) {
    ElMessage.error('处理失败')
  } finally {
    processingIds[item.id] = false
  }
}

async function processSelected() {
  const rows = selectedItems.value.filter((item) => item.processable)
  if (!rows.length) {
    ElMessage.warning('当前所选消息没有可执行的批量动作')
    return
  }
  batchProcessing.value = true
  try {
    for (const item of rows) {
      await executeProcess(item)
      setRead(item, true)
    }
    ElMessage.success(`已处理 ${rows.length} 条消息`)
    await fetchAll()
  } finally {
    batchProcessing.value = false
  }
}

function goItem(item) {
  if (!isRead(item)) {
    setRead(item, true)
  }
  const target = resolveAdminJumpUrl(item.jumpUrl || '') || item.jumpUrl || '/dashboard'
  router.push(target)
}

onMounted(() => {
  loadReadState()
  fetchAll()
})
</script>

<style scoped lang="scss">
// 设计系统变量
$bg-color: #f8fafc;
$card-bg: #ffffff;
$text-main: #0f172a;
$text-regular: #475569;
$text-light: #94a3b8;
$border-color: #e2e8f0;
$primary: #3b82f6;
$danger: #ef4444;
$warning: #f59e0b;
$success: #10b981;
$info: #64748b;
$radius-lg: 16px;
$radius-md: 8px;
$shadow-soft: 0 10px 30px rgba(0, 0, 0, 0.03);
$shadow-hover: 0 15px 35px rgba(59, 130, 246, 0.06);

// --- 核心入场动画 Keyframes ---
@keyframes fadeSlideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.page-container {
  padding: 32px;
  background-color: $bg-color;
  min-height: 100vh;
  box-sizing: border-box;
}

/* --- 顶部概览区 --- */
.overview-section {
  margin-bottom: 24px;
  animation: fadeSlideUp 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-end; // 修改为底部对齐更好看
  margin-bottom: 24px;

  .eyebrow {
    display: inline-block;
    color: $primary;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.08em;
    margin-bottom: 8px;
  }

  .page-title {
    font-size: 28px;
    font-weight: 700;
    color: $text-main;
    margin: 0 0 12px 0;
  }

  .page-desc {
    color: $text-regular;
    font-size: 14px;
    margin: 0;
    line-height: 1.5;

    .update-time {
      color: $text-light;
      margin-left: 16px;
      font-size: 13px;
      padding-left: 16px;
      border-left: 1px solid $border-color;
    }
  }
}

/* --- 指标卡片 (悬浮美学) --- */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 16px;
}

.stat-card {
  background: $card-bg;
  border-radius: $radius-lg;
  padding: 20px;
  box-shadow: $shadow-soft;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  position: relative;
  overflow: hidden;
  animation: fadeSlideUp 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both;

  // 使用 SCSS 循环为指标卡片添加优雅的交错延迟 (Staggered Animation)
  @for $i from 1 through 6 {
    &:nth-child(#{$i}) {
      animation-delay: #{$i * 0.05}s;
    }
  }

  // 左侧彩色指示条
  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 4px;
    opacity: 0;
    transition: opacity 0.3s;
  }

  &.has-unread::before { opacity: 1; }
  &.is-primary::before { background-color: $primary; }
  &.is-danger::before { background-color: $danger; }
  &.is-warning::before { background-color: $warning; }
  &.is-info::before { background-color: $info; }

  &:hover {
    transform: translateY(-2px);
    box-shadow: $shadow-hover;
  }

  .stat-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;

    .stat-label {
      font-size: 14px;
      color: $text-regular;
      font-weight: 500;
    }

    .unread-badge {
      font-size: 12px;
      padding: 2px 8px;
      border-radius: 12px;
      background: #f1f5f9;
      color: $text-regular;
    }
  }

  .stat-value {
    font-size: 32px;
    font-weight: 700;
    color: $text-main;
    line-height: 1;
    font-family: 'Inter', sans-serif;
  }

  // 特定颜色的未读 Badge 样式
  &.is-danger .unread-badge { background: #fef2f2; color: $danger; }
  &.is-warning .unread-badge { background: #fffbeb; color: $warning; }
  &.is-primary .unread-badge { background: #eff6ff; color: $primary; }
}

/* --- 控制栏 --- */
.control-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  background: $card-bg;
  padding: 16px 24px;
  border-radius: $radius-lg;
  box-shadow: $shadow-soft;
  margin-bottom: 16px;
  animation: fadeSlideUp 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) 0.1s both;

  .filter-group {
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
  }
}

// 药丸风格定制 Radio
:deep(.custom-radio) {
  .el-radio-button__inner {
    border: none !important;
    background: transparent;
    color: $text-regular;
    font-weight: 500;
    border-radius: 6px !important;
    padding: 8px 16px;
    box-shadow: none !important;
  }
  
  .el-radio-button__original-radio:checked + .el-radio-button__inner {
    background-color: #eff6ff;
    color: $primary;
    box-shadow: none !important;
  }

  &.light-radio .el-radio-button__original-radio:checked + .el-radio-button__inner {
    background-color: #f1f5f9;
    color: $text-main;
  }
}

:deep(.custom-search) {
  width: 320px;
  .el-input__wrapper {
    box-shadow: 0 0 0 1px $border-color inset;
    border-radius: 8px;
    padding: 4px 12px;
    &:hover, &.is-focus { box-shadow: 0 0 0 1px $primary inset; }
  }
}

/* --- 批量操作栏 --- */
.batch-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 8px 16px 8px;
  flex-wrap: wrap;
  animation: fadeSlideUp 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) 0.15s both;

  .select-info {
    font-size: 14px;
    color: $text-regular;
    strong { color: $primary; font-size: 16px; }
  }

  .batch-actions {
    display: flex;
    gap: 8px;
    align-items: center;
  }
}

/* --- 消息列表 --- */
.message-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: relative;
}

/* --- Vue Transition Group 丝滑过渡动画 --- */
.list-move,
.list-enter-active,
.list-leave-active {
  transition: all 0.4s cubic-bezier(0.2, 0.8, 0.2, 1);
}

.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateY(20px) scale(0.98);
}

.list-leave-active {
  position: absolute;
  left: 0;
  right: 0;
  z-index: 0;
}

/* 缺省页动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.empty-state {
  background: $card-bg;
  border-radius: $radius-lg;
  padding: 60px 0;
  box-shadow: $shadow-soft;
}

.message-card {
  background: $card-bg;
  border-radius: $radius-lg;
  padding: 20px 24px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  box-shadow: $shadow-soft;
  transition: all 0.2s ease;
  border: 1px solid transparent;

  &:hover {
    border-color: rgba(59, 130, 246, 0.1);
    box-shadow: $shadow-hover;
    .hover-btn { opacity: 1; visibility: visible; }
  }

  // 选中状态
  &.is-selected {
    border-color: rgba(59, 130, 246, 0.3);
    background-color: #f8fafc;
  }

  // 已读状态
  &.is-read {
    opacity: 0.65;
    .msg-title { color: $text-regular; font-weight: 500; }
  }

  .card-left {
    display: flex;
    gap: 16px;
    flex: 1;
  }

  .msg-checkbox {
    margin-top: 2px;
  }

  .msg-content {
    flex: 1;
  }

  .msg-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
    flex-wrap: wrap;

    .msg-title {
      font-size: 16px;
      font-weight: 600;
      color: $text-main;
      margin: 0;
    }

    .status-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background-color: $danger;
    }

    .severity-badge {
      font-size: 12px;
      padding: 2px 8px;
      border-radius: 4px;
      border: 1px solid currentColor;
      
      &.badge-danger { color: $danger; background: #fef2f2; border-color: rgba(239, 68, 68, 0.2); }
      &.badge-warning { color: $warning; background: #fffbeb; border-color: rgba(245, 158, 11, 0.2); }
      &.badge-success { color: $success; background: #ecfdf5; border-color: rgba(16, 185, 129, 0.2); }
      &.badge-info, &.badge-primary { color: $info; background: #f1f5f9; border-color: rgba(100, 116, 139, 0.2); }
    }
  }

  .msg-desc {
    color: $text-regular;
    font-size: 13px;
    margin: 0 0 8px 0;
  }
  
  .msg-detail {
    color: $text-main;
    font-size: 14px;
    margin: 0;
    line-height: 1.5;
  }

  .card-right {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 12px;
    min-width: 200px;

    .msg-time {
      font-size: 13px;
      color: $text-light;
    }

    .msg-actions {
      display: flex;
      gap: 12px;

      // 默认隐藏部分按钮，hover时显示
      .hover-btn {
        opacity: 0;
        visibility: hidden;
        transition: all 0.2s;
      }
    }
  }
}

:deep(.custom-tag) {
  border-radius: 6px;
  font-weight: 500;
  border: none;
  &.el-tag--danger { background-color: #fef2f2; color: $danger; }
  &.el-tag--warning { background-color: #fffbeb; color: $warning; }
}

// 响应式设计
@media (max-width: 960px) {
  .header-row { flex-direction: column; align-items: flex-start; gap: 16px; }
  .message-card {
    flex-direction: column;
    .card-right {
      width: 100%;
      align-items: flex-start;
      margin-top: 16px;
      padding-left: 30px; // 与左侧复选框对齐
      flex-direction: row;
      justify-content: space-between;
      
      .hover-btn { opacity: 1; visibility: visible; }
    }
  }
}
</style>