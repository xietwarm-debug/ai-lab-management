<template>
  <div class="todo-page">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="eyebrow">管理员工作台</span>
        <h2>待办中心</h2>
        <p>把预约审批、报修工单、认领审核、课程提醒和定时公告集中在一个页面里处理。</p>
        <div class="hero-meta">
          <span>生成时间：{{ generatedAt || '-' }}</span>
          <span>AI 日报：{{ dailyBrief.generatedAt || '-' }}</span>
        </div>
      </div>
      <div class="hero-actions">
        <el-button :loading="loading" @click="fetchTodos">刷新待办</el-button>
        <el-button :loading="briefLoading" @click="fetchAiBrief">刷新日报</el-button>
      </div>
    </section>

    <section class="metric-grid">
      <article class="metric-card">
        <span class="metric-label">待办总量</span>
        <strong class="metric-value">{{ summary.total || 0 }}</strong>
        <span class="metric-sub">所有卡片合计</span>
      </article>
      <article class="metric-card">
        <span class="metric-label">超时总量</span>
        <strong class="metric-value danger">{{ summary.timeoutTotal || 0 }}</strong>
        <span class="metric-sub">建议优先处理</span>
      </article>
      <article class="metric-card">
        <span class="metric-label">高优先级</span>
        <strong class="metric-value warning">{{ summary.highPriorityTotal || 0 }}</strong>
        <span class="metric-sub">分值较高</span>
      </article>
      <article class="metric-card">
        <span class="metric-label">AI 聚焦动作</span>
        <strong class="metric-value">{{ dailyBrief.focusActions?.length || 0 }}</strong>
        <span class="metric-sub">日报给出的建议</span>
      </article>
    </section>

    <section class="panel-grid">
      <article class="panel-card panel-span-2">
        <div class="panel-head">
          <div>
            <h3>AI 每日简报</h3>
            <span>{{ dailyBrief.generatedAt || '暂无日报' }}</span>
          </div>
          <el-button text :loading="briefLoading" @click="fetchAiBrief">刷新</el-button>
        </div>
        <p class="brief-copy">{{ dailyBrief.summaryText || '暂时还没有日报摘要。' }}</p>
        <div v-if="dailyBrief.highlights?.length" class="brief-list">
          <div v-for="(item, index) in dailyBrief.highlights" :key="index" class="brief-item">
            <span class="brief-dot" />
            <span>{{ item }}</span>
          </div>
        </div>
        <el-empty v-else description="暂无日报重点" />
        <div v-if="dailyBrief.focusActions?.length" class="focus-row">
          <el-button
            v-for="(item, index) in dailyBrief.focusActions"
            :key="`${item.title}-${index}`"
            text
            type="primary"
            @click="jumpTo(item.jumpUrl)"
          >
            {{ item.title || '查看建议动作' }}
          </el-button>
        </div>
      </article>

      <article class="panel-card">
        <div class="panel-head">
          <div>
            <h3>排序与显示</h3>
            <span>控制卡片内排序与完成态展示</span>
          </div>
        </div>
        <el-form label-position="top">
          <el-form-item label="排序字段">
            <el-radio-group v-model="sortBy" @change="fetchTodos">
              <el-radio-button label="priority">按优先级</el-radio-button>
              <el-radio-button label="deadline">按截止时间</el-radio-button>
              <el-radio-button label="createdAt">按创建时间</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="排序方向">
            <el-radio-group v-model="sortOrder" @change="fetchTodos">
              <el-radio-button label="desc">降序</el-radio-button>
              <el-radio-button label="asc">升序</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <div class="switch-row">
            <span>显示已标记完成</span>
            <el-switch v-model="showDone" />
          </div>
        </el-form>
      </article>
    </section>

    <section v-if="loading" class="loading-card panel-card">
      <el-skeleton :rows="4" animated />
    </section>

    <section v-for="card in displayCards" :key="card.key" class="todo-card panel-card">
      <div class="panel-head">
        <div>
          <h3>{{ card.title }}</h3>
          <span>{{ card.description }}</span>
          <p class="card-meta">总量 {{ card.total || 0 }} · 超时 {{ card.timeoutCount || 0 }} · 当前展示 {{ card.visibleCount || 0 }}</p>
        </div>
        <div class="card-actions">
          <el-button text @click="jumpTo(card.jumpUrl)">跳转页</el-button>
          <el-button @click="toggleSelectAll(card)">
            {{ isCardAllSelected(card) ? '取消全选' : '全选当前卡片' }}
          </el-button>
          <el-button
            type="primary"
            :loading="processingCardMap[card.key]"
            @click="processCard(card)"
          >
            批量处理
          </el-button>
        </div>
      </div>

      <div class="chip-row">
        <el-button size="small" @click="clearSelection(card.key)">清空选择</el-button>
        <el-button size="small" @click="markTimeoutBatch(card, true)">标记超时</el-button>
        <el-button size="small" @click="markTimeoutBatch(card, false)">取消超时</el-button>
        <el-button size="small" @click="markDoneBatch(card, true)">标记完成</el-button>
        <el-button size="small" @click="markDoneBatch(card, false)">取消完成</el-button>
        <span class="selected-text">已选 {{ selectedCount(card.key) }}</span>
      </div>

      <div v-if="card.items.length" class="item-list">
        <article v-for="item in card.items" :key="item.id" class="item-card">
          <div class="item-head">
            <div class="item-main">
              <el-checkbox
                :model-value="isSelected(card.key, item.entityId)"
                @change="toggleSelect(card.key, item.entityId)"
              />
              <div>
                <strong>{{ item.title }}</strong>
                <p>{{ item.subtitle || '-' }}</p>
              </div>
            </div>
            <div class="tag-row">
              <el-tag size="small" :type="priorityTagType(item.effectivePriority)">{{ item.priorityLevel || '普通' }}</el-tag>
              <el-tag v-if="item.effectiveTimeout" size="small" type="danger">超时</el-tag>
              <el-tag v-if="item.manualDone" size="small" type="success">已完成</el-tag>
            </div>
          </div>

          <p v-if="item.detail" class="detail-copy">{{ item.detail }}</p>
          <div class="item-meta">
            <span>创建：{{ item.createdAt || '-' }}</span>
            <span v-if="item.deadlineAt">截止：{{ item.deadlineAt }}</span>
          </div>

          <div class="item-actions">
            <el-button text @click="jumpTo(item.jumpUrl)">跳转</el-button>
            <el-button text @click="toggleTimeout(item)">
              {{ item.manualTimeout ? '取消超时标记' : '超时标记' }}
            </el-button>
            <el-button text @click="toggleDone(item)">
              {{ item.manualDone ? '取消完成' : '标记完成' }}
            </el-button>
            <el-button
              type="primary"
              :loading="processingItemMap[item.id]"
              @click="processSingle(card, item)"
            >
              处理
            </el-button>
          </div>
        </article>
      </div>
      <el-empty v-else description="当前卡片暂无待办" />
    </section>
  </div>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { updateAnnouncement } from '@/api/announcements'
import { getAdminAiDailyBrief } from '@/api/ai'
import { batchApproveReservations } from '@/api/reservations'
import { updateRepairOrderStatus } from '@/api/repairs'
import { getTodoCenter, notifyMissingCourseTask, reviewLostFoundClaim } from '@/api/todo'
import { useAuthStore } from '@/stores/auth'
import { resolveAdminJumpUrl } from '@/utils/admin-links'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const briefLoading = ref(false)
const generatedAt = ref('')
const dailyBrief = ref({})
const cards = ref([])
const summary = ref({
  total: 0,
  timeoutTotal: 0,
  highPriorityTotal: 0
})

const sortBy = ref('priority')
const sortOrder = ref('desc')
const showDone = ref(false)
const selectedMap = ref({})
const markState = ref({
  timeout: {},
  done: {}
})
const processingCardMap = reactive({})
const processingItemMap = reactive({})

const storageKey = computed(() => `admin_todo_marks_${authStore.username || 'default'}`)

const displayCards = computed(() => {
  return safeArray(cards.value).map((card) => {
    const key = String(card?.key || '')
    const rows = enrichItems(card?.items || [])
    const visible = showDone.value ? rows : rows.filter((item) => !item.manualDone)
    const sorted = sortItems(visible)
    return {
      ...card,
      key,
      items: sorted,
      visibleCount: sorted.length
    }
  })
})

function safeArray(value) {
  return Array.isArray(value) ? value : []
}

function toInt(value, fallback = 0) {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? Math.round(numeric) : fallback
}

function toDateNumber(value) {
  const text = String(value || '').trim().replace(' ', 'T')
  const numeric = Date.parse(text)
  return Number.isFinite(numeric) ? numeric : 0
}

function nowTimeText() {
  const date = new Date()
  const pad = (value) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function priorityTagType(score) {
  const numeric = toInt(score, 0)
  if (numeric >= 90) return 'danger'
  if (numeric >= 75) return 'warning'
  if (numeric >= 60) return 'primary'
  return 'info'
}

function markKey(item) {
  return `${String(item?.category || '')}:${toInt(item?.entityId, 0)}`
}

function loadMarks() {
  try {
    const raw = localStorage.getItem(storageKey.value)
    if (!raw) return
    const parsed = JSON.parse(raw)
    markState.value = {
      timeout: parsed?.timeout && typeof parsed.timeout === 'object' ? parsed.timeout : {},
      done: parsed?.done && typeof parsed.done === 'object' ? parsed.done : {}
    }
  } catch (error) {
    markState.value = { timeout: {}, done: {} }
  }
}

function saveMarks() {
  localStorage.setItem(storageKey.value, JSON.stringify(markState.value))
}

function enrichItems(items) {
  return safeArray(items).map((item) => {
    const key = markKey(item)
    const manualTimeout = Boolean(markState.value.timeout[key])
    const manualDone = Boolean(markState.value.done[key])
    const basePriority = toInt(item?.priorityScore, 0)
    return {
      ...item,
      manualTimeout,
      manualDone,
      effectiveTimeout: Boolean(item?.timeout) || manualTimeout,
      effectivePriority: basePriority + (manualTimeout ? 8 : 0) - (manualDone ? 20 : 0)
    }
  })
}

function sortItems(items) {
  const rows = safeArray(items).slice()
  if (sortBy.value === 'priority') {
    rows.sort((a, b) => {
      if (a.effectivePriority !== b.effectivePriority) {
        return sortOrder.value === 'asc'
          ? a.effectivePriority - b.effectivePriority
          : b.effectivePriority - a.effectivePriority
      }
      return toDateNumber(a.deadlineAt || a.createdAt) - toDateNumber(b.deadlineAt || b.createdAt)
    })
    return rows
  }
  if (sortBy.value === 'deadline') {
    rows.sort((a, b) => (
      sortOrder.value === 'asc'
        ? toDateNumber(a.deadlineAt || a.createdAt) - toDateNumber(b.deadlineAt || b.createdAt)
        : toDateNumber(b.deadlineAt || b.createdAt) - toDateNumber(a.deadlineAt || a.createdAt)
    ))
    return rows
  }
  rows.sort((a, b) => (
    sortOrder.value === 'asc'
      ? toDateNumber(a.createdAt) - toDateNumber(b.createdAt)
      : toDateNumber(b.createdAt) - toDateNumber(a.createdAt)
  ))
  return rows
}

function cleanSelection() {
  const next = {}
  displayCards.value.forEach((card) => {
    const key = String(card.key || '')
    const validIds = new Set(safeArray(card.items).map((item) => toInt(item.entityId, 0)))
    next[key] = safeArray(selectedMap.value[key]).filter((id) => validIds.has(toInt(id, 0)))
  })
  selectedMap.value = next
}

function selectedCount(cardKey) {
  return safeArray(selectedMap.value[String(cardKey || '')]).length
}

function isSelected(cardKey, entityId) {
  const key = String(cardKey || '')
  const id = toInt(entityId, 0)
  return safeArray(selectedMap.value[key]).includes(id)
}

function toggleSelect(cardKey, entityId) {
  const key = String(cardKey || '')
  const id = toInt(entityId, 0)
  const current = safeArray(selectedMap.value[key]).slice()
  const index = current.indexOf(id)
  if (index >= 0) current.splice(index, 1)
  else current.push(id)
  selectedMap.value = {
    ...selectedMap.value,
    [key]: current
  }
}

function clearSelection(cardKey) {
  selectedMap.value = {
    ...selectedMap.value,
    [String(cardKey || '')]: []
  }
}

function isCardAllSelected(card) {
  const ids = safeArray(card?.items).map((item) => toInt(item.entityId, 0)).filter((id) => id > 0)
  if (!ids.length) return false
  const selected = new Set(safeArray(selectedMap.value[String(card?.key || '')]))
  return ids.every((id) => selected.has(id))
}

function toggleSelectAll(card) {
  const key = String(card?.key || '')
  const ids = safeArray(card?.items).map((item) => toInt(item.entityId, 0)).filter((id) => id > 0)
  if (!ids.length) return
  if (isCardAllSelected(card)) {
    clearSelection(key)
    return
  }
  selectedMap.value = {
    ...selectedMap.value,
    [key]: ids
  }
}

function resolveTargets(card) {
  const rows = safeArray(card?.items)
  const selected = new Set(safeArray(selectedMap.value[String(card?.key || '')]))
  const useSelected = selected.size > 0
  return rows.filter((item) => {
    const id = toInt(item.entityId, 0)
    if (id <= 0) return false
    return useSelected ? selected.has(id) : true
  })
}

function toggleTimeout(item) {
  const key = markKey(item)
  const timeoutMap = { ...markState.value.timeout }
  if (timeoutMap[key]) delete timeoutMap[key]
  else timeoutMap[key] = true
  markState.value = {
    ...markState.value,
    timeout: timeoutMap
  }
  saveMarks()
}

function toggleDone(item) {
  const key = markKey(item)
  const doneMap = { ...markState.value.done }
  if (doneMap[key]) delete doneMap[key]
  else doneMap[key] = true
  markState.value = {
    ...markState.value,
    done: doneMap
  }
  saveMarks()
}

function markTimeoutBatch(card, flag) {
  const rows = resolveTargets(card)
  if (!rows.length) {
    ElMessage.info('没有可操作项')
    return
  }
  const timeoutMap = { ...markState.value.timeout }
  rows.forEach((item) => {
    const key = markKey(item)
    if (flag) timeoutMap[key] = true
    else delete timeoutMap[key]
  })
  markState.value = {
    ...markState.value,
    timeout: timeoutMap
  }
  saveMarks()
}

function markDoneBatch(card, flag) {
  const rows = resolveTargets(card)
  if (!rows.length) {
    ElMessage.info('没有可操作项')
    return
  }
  const doneMap = { ...markState.value.done }
  rows.forEach((item) => {
    const key = markKey(item)
    if (flag) doneMap[key] = true
    else delete doneMap[key]
  })
  markState.value = {
    ...markState.value,
    done: doneMap
  }
  saveMarks()
}

function markProcessedDone(items) {
  const doneMap = { ...markState.value.done }
  safeArray(items).forEach((item) => {
    doneMap[markKey(item)] = true
  })
  markState.value = {
    ...markState.value,
    done: doneMap
  }
  saveMarks()
}

async function fetchAiBrief() {
  briefLoading.value = true
  try {
    const response = await getAdminAiDailyBrief()
    dailyBrief.value = response.data?.data || {}
  } finally {
    briefLoading.value = false
  }
}

async function fetchTodos() {
  loading.value = true
  try {
    const response = await getTodoCenter({
      sortBy: sortBy.value,
      sortOrder: sortOrder.value,
      limitPerCard: 60
    })
    const payload = response.data?.data || {}
    cards.value = safeArray(payload.cards)
    summary.value = payload.summary || { total: 0, timeoutTotal: 0, highPriorityTotal: 0 }
    generatedAt.value = String(payload.generatedAt || '')
    cleanSelection()
  } finally {
    loading.value = false
  }
}

function jumpTo(jumpUrl) {
  const target = resolveAdminJumpUrl(jumpUrl)
  if (!target) {
    ElMessage.info('当前没有可跳转的后台页面')
    return
  }
  router.push(target)
}

async function processItems(category, items) {
  const rows = safeArray(items)
  if (!rows.length) return { success: 0, failed: 0, processedEntityIds: [] }

  if (category === 'alarm_high_risk') {
    markProcessedDone(rows)
    return {
      success: rows.length,
      failed: 0,
      processedEntityIds: rows.map((item) => toInt(item.entityId, 0)).filter((id) => id > 0)
    }
  }

  if (category === 'reservation_pending') {
    const ids = rows.map((item) => toInt(item.entityId, 0)).filter((id) => id > 0)
    if (!ids.length) return { success: 0, failed: 0, processedEntityIds: [] }
    const response = await batchApproveReservations(ids)
    const data = response.data?.data || {}
    const approvedIds = safeArray(data.approvedIds).map((item) => toInt(item, 0)).filter((id) => id > 0)
    return {
      success: toInt(data.count, approvedIds.length),
      failed: Math.max(0, ids.length - toInt(data.count, approvedIds.length)),
      processedEntityIds: approvedIds
    }
  }

  if (category === 'repair_pending') {
    return processSequential(rows, async (item) => {
      await updateRepairOrderStatus(item.entityId, { status: 'accepted' })
      return toInt(item.entityId, 0)
    })
  }

  if (category === 'claim_pending') {
    return processSequential(rows, async (item) => {
      await reviewLostFoundClaim(item.entityId, {
        action: 'approve',
        note: 'todo center batch approve'
      })
      return toInt(item.entityId, 0)
    })
  }

  if (category === 'course_task_due') {
    return processSequential(rows, async (item) => {
      const courseId = toInt(item.courseId, 0)
      const taskId = toInt(item.taskId || item.entityId, 0)
      if (!courseId || !taskId) throw new Error('缺少课程或任务编号')
      await notifyMissingCourseTask(courseId, taskId)
      return taskId
    })
  }

  if (category === 'announcement_today_scheduled') {
    return processSequential(rows, async (item) => {
      await updateAnnouncement(item.entityId, {
        publishAt: nowTimeText()
      })
      return toInt(item.entityId, 0)
    })
  }

  return { success: 0, failed: rows.length, processedEntityIds: [] }
}

async function processSequential(rows, runner) {
  let success = 0
  let failed = 0
  const processedEntityIds = []
  for (const item of rows) {
    try {
      const entityId = await runner(item)
      if (entityId > 0) {
        success += 1
        processedEntityIds.push(entityId)
      }
    } catch (error) {
      failed += 1
    }
  }
  return { success, failed, processedEntityIds }
}

async function processCard(card) {
  const rows = resolveTargets(card)
  if (!rows.length) {
    ElMessage.info('没有可处理项')
    return
  }

  await ElMessageBox.confirm(`将处理 ${rows.length} 条待办，是否继续？`, '批量处理', {
    type: 'warning'
  })

  processingCardMap[card.key] = true
  try {
    const result = await processItems(card.key, rows)
    const processedSet = new Set(safeArray(result.processedEntityIds))
    if (processedSet.size > 0) {
      markProcessedDone(rows.filter((item) => processedSet.has(toInt(item.entityId, 0))))
    }
    clearSelection(card.key)
    ElMessage.success(`成功 ${result.success} 条，失败 ${result.failed} 条`)
    await fetchTodos()
  } finally {
    processingCardMap[card.key] = false
  }
}

async function processSingle(card, item) {
  processingItemMap[item.id] = true
  try {
    const result = await processItems(card.key, [item])
    if (safeArray(result.processedEntityIds).includes(toInt(item.entityId, 0))) {
      markProcessedDone([item])
    }
    ElMessage.success(result.failed > 0 ? `成功 ${result.success} 条，失败 ${result.failed} 条` : '处理成功')
    await fetchTodos()
  } finally {
    processingItemMap[item.id] = false
  }
}

watch(storageKey, () => {
  loadMarks()
})

onMounted(async () => {
  loadMarks()
  await Promise.all([fetchTodos(), fetchAiBrief()])
})
</script>

<style scoped lang="scss">
.todo-page {
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
    radial-gradient(circle at top right, rgba(15, 118, 110, 0.16), transparent 34%),
    linear-gradient(135deg, #fbfffe 0%, #eef8f6 100%);
}

.hero-copy,
.brief-list,
.item-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hero-card h2,
.panel-head h3 {
  margin: 0;
}

.hero-card p,
.hero-meta,
.metric-sub,
.metric-label,
.panel-head span,
.card-meta,
.detail-copy,
.item-meta,
.selected-text {
  color: var(--app-muted);
}

.hero-meta,
.focus-row,
.chip-row,
.item-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
}

.hero-actions,
.card-actions,
.item-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: var(--app-primary-soft);
  color: #115e59;
  font-size: 12px;
  font-weight: 700;
}

.metric-grid,
.panel-grid {
  display: grid;
  gap: 20px;
}

.metric-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.metric-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 24px;
}

.metric-value {
  font-size: 32px;
  line-height: 1;
}

.metric-value.warning {
  color: #b45309;
}

.metric-value.danger {
  color: #b42318;
}

.panel-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.panel-card {
  padding: 24px;
}

.panel-span-2 {
  grid-column: span 2;
}

.panel-head,
.item-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.brief-item,
.item-main {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.brief-dot {
  width: 8px;
  height: 8px;
  margin-top: 6px;
  border-radius: 50%;
  background: var(--app-primary);
}

.todo-card {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.item-list {
  gap: 14px;
}

.item-card {
  padding: 18px;
  background: #f8fafc;
}

.item-card strong {
  color: #0f172a;
}

.item-card p {
  margin: 0;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-copy {
  margin: 0;
  line-height: 1.7;
}

.loading-card {
  padding: 24px;
}

@media (max-width: 1280px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .panel-grid {
    grid-template-columns: 1fr;
  }

  .panel-span-2 {
    grid-column: span 1;
  }
}

@media (max-width: 768px) {
  .hero-card,
  .panel-head,
  .item-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .metric-grid {
    grid-template-columns: 1fr;
  }
}
</style>
