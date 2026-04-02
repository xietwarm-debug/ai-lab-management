<template>
  <div class="page-container todo-page">
    <!-- 顶部 Hero 区 (带入场动画) -->
    <section class="hero-card overview-section">
      <div class="hero-content">
        <div class="hero-copy">
          <span class="eyebrow">管理员工作台</span>
          <h1 class="page-title">待办中心</h1>
          <p class="page-desc">把预约审批、报修工单、认领审核和定时公告集中在一个页面里处理。</p>
          <div class="hero-meta">
            <span class="meta-item"><el-icon><Clock /></el-icon> 生成时间：{{ generatedAt || '-' }}</span>
            <span class="meta-item"><el-icon><MagicStick /></el-icon> AI 日报：{{ dailyBrief.generatedAt || '-' }}</span>
          </div>
        </div>
        <div class="hero-actions">
          <el-button :loading="loading" @click="fetchTodos" :icon="RefreshRight" class="hover-lift">刷新待办</el-button>
          <el-button type="primary" :loading="briefLoading" @click="fetchAiBrief" :icon="MagicStick" class="hover-lift">刷新日报</el-button>
        </div>
      </div>
      <!-- 装饰性背景元素 -->
      <div class="hero-decoration"></div>
    </section>

    <!-- 数据指标区 (交错入场动画) -->
    <section class="stats-grid metric-grid">
      <article class="stat-card is-primary">
        <div class="stat-info">
          <span class="stat-label">待办总量</span>
        </div>
        <strong class="stat-value">{{ summary.total || 0 }}</strong>
        <span class="stat-sub">所有卡片合计</span>
      </article>
      <article class="stat-card is-danger" :class="{ 'has-unread': summary.timeoutTotal > 0 }">
        <div class="stat-info">
          <span class="stat-label">超时总量</span>
          <span v-if="summary.timeoutTotal > 0" class="unread-badge">优先</span>
        </div>
        <strong class="stat-value text-danger">{{ summary.timeoutTotal || 0 }}</strong>
        <span class="stat-sub">建议优先处理</span>
      </article>
      <article class="stat-card is-warning">
        <div class="stat-info">
          <span class="stat-label">高优先级</span>
        </div>
        <strong class="stat-value text-warning">{{ summary.highPriorityTotal || 0 }}</strong>
        <span class="stat-sub">分值较高</span>
      </article>
      <article class="stat-card is-purple">
        <div class="stat-info">
          <span class="stat-label">AI 聚焦动作</span>
        </div>
        <strong class="stat-value text-purple">{{ dailyBrief.focusActions?.length || 0 }}</strong>
        <span class="stat-sub">日报给出的建议</span>
      </article>
    </section>

    <!-- AI 简报区 -->
    <section class="panel-card ai-panel panel-fade-in">
      <div class="panel-head">
        <div class="head-left">
          <el-icon class="head-icon text-purple"><MagicStick /></el-icon>
          <div>
            <h3>AI 每日简报</h3>
            <span class="sub-text">{{ dailyBrief.generatedAt || '暂无日报' }}</span>
          </div>
        </div>
        <el-button link type="primary" :loading="briefLoading" @click="fetchAiBrief" class="hover-btn">刷新简报</el-button>
      </div>
      
      <div class="ai-content">
        <p class="brief-copy">{{ dailyBrief.summaryText || '暂时还没有日报摘要。' }}</p>
        
        <div v-if="dailyBrief.highlights?.length" class="brief-list">
          <div v-for="(item, index) in dailyBrief.highlights" :key="index" class="brief-item">
            <span class="brief-dot"></span>
            <span>{{ item }}</span>
          </div>
        </div>
        <el-empty v-else description="暂无日报重点" :image-size="60" />

        <div v-if="dailyBrief.focusActions?.length" class="focus-row mt-4">
          <el-button
            v-for="(item, index) in dailyBrief.focusActions"
            :key="`${item.title}-${index}`"
            plain
            type="primary"
            size="small"
            class="action-pill hover-lift"
            @click="jumpTo(item.jumpUrl)"
          >
            {{ item.title || '查看建议动作' }}
            <el-icon class="ml-1"><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>
    </section>

    <!-- 控制栏 (排序与显示) -->
    <section class="control-bar panel-card panel-fade-in">
      <div class="filter-group">
        <div class="control-label">排序方式</div>
        <el-radio-group v-model="sortBy" size="large" class="custom-radio" @change="fetchTodos">
          <el-radio-button label="priority">按优先级</el-radio-button>
          <el-radio-button label="deadline">按截止时间</el-radio-button>
          <el-radio-button label="createdAt">按创建时间</el-radio-button>
        </el-radio-group>
        
        <el-divider direction="vertical" />
        
        <el-radio-group v-model="sortOrder" size="large" class="custom-radio light-radio" @change="fetchTodos">
          <el-radio-button label="desc">降序</el-radio-button>
          <el-radio-button label="asc">升序</el-radio-button>
        </el-radio-group>
      </div>
      
      <div class="switch-group">
        <span class="switch-label">显示已标记完成</span>
        <el-switch v-model="showDone" active-color="#3b82f6" />
      </div>
    </section>

    <!-- 加载骨架屏 -->
    <section v-if="loading" class="panel-card panel-fade-in">
      <el-skeleton :rows="4" animated />
    </section>

    <!-- 待办卡片列表 -->
    <template v-else>
      <section 
        v-for="card in displayCards" 
        :key="card.key" 
        class="todo-card panel-card panel-fade-in"
      >
        <div class="panel-head border-bottom">
          <div class="head-left">
            <div>
              <h3>{{ card.title }}</h3>
              <p class="card-meta">
                {{ card.description }} · 总量 {{ card.total || 0 }} · 超时 {{ card.timeoutCount || 0 }} · 当前展示 {{ card.visibleCount || 0 }}
              </p>
            </div>
          </div>
          <div class="card-actions">
            <el-button link type="info" @click="jumpTo(card.jumpUrl)" class="hover-btn">跳转页</el-button>
            <el-button link @click="toggleSelectAll(card)">
              {{ isCardAllSelected(card) ? '取消全选' : '全选当前卡片' }}
            </el-button>
            <el-button
              type="primary"
              plain
              :loading="processingCardMap[card.key]"
              :disabled="!selectedCount(card.key)"
              @click="processCard(card)"
              class="hover-lift"
            >
              批量处理
            </el-button>
          </div>
        </div>

        <div class="batch-bar chip-row">
          <div class="chip-actions">
            <el-button link size="small" @click="clearSelection(card.key)" :disabled="!selectedCount(card.key)">清空选择</el-button>
            <el-divider direction="vertical" />
            <el-button link size="small" @click="markTimeoutBatch(card, true)" :disabled="!selectedCount(card.key)">标记超时</el-button>
            <el-button link size="small" @click="markTimeoutBatch(card, false)" :disabled="!selectedCount(card.key)">取消超时</el-button>
            <el-divider direction="vertical" />
            <el-button link size="small" type="success" @click="markDoneBatch(card, true)" :disabled="!selectedCount(card.key)">标记完成</el-button>
            <el-button link size="small" @click="markDoneBatch(card, false)" :disabled="!selectedCount(card.key)">取消完成</el-button>
          </div>
          <span class="select-info">已选 <strong>{{ selectedCount(card.key) }}</strong> 项</span>
        </div>

        <!-- 使用 FLIP 动画的待办项列表 -->
        <transition-group name="list" tag="div" class="item-list" v-if="card.items.length">
          <article 
            v-for="item in card.items" 
            :key="item.id" 
            class="message-card item-card"
            :class="{ 'is-selected': isSelected(card.key, item.entityId), 'is-done': item.manualDone }"
          >
            <div class="card-left">
              <el-checkbox
                class="msg-checkbox"
                :model-value="isSelected(card.key, item.entityId)"
                @change="toggleSelect(card.key, item.entityId)"
              />
              <div class="msg-content">
                <div class="msg-header">
                  <h3 class="msg-title">{{ item.title }}</h3>
                  
                  <div class="tag-row">
                    <el-tag size="small" effect="light" class="custom-tag" :type="priorityTagType(item.effectivePriority)">
                      {{ item.priorityLevel || '普通' }}
                    </el-tag>
                    <el-tag v-if="item.effectiveTimeout" size="small" effect="light" type="danger" class="custom-tag">超时</el-tag>
                    <el-tag v-if="item.manualDone" size="small" effect="light" type="success" class="custom-tag">已完成</el-tag>
                  </div>
                </div>
                <p class="msg-desc">{{ item.subtitle || '-' }}</p>
                <p v-if="item.detail" class="msg-detail">{{ item.detail }}</p>
              </div>
            </div>

            <div class="card-right">
              <div class="item-meta-col">
                <span class="time-text">创建: {{ item.createdAt || '-' }}</span>
                <span v-if="item.deadlineAt" class="time-text text-danger">截止: {{ item.deadlineAt }}</span>
              </div>
              
              <div class="msg-actions">
                <el-button link type="info" class="hover-btn" @click="jumpTo(item.jumpUrl)">跳转</el-button>
                <el-button link :type="item.manualTimeout ? 'info' : 'warning'" class="hover-btn" @click="toggleTimeout(item)">
                  {{ item.manualTimeout ? '取消超时' : '标超时' }}
                </el-button>
                <el-button link :type="item.manualDone ? 'info' : 'success'" class="hover-btn" @click="toggleDone(item)">
                  {{ item.manualDone ? '取消完成' : '标完成' }}
                </el-button>
                <el-button
                  type="primary"
                  link
                  class="action-btn hover-btn"
                  :loading="processingItemMap[item.id]"
                  @click="processSingle(card, item)"
                >
                  处理
                </el-button>
              </div>
            </div>
          </article>
        </transition-group>
        <el-empty v-else description="当前卡片暂无待办" :image-size="80" />
      </section>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { Clock, MagicStick, RefreshRight, ArrowRight } from '@element-plus/icons-vue'

// 假设的 API 和 Store 导入 (与原代码保持一致)
import { updateAnnouncement } from '@/api/announcements'
import { getAdminAiDailyBrief } from '@/api/ai'
import { batchApproveReservations } from '@/api/reservations'
import { updateRepairOrderStatus } from '@/api/repairs'
import { getTodoCenter, reviewLostFoundClaim } from '@/api/todo'
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
  return safeArray(cards.value)
    .filter((card) => card.key !== 'course_task_due')
    .map((card) => {
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

// --- 保持所有的业务逻辑与数据处理函数不变 ---
function safeArray(value) { return Array.isArray(value) ? value : [] }
function toInt(value, fallback = 0) { const numeric = Number(value); return Number.isFinite(numeric) ? Math.round(numeric) : fallback }
function toDateNumber(value) { const text = String(value || '').trim().replace(' ', 'T'); const numeric = Date.parse(text); return Number.isFinite(numeric) ? numeric : 0 }
function nowTimeText() { const date = new Date(); const pad = (value) => String(value).padStart(2, '0'); return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}` }

function priorityTagType(score) {
  const numeric = toInt(score, 0)
  if (numeric >= 90) return 'danger'
  if (numeric >= 75) return 'warning'
  if (numeric >= 60) return 'primary'
  return 'info'
}

function markKey(item) { return `${String(item?.category || '')}:${toInt(item?.entityId, 0)}` }

function loadMarks() {
  try {
    const raw = localStorage.getItem(storageKey.value)
    if (!raw) return
    const parsed = JSON.parse(raw)
    markState.value = {
      timeout: parsed?.timeout && typeof parsed.timeout === 'object' ? parsed.timeout : {},
      done: parsed?.done && typeof parsed.done === 'object' ? parsed.done : {}
    }
  } catch (error) { markState.value = { timeout: {}, done: {} } }
}

function saveMarks() { localStorage.setItem(storageKey.value, JSON.stringify(markState.value)) }

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
        return sortOrder.value === 'asc' ? a.effectivePriority - b.effectivePriority : b.effectivePriority - a.effectivePriority
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

function selectedCount(cardKey) { return safeArray(selectedMap.value[String(cardKey || '')]).length }
function isSelected(cardKey, entityId) { return safeArray(selectedMap.value[String(cardKey || '')]).includes(toInt(entityId, 0)) }

function toggleSelect(cardKey, entityId) {
  const key = String(cardKey || '')
  const id = toInt(entityId, 0)
  const current = safeArray(selectedMap.value[key]).slice()
  const index = current.indexOf(id)
  if (index >= 0) current.splice(index, 1)
  else current.push(id)
  selectedMap.value = { ...selectedMap.value, [key]: current }
}

function clearSelection(cardKey) { selectedMap.value = { ...selectedMap.value, [String(cardKey || '')]: [] } }

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
  if (isCardAllSelected(card)) { clearSelection(key); return }
  selectedMap.value = { ...selectedMap.value, [key]: ids }
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
  markState.value = { ...markState.value, timeout: timeoutMap }
  saveMarks()
}

function toggleDone(item) {
  const key = markKey(item)
  const doneMap = { ...markState.value.done }
  if (doneMap[key]) delete doneMap[key]
  else doneMap[key] = true
  markState.value = { ...markState.value, done: doneMap }
  saveMarks()
}

function markTimeoutBatch(card, flag) {
  const rows = resolveTargets(card)
  if (!rows.length) { ElMessage.info('没有可操作项'); return }
  const timeoutMap = { ...markState.value.timeout }
  rows.forEach((item) => {
    const key = markKey(item)
    if (flag) timeoutMap[key] = true; else delete timeoutMap[key]
  })
  markState.value = { ...markState.value, timeout: timeoutMap }
  saveMarks()
}

function markDoneBatch(card, flag) {
  const rows = resolveTargets(card)
  if (!rows.length) { ElMessage.info('没有可操作项'); return }
  const doneMap = { ...markState.value.done }
  rows.forEach((item) => {
    const key = markKey(item)
    if (flag) doneMap[key] = true; else delete doneMap[key]
  })
  markState.value = { ...markState.value, done: doneMap }
  saveMarks()
}

function markProcessedDone(items) {
  const doneMap = { ...markState.value.done }
  safeArray(items).forEach((item) => { doneMap[markKey(item)] = true })
  markState.value = { ...markState.value, done: doneMap }
  saveMarks()
}

async function fetchAiBrief() {
  briefLoading.value = true
  try {
    const response = await getAdminAiDailyBrief()
    dailyBrief.value = response.data?.data || {}
  } catch(e) {} finally { briefLoading.value = false }
}

async function fetchTodos() {
  loading.value = true
  try {
    const response = await getTodoCenter({ sortBy: sortBy.value, sortOrder: sortOrder.value, limitPerCard: 60 })
    const payload = response.data?.data || {}
    cards.value = safeArray(payload.cards)
    summary.value = payload.summary || { total: 0, timeoutTotal: 0, highPriorityTotal: 0 }
    generatedAt.value = String(payload.generatedAt || '')
    cleanSelection()
  } catch(e) {} finally { loading.value = false }
}

function jumpTo(jumpUrl) {
  const target = resolveAdminJumpUrl(jumpUrl)
  if (!target) { ElMessage.info('当前没有可跳转的后台页面'); return }
  router.push(target)
}

async function processItems(category, items) {
  const rows = safeArray(items)
  if (!rows.length) return { success: 0, failed: 0, processedEntityIds: [] }

  if (category === 'alarm_high_risk') {
    markProcessedDone(rows)
    return { success: rows.length, failed: 0, processedEntityIds: rows.map((item) => toInt(item.entityId, 0)).filter((id) => id > 0) }
  }

  if (category === 'reservation_pending') {
    const ids = rows.map((item) => toInt(item.entityId, 0)).filter((id) => id > 0)
    if (!ids.length) return { success: 0, failed: 0, processedEntityIds: [] }
    const response = await batchApproveReservations(ids)
    const data = response.data?.data || {}
    const approvedIds = safeArray(data.approvedIds).map((item) => toInt(item, 0)).filter((id) => id > 0)
    return { success: toInt(data.count, approvedIds.length), failed: Math.max(0, ids.length - toInt(data.count, approvedIds.length)), processedEntityIds: approvedIds }
  }

  if (category === 'repair_pending') {
    return processSequential(rows, async (item) => { await updateRepairOrderStatus(item.entityId, { status: 'accepted' }); return toInt(item.entityId, 0) })
  }

  if (category === 'claim_pending') {
    return processSequential(rows, async (item) => { await reviewLostFoundClaim(item.entityId, { action: 'approve', note: 'todo batch approve' }); return toInt(item.entityId, 0) })
  }
  if (category === 'announcement_today_scheduled') {
    return processSequential(rows, async (item) => { await updateAnnouncement(item.entityId, { publishAt: nowTimeText() }); return toInt(item.entityId, 0) })
  }

  return { success: 0, failed: rows.length, processedEntityIds: [] }
}

async function processSequential(rows, runner) {
  let success = 0, failed = 0; const processedEntityIds = []
  for (const item of rows) {
    try { const entityId = await runner(item); if (entityId > 0) { success += 1; processedEntityIds.push(entityId) } } 
    catch (error) { failed += 1 }
  }
  return { success, failed, processedEntityIds }
}

async function processCard(card) {
  const rows = resolveTargets(card)
  if (!rows.length) { ElMessage.info('没有可处理项'); return }
  await ElMessageBox.confirm(`将处理 ${rows.length} 条待办，是否继续？`, '批量处理', { type: 'warning' })
  processingCardMap[card.key] = true
  try {
    const result = await processItems(card.key, rows)
    const processedSet = new Set(safeArray(result.processedEntityIds))
    if (processedSet.size > 0) { markProcessedDone(rows.filter((item) => processedSet.has(toInt(item.entityId, 0)))) }
    clearSelection(card.key)
    ElMessage.success(`成功 ${result.success} 条，失败 ${result.failed} 条`)
    await fetchTodos()
  } finally { processingCardMap[card.key] = false }
}

async function processSingle(card, item) {
  processingItemMap[item.id] = true
  try {
    const result = await processItems(card.key, [item])
    if (safeArray(result.processedEntityIds).includes(toInt(item.entityId, 0))) { markProcessedDone([item]) }
    ElMessage.success(result.failed > 0 ? `成功 ${result.success} 条，失败 ${result.failed} 条` : '处理成功')
    await fetchTodos()
  } finally { processingItemMap[item.id] = false }
}

watch(storageKey, () => { loadMarks() })

onMounted(async () => {
  loadMarks()
  await Promise.all([fetchTodos(), fetchAiBrief()])
})
</script>

<style scoped lang="scss">
// 统一的学术极简设计变量
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
$purple: #8b5cf6; // 专属 AI 色
$radius-lg: 16px;
$radius-md: 8px;
$shadow-soft: 0 10px 30px rgba(0, 0, 0, 0.03);
$shadow-hover: 0 15px 35px rgba(59, 130, 246, 0.06);

// --- 动画 Keyframes ---
@keyframes fadeSlideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.page-container {
  padding: 32px;
  background-color: $bg-color;
  min-height: 100vh;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

// 文本颜色工具
.text-danger { color: $danger !important; }
.text-warning { color: $warning !important; }
.text-purple { color: $purple !important; }
.mt-4 { margin-top: 16px; }
.ml-1 { margin-left: 4px; }

/* --- 通用面板卡片 (悬浮美学) --- */
.panel-card {
  background: $card-bg;
  border-radius: $radius-lg;
  padding: 24px;
  box-shadow: $shadow-soft;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  border: 1px solid transparent;

  &:hover { box-shadow: $shadow-hover; border-color: rgba(59, 130, 246, 0.05); }
}

// 动画交错控制
.overview-section { animation: fadeSlideUp 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both; }
.metric-grid { animation: fadeSlideUp 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) 0.05s both; }
.panel-fade-in {
  animation: fadeSlideUp 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both;
  &:nth-child(n) { animation-delay: 0.1s; }
  &:nth-child(n+4) { animation-delay: 0.15s; }
  &:nth-child(n+5) { animation-delay: 0.2s; }
}

/* --- Hero 区域 --- */
.hero-card {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding: 32px;
  background: #ffffff;
  border-radius: $radius-lg;
  box-shadow: $shadow-soft;
  overflow: hidden;

  .hero-decoration {
    position: absolute;
    right: 0;
    top: 0;
    width: 300px;
    height: 100%;
    background: radial-gradient(circle at top right, rgba(59, 130, 246, 0.08), transparent 70%);
    pointer-events: none;
  }

  .hero-content {
    position: relative;
    z-index: 1;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    width: 100%;
    flex-wrap: wrap;
    gap: 24px;
  }

  .eyebrow {
    display: inline-block;
    color: $primary;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.08em;
    margin-bottom: 12px;
    background: #eff6ff;
    padding: 4px 12px;
    border-radius: 20px;
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
    margin: 0 0 16px 0;
  }

  .hero-meta {
    display: flex;
    gap: 16px;
    color: $text-light;
    font-size: 13px;
    
    .meta-item { display: flex; align-items: center; gap: 4px; }
  }

  .hero-actions { display: flex; gap: 12px; }
}

/* --- 指标卡片 (带彩色指示条) --- */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.stat-card {
  background: $card-bg;
  border-radius: $radius-lg;
  padding: 20px 24px;
  box-shadow: $shadow-soft;
  position: relative;
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;

  // 使用 SCSS 循环为指标卡片添加交错延迟
  @for $i from 1 through 4 {
    &:nth-child(#{$i}) { animation: fadeSlideUp 0.5s cubic-bezier(0.2, 0.8, 0.2, 1) #{$i * 0.05}s both; }
  }

  &::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0; width: 4px;
    opacity: 0.8;
  }

  &.is-primary::before { background-color: $primary; }
  &.is-danger::before { background-color: $danger; }
  &.is-warning::before { background-color: $warning; }
  &.is-purple::before { background-color: $purple; }

  &:hover { transform: translateY(-2px); box-shadow: $shadow-hover; }

  .stat-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    
    .stat-label { font-size: 14px; color: $text-regular; font-weight: 500; }
    .unread-badge { font-size: 12px; padding: 2px 8px; border-radius: 12px; background: #fef2f2; color: $danger; }
  }

  .stat-value { font-size: 32px; font-weight: 700; color: $text-main; line-height: 1; font-family: 'Inter', sans-serif; display: block; margin-bottom: 8px;}
  .stat-sub { color: $text-light; font-size: 13px; }
}

/* --- 面板头部通用 --- */
.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  
  &.border-bottom { padding-bottom: 16px; border-bottom: 1px solid $border-color; margin-bottom: 16px; }

  .head-left {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .head-icon { font-size: 24px; }
    h3 { font-size: 18px; font-weight: 600; color: $text-main; margin: 0 0 4px 0; }
    .sub-text, .card-meta { font-size: 13px; color: $text-light; margin: 0; }
  }
}

/* --- AI 简报区 --- */
.ai-panel {
  .brief-copy { color: $text-main; line-height: 1.6; margin: 0 0 16px 0; font-size: 14px; }
  
  .brief-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    background: #f8fafc;
    padding: 16px;
    border-radius: $radius-md;
    border: 1px dashed rgba(139, 92, 246, 0.3); // 浅紫色虚线框
  }

  .brief-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    color: $text-regular;
    font-size: 14px;
    line-height: 1.5;

    .brief-dot {
      width: 6px; height: 6px; border-radius: 50%;
      background: $purple; margin-top: 8px; flex-shrink: 0;
    }
  }

  .action-pill { border-radius: 20px; }
}

/* --- 控制栏 (排序与显示) --- */
.control-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  padding: 16px 24px;
  background:
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.1), transparent 35%),
    $card-bg;
  border: 1px solid rgba(59, 130, 246, 0.08);

  .control-label, .switch-label { font-size: 14px; color: $text-regular; font-weight: 500; }
  
  .filter-group, .switch-group { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
}

// 药丸风格 Radio
:deep(.custom-radio) {
  .el-radio-button__inner {
    border: none !important; background: transparent; color: $text-regular; font-weight: 500;
    border-radius: 6px !important; padding: 6px 16px; box-shadow: none !important;
  }
  .el-radio-button__original-radio:checked + .el-radio-button__inner { background-color: #eff6ff; color: $primary; box-shadow: none !important; }
  &.light-radio .el-radio-button__original-radio:checked + .el-radio-button__inner { background-color: #f1f5f9; color: $text-main; }
}

/* --- 待办卡片内部 --- */
.todo-card {
  transition: transform 0.2s ease, box-shadow 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: $shadow-hover;
  }

  .batch-bar {
    display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;
    background: #f8fafc; padding: 8px 16px; border-radius: $radius-md;
    
    .chip-actions { display: flex; align-items: center; gap: 8px; }
    .select-info { font-size: 13px; color: $text-regular; strong { color: $primary; } }
  }

  .item-list { display: flex; flex-direction: column; gap: 12px; position: relative; }
}

/* --- 具体待办项 (复刻消息列表样式) --- */
.message-card {
  background: $card-bg; border-radius: $radius-md; padding: 20px 24px;
  display: flex; justify-content: space-between; align-items: flex-start;
  box-shadow: 0 2px 12px rgba(0,0,0,0.02); transition: all 0.2s ease;
  border: 1px solid $border-color;

  &:hover {
    border-color: rgba(59, 130, 246, 0.2); box-shadow: $shadow-hover;
    .hover-btn { opacity: 1; visibility: visible; }
  }

  &.is-selected { border-color: rgba(59, 130, 246, 0.4); background-color: #f8fafc; }
  &.is-done {
    opacity: 0.6; background: #f8fafc; border-color: transparent;
    .msg-title { text-decoration: line-through; color: $text-light; }
  }

  .card-left { display: flex; gap: 16px; flex: 1; }
  .msg-checkbox { margin-top: 2px; }
  .msg-content { flex: 1; }

  .msg-header {
    display: flex; align-items: center; gap: 12px; margin-bottom: 8px; flex-wrap: wrap;
    .msg-title { font-size: 16px; font-weight: 600; color: $text-main; margin: 0; }
    .tag-row { display: flex; gap: 8px; }
  }

  .msg-desc { color: $text-regular; font-size: 14px; margin: 0 0 6px 0; }
  .msg-detail { color: $text-light; font-size: 13px; margin: 0; line-height: 1.5; }

  .card-right {
    display: flex; flex-direction: column; align-items: flex-end; justify-content: space-between;
    gap: 16px; min-width: 220px; height: 100%;

    .item-meta-col { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
    .time-text { font-size: 12px; color: $text-light; }

    .msg-actions {
      display: flex; gap: 8px; align-items: center;
      .hover-btn { opacity: 0; visibility: hidden; transition: all 0.2s; }
      .action-btn { opacity: 1; visibility: visible; } // 核心处理按钮常驻
    }
  }
}

:deep(.custom-tag) {
  border-radius: 6px; font-weight: 500; border: none;
  &.el-tag--danger { background-color: #fef2f2; color: $danger; }
  &.el-tag--warning { background-color: #fffbeb; color: $warning; }
  &.el-tag--success { background-color: #ecfdf5; color: $success; }
}

/* --- Vue Transition Group 丝滑过渡动画 (FLIP) --- */
.list-move, .list-enter-active, .list-leave-active { transition: all 0.4s cubic-bezier(0.2, 0.8, 0.2, 1); }
.list-enter-from, .list-leave-to { opacity: 0; transform: translateY(20px) scale(0.98); }
.list-leave-active { position: absolute; left: 0; right: 0; z-index: 0; }

// 交互微动效
.hover-lift { transition: transform 0.2s ease; &:hover { transform: translateY(-1px); } }

/* --- 响应式 --- */
@media (max-width: 1024px) {
  .hero-content { flex-direction: column; align-items: flex-start; }
  .message-card {
    flex-direction: column;
    .card-right { width: 100%; align-items: flex-start; margin-top: 16px; padding-left: 30px; flex-direction: row; justify-content: space-between; .hover-btn { opacity: 1; visibility: visible; } }
  }
}
</style>
