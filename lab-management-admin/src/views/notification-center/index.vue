<template>
  <div class="notify-page">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="eyebrow">统一消息流</span>
        <h2>通知中心</h2>
        <p>把公告、借用提醒、预约审批、门禁提醒和异常预警汇总到一处，支持已读未读、类型筛选和批量处理。</p>
        <div class="hero-meta">
          <span>总消息 {{ allItems.length }}</span>
          <span>未读 {{ unreadTotal }}</span>
          <span>最近刷新 {{ lastUpdated || '-' }}</span>
        </div>
      </div>
      <div class="hero-actions">
        <el-button @click="markShownAsRead" :disabled="!filteredItems.length">标记当前已读</el-button>
        <el-button type="primary" :loading="loading" @click="fetchAll">刷新消息流</el-button>
      </div>
    </section>

    <section class="metric-grid">
      <article class="metric-card" v-for="item in metricCards" :key="item.key">
        <span class="metric-label">{{ item.label }}</span>
        <strong class="metric-value">{{ item.value }}</strong>
        <span class="metric-sub">{{ item.sub }}</span>
      </article>
    </section>

    <section class="panel-card">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-radio-group v-model="typeFilter">
            <el-radio-button v-for="item in typeOptions" :key="item.value" :label="item.value">
              {{ item.label }}
            </el-radio-button>
          </el-radio-group>
          <el-radio-group v-model="readFilter">
            <el-radio-button label="all">全部</el-radio-button>
            <el-radio-button label="unread">未读</el-radio-button>
            <el-radio-button label="read">已读</el-radio-button>
          </el-radio-group>
        </div>
        <div class="toolbar-right">
          <el-input
            v-model="keyword"
            placeholder="搜索标题、消息内容、实验室或申请人"
            clearable
            style="width: 320px"
          />
        </div>
      </div>

      <div class="batch-bar">
        <span>已选 {{ selectedIds.length }} 条</span>
        <el-button size="small" @click="toggleSelectAll">
          {{ isAllShownSelected ? '取消全选' : '全选当前列表' }}
        </el-button>
        <el-button size="small" @click="markBatch(true)" :disabled="!selectedIds.length">批量已读</el-button>
        <el-button size="small" @click="markBatch(false)" :disabled="!selectedIds.length">批量未读</el-button>
        <el-button
          size="small"
          type="primary"
          :loading="batchProcessing"
          :disabled="!selectedProcessableCount"
          @click="processSelected"
        >
          批量处理 {{ selectedProcessableCount }} 条
        </el-button>
      </div>

      <div v-if="filteredItems.length" class="stream-list">
        <article
          v-for="item in filteredItems"
          :key="item.id"
          class="stream-item"
          :class="{ unread: !isRead(item), active: isSelected(item.id) }"
        >
          <div class="stream-head">
            <div class="stream-main">
              <el-checkbox :model-value="isSelected(item.id)" @change="toggleSelect(item.id)" />
              <div>
                <div class="title-row">
                  <el-tag size="small" :type="item.tagType">{{ item.typeLabel }}</el-tag>
                  <strong>{{ item.title }}</strong>
                  <span v-if="!isRead(item)" class="unread-dot">未读</span>
                </div>
                <p class="subtitle">{{ item.subtitle }}</p>
              </div>
            </div>
            <div class="stream-side">
              <el-tag size="small" effect="plain" :type="item.statusType">{{ item.statusLabel }}</el-tag>
              <span>{{ item.createdAt || '-' }}</span>
            </div>
          </div>

          <p class="message">{{ item.message }}</p>

          <div class="stream-actions">
            <el-button text @click="goItem(item)">查看详情</el-button>
            <el-button text @click="toggleRead(item)">{{ isRead(item) ? '标记未读' : '标记已读' }}</el-button>
            <el-button
              v-if="item.processable"
              text
              type="primary"
              :loading="processingIds[item.id]"
              @click="processItem(item)"
            >
              {{ item.processLabel }}
            </el-button>
          </div>
        </article>
      </div>
      <el-empty v-else description="当前筛选条件下暂无消息" />
    </section>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
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

const metricCards = computed(() => {
  const build = (type, label) => {
    const rows = allItems.value.filter((item) => item.type === type)
    return {
      key: type,
      label,
      value: rows.length,
      sub: `未读 ${rows.filter((item) => !isRead(item)).length}`
    }
  }
  return [
    { key: 'all', label: '消息总量', value: allItems.value.length, sub: `未读 ${unreadTotal.value}` },
    build('announcement', '公告消息'),
    build('reservation', '预约审批'),
    build('asset_borrow', '借用提醒'),
    build('door_reminder', '门禁提醒'),
    build('risk_alert', '异常预警')
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
      [item.id]: {
        readAt: nowText()
      }
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
.notify-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.hero-card,
.panel-card,
.metric-card {
  border: 1px solid var(--app-border);
  border-radius: 28px;
  background:
    radial-gradient(circle at top right, rgba(15, 76, 129, 0.14), transparent 32%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
  box-shadow: var(--app-shadow);
}

.hero-card,
.toolbar,
.hero-meta,
.batch-bar,
.stream-head,
.stream-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.hero-card,
.panel-card {
  padding: 24px;
}

.hero-copy h2,
.metric-value,
.title-row strong {
  margin: 0;
}

.hero-copy p,
.subtitle,
.message {
  margin: 0;
  color: var(--app-text-secondary);
}

.hero-meta,
.batch-bar,
.subtitle {
  color: var(--app-text-tertiary);
  flex-wrap: wrap;
}

.eyebrow {
  display: inline-flex;
  margin-bottom: 8px;
  color: #0f4c81;
  font-size: 13px;
  letter-spacing: 0.08em;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.metric-card {
  padding: 20px;
}

.metric-label,
.metric-sub {
  display: block;
}

.metric-label {
  color: var(--app-text-secondary);
  font-size: 13px;
}

.metric-value {
  display: block;
  margin: 8px 0;
  font-size: 32px;
}

.metric-sub {
  color: var(--app-text-tertiary);
  font-size: 13px;
}

.toolbar,
.batch-bar {
  flex-wrap: wrap;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.stream-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 18px;
}

.stream-item {
  padding: 18px;
  border-radius: 22px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.76);
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.stream-item.unread {
  border-color: rgba(15, 76, 129, 0.24);
  box-shadow: 0 12px 28px rgba(15, 76, 129, 0.08);
}

.stream-item.active {
  transform: translateY(-1px);
  border-color: rgba(219, 39, 119, 0.26);
}

.stream-main,
.title-row,
.stream-side {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stream-main {
  align-items: flex-start;
}

.stream-side {
  flex-direction: column;
  align-items: flex-end;
  color: var(--app-text-tertiary);
  font-size: 13px;
}

.title-row {
  flex-wrap: wrap;
}

.unread-dot {
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(219, 39, 119, 0.1);
  color: #be185d;
  font-size: 12px;
}

.message {
  margin: 14px 0 10px;
  line-height: 1.7;
}

.stream-actions {
  justify-content: flex-end;
}

@media (max-width: 960px) {
  .hero-card,
  .toolbar,
  .stream-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .stream-side,
  .stream-actions {
    width: 100%;
    align-items: flex-start;
    justify-content: flex-start;
  }
}
</style>
