<template>
  <div class="ai-page">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="hero-badge">Admin Only</span>
        <h2>AI 助手工作台</h2>
        <p>把后台已有的 AI 能力集中到一个入口，方便做每日速览、数据问答、风险研判和管理问答。</p>
        <div class="hero-meta">
          <span>日报时间：{{ dailyBrief.generatedAt || '-' }}</span>
          <span>风险等级：{{ riskLevelText }}</span>
        </div>
      </div>
      <div class="hero-actions">
        <el-button :loading="pageLoading" @click="reloadAll">刷新全部</el-button>
      </div>
    </section>

    <section class="summary-grid">
      <article class="summary-card">
        <span class="summary-label">今日速览</span>
        <strong class="summary-value">{{ dailyBrief.highlights?.length || 0 }}</strong>
        <span class="summary-sub">重点摘要条数</span>
      </article>
      <article class="summary-card">
        <span class="summary-label">风险提醒</span>
        <strong class="summary-value">{{ riskAlerts.length }}</strong>
        <span class="summary-sub">按风险分数排序</span>
      </article>
      <article class="summary-card">
        <span class="summary-label">设备健康</span>
        <strong class="summary-value">{{ equipmentHealth.length }}</strong>
        <span class="summary-sub">预测样本设备数</span>
      </article>
      <article class="summary-card">
        <span class="summary-label">对话消息</span>
        <strong class="summary-value">{{ messages.length }}</strong>
        <span class="summary-sub">当前会话历史条数</span>
      </article>
    </section>

    <section class="content-grid">
      <article class="panel-card panel-span-2">
        <div class="panel-head">
          <div>
            <h3>管理问答</h3>
            <span>复用 `/agent/chat` 与 `/agent/history`</span>
          </div>
          <div class="panel-actions">
            <el-button text @click="loadHistory">刷新记录</el-button>
            <el-popconfirm title="确认清空当前会话历史？" @confirm="handleClearHistory">
              <template #reference>
                <el-button text type="danger">清空历史</el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>

        <div class="prompt-list">
          <el-button
            v-for="prompt in quickPrompts"
            :key="prompt"
            class="prompt-item"
            @click="usePrompt(prompt)"
          >
            {{ prompt }}
          </el-button>
        </div>

        <div class="chat-box">
          <div v-if="messages.length" class="message-list">
            <div
              v-for="item in messages"
              :key="item.id"
              class="message-item"
              :class="`message-item--${item.role}`"
            >
              <div class="message-meta">
                <strong>{{ item.role === 'user' ? '我' : 'AI 助手' }}</strong>
                <span>{{ item.createdAt || '-' }}</span>
              </div>
              <p>{{ item.text }}</p>
              <div v-if="item.action || item.sources?.length" class="message-extra">
                <el-tag v-if="item.action" size="small" type="info">{{ item.action }}</el-tag>
                <div v-if="item.sources?.length" class="source-list">
                  <el-link
                    v-for="(source, index) in item.sources"
                    :key="`${item.id}-${index}`"
                    type="primary"
                    :href="source.url"
                    target="_blank"
                  >
                    {{ source.title || source.url }}
                  </el-link>
                </div>
              </div>
            </div>
          </div>
          <el-empty v-else description="还没有对话记录，可以从下方快捷提问开始。" />
        </div>

        <div class="composer">
          <el-input
            v-model="chatInput"
            type="textarea"
            :rows="3"
            maxlength="200"
            show-word-limit
            resize="none"
            placeholder="例如：请总结今天后台最值得优先处理的事项"
            @keyup.ctrl.enter="submitChat"
          />
          <div class="composer-actions">
            <span>快捷发送：Ctrl + Enter</span>
            <el-button type="primary" :loading="chatLoading" @click="submitChat">发送</el-button>
          </div>
        </div>
      </article>

      <article class="panel-card">
        <div class="panel-head">
          <div>
            <h3>AI 每日简报</h3>
            <span>复用 `/admin/ai/daily-brief`</span>
          </div>
        </div>
        <p class="brief-text">{{ dailyBrief.summaryText || '暂无日报摘要。' }}</p>
        <div v-if="dailyBrief.highlights?.length" class="simple-list">
          <div v-for="(item, index) in dailyBrief.highlights" :key="index" class="simple-item">
            <span class="dot" />
            <span>{{ item }}</span>
          </div>
        </div>
        <el-empty v-else description="暂无重点摘要" />
        <div v-if="dailyBrief.focusActions?.length" class="action-list">
          <el-button
            v-for="(item, index) in dailyBrief.focusActions"
            :key="`${item.title}-${index}`"
            text
            type="primary"
            @click="jumpFromBackend(item.jumpUrl)"
          >
            {{ item.title || '未命名待办' }}
          </el-button>
        </div>
      </article>

      <article class="panel-card">
        <div class="panel-head">
          <div>
            <h3>数据问答</h3>
            <span>复用 `/admin/stats/ai-query`</span>
          </div>
          <el-button text :loading="queryLoading" @click="submitAiQuery">提问</el-button>
        </div>
        <el-input
          v-model="statsQuestion"
          placeholder="例如：当前待审批预约有多少？"
          maxlength="100"
          @keyup.enter="submitAiQuery"
        />
        <div class="query-result">
          <div class="query-meta">
            <el-tag size="small">{{ statsAnswer.intent || 'summary' }}</el-tag>
            <el-tag size="small" :type="statsAnswer.matched ? 'success' : 'info'">
              {{ statsAnswer.matched ? '已命中规则问法' : '通用摘要回答' }}
            </el-tag>
          </div>
          <p>{{ statsAnswer.answer || '输入问题后，AI 会基于后台统计快照返回简短回答。' }}</p>
        </div>
      </article>

      <article class="panel-card">
        <div class="panel-head">
          <div>
            <h3>风险提醒</h3>
            <span>复用 `/admin/ai/risk-alerts`</span>
          </div>
        </div>
        <div v-if="riskAlerts.length" class="alert-list">
          <div v-for="(item, index) in riskAlerts" :key="`${item.title}-${index}`" class="alert-item">
            <div class="alert-title">
              <strong>{{ item.title || '未命名提醒' }}</strong>
              <el-tag size="small" :type="riskTagType(item.level)">{{ riskLevelLabel(item.level) }}</el-tag>
            </div>
            <p>{{ item.description || '-' }}</p>
            <div class="alert-footer">
              <span>风险分：{{ item.score ?? '-' }}</span>
              <el-button v-if="normalizeJumpUrl(item.jumpUrl)" text type="primary" @click="jumpFromBackend(item.jumpUrl)">
                查看相关页面
              </el-button>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无风险提醒" />
      </article>

      <article class="panel-card panel-span-2">
        <div class="panel-head">
          <div>
            <h3>设备健康预测</h3>
            <span>复用 `/admin/ai/equipment-health`</span>
          </div>
          <div class="panel-actions">
            <el-button text :loading="equipmentLoading" @click="fetchEquipmentHealth">刷新列表</el-button>
            <el-button type="primary" plain :loading="equipmentRefreshing" @click="refreshEquipmentPrediction">
              刷新预测
            </el-button>
          </div>
        </div>
        <el-table :data="equipmentHealth" empty-text="暂无设备健康预测数据" stripe>
          <el-table-column prop="name" label="设备名称" min-width="180" />
          <el-table-column prop="assetCode" label="资产编号" min-width="160" />
          <el-table-column prop="labName" label="所属实验室" min-width="160" />
          <el-table-column label="风险等级" min-width="120">
            <template #default="{ row }">
              <el-tag size="small" :type="riskTagType(row.riskLevel)">{{ riskLevelLabel(row.riskLevel) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="失败概率" min-width="120">
            <template #default="{ row }">
              {{ formatPercent(row.failureProbability) }}
            </template>
          </el-table-column>
          <el-table-column label="风险分" min-width="100">
            <template #default="{ row }">
              {{ formatScore(row.riskScore) }}
            </template>
          </el-table-column>
          <el-table-column label="诊断依据" min-width="280">
            <template #default="{ row }">
              {{ Array.isArray(row.reasonLines) && row.reasonLines.length ? row.reasonLines.join('；') : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="recommendation" label="建议" min-width="220" />
        </el-table>
      </article>
    </section>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import {
  chatWithAgent,
  clearAgentHistory,
  getAdminAiDailyBrief,
  getAdminAiEquipmentHealth,
  getAdminAiRiskAlerts,
  getAgentHistory,
  queryAdminStatsAi,
  refreshAdminAiEquipmentHealth
} from '@/api/ai'

const router = useRouter()

const pageLoading = ref(false)
const queryLoading = ref(false)
const chatLoading = ref(false)
const equipmentLoading = ref(false)
const equipmentRefreshing = ref(false)

const dailyBrief = ref({})
const riskAlerts = ref([])
const equipmentHealth = ref([])
const messages = ref([])
const statsQuestion = ref('当前待审批预约有多少？')
const statsAnswer = ref({})
const chatInput = ref('')

const quickPrompts = [
  '请总结今天后台最值得优先处理的事项',
  '当前待审批预约有多少？',
  '最近 24 小时有哪些风险提醒？',
  '有哪些设备故障风险较高？'
]

const riskLevelText = computed(() => riskLevelLabel(dailyBrief.value.riskLevel))

function riskTagType(level) {
  const normalized = String(level || '').trim().toLowerCase()
  if (normalized === 'high') return 'danger'
  if (normalized === 'medium') return 'warning'
  return 'success'
}

function riskLevelLabel(level) {
  const normalized = String(level || '').trim().toLowerCase()
  if (normalized === 'high') return '高'
  if (normalized === 'medium') return '中'
  return '低'
}

function formatPercent(value) {
  const numeric = Number(value || 0)
  return `${(numeric * 100).toFixed(1)}%`
}

function formatScore(value) {
  const numeric = Number(value || 0)
  return Number.isFinite(numeric) ? numeric.toFixed(1) : '-'
}

function normalizeJumpUrl(jumpUrl) {
  const raw = String(jumpUrl || '').trim()
  if (!raw) return ''
  if (raw.startsWith('/pages/admin/approve')) return '/reservations'
  if (raw.startsWith('/pages/admin/equipments')) return '/equipments'
  if (raw.startsWith('/pages/admin/users')) return '/users'
  if (raw.startsWith('/pages/admin/stats')) return '/ai-assistant'
  if (raw.startsWith('/pages/admin/labs')) return '/equipments'
  if (raw.startsWith('/dashboard') || raw.startsWith('/reservations') || raw.startsWith('/equipments') || raw.startsWith('/users') || raw.startsWith('/reports')) {
    return raw
  }
  return ''
}

function jumpFromBackend(jumpUrl) {
  const target = normalizeJumpUrl(jumpUrl)
  if (!target) {
    ElMessage.info('当前建议没有可跳转的后台页面')
    return
  }
  router.push(target)
}

function normalizeMessage(row, index) {
  const meta = row?.meta && typeof row.meta === 'object' ? row.meta : {}
  const rawSources = Array.isArray(meta.sources) ? meta.sources : []
  return {
    id: row?.id || `${row?.role || 'message'}-${row?.createdAt || index}`,
    role: String(row?.role || '').trim() === 'user' ? 'user' : 'assistant',
    text: String(row?.text || '').trim(),
    action: String(row?.action || '').trim(),
    createdAt: String(row?.createdAt || '').trim(),
    sources: rawSources
      .map((item) => ({
        title: String(item?.title || '').trim(),
        url: String(item?.url || '').trim(),
        publishedDate: String(item?.publishedDate || item?.published_date || '').trim()
      }))
      .filter((item) => item.title || item.url)
  }
}

async function fetchDailyBrief() {
  const response = await getAdminAiDailyBrief()
  dailyBrief.value = response.data?.data || {}
}

async function fetchRiskAlerts() {
  const response = await getAdminAiRiskAlerts()
  const alerts = response.data?.data?.alerts
  riskAlerts.value = Array.isArray(alerts) ? alerts : []
}

async function fetchEquipmentHealth() {
  equipmentLoading.value = true
  try {
    const response = await getAdminAiEquipmentHealth({ limit: 8 })
    const items = response.data?.data?.items
    equipmentHealth.value = Array.isArray(items) ? items : []
  } finally {
    equipmentLoading.value = false
  }
}

async function loadHistory() {
  const response = await getAgentHistory({ limit: 120 })
  const rows = response.data?.data?.messages
  messages.value = Array.isArray(rows)
    ? rows.map((item, index) => normalizeMessage(item, index)).filter((item) => item.text)
    : []
}

async function submitAiQuery() {
  const question = String(statsQuestion.value || '').trim()
  if (!question) {
    ElMessage.warning('请先输入要提问的问题')
    return
  }
  queryLoading.value = true
  try {
    const response = await queryAdminStatsAi({ question })
    statsAnswer.value = response.data?.data || {}
  } finally {
    queryLoading.value = false
  }
}

function usePrompt(prompt) {
  chatInput.value = prompt
  submitChat()
}

async function submitChat() {
  const text = String(chatInput.value || '').trim()
  if (!text) {
    ElMessage.warning('请先输入问题')
    return
  }
  chatLoading.value = true
  try {
    messages.value.push({
      id: `pending-user-${Date.now()}`,
      role: 'user',
      text,
      action: '',
      createdAt: new Date().toLocaleString(),
      sources: []
    })
    chatInput.value = ''
    const response = await chatWithAgent({ text })
    const payload = response.data || {}
    const data = payload.data || {}
    if (Number(payload.code || 0) !== 0) {
      messages.value.push({
        id: `error-${Date.now()}`,
        role: 'assistant',
        text: String(data.reply || payload.msg || '请求失败').trim(),
        action: String(data.action || 'error').trim(),
        createdAt: new Date().toLocaleString(),
        sources: []
      })
      return
    }

    messages.value.push({
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      text: String(data.reply || '已处理完成。').trim(),
      action: String(data.action || 'reply').trim(),
      createdAt: new Date().toLocaleString(),
      sources: Array.isArray(data.sources)
        ? data.sources
          .map((item) => ({
            title: String(item?.title || '').trim(),
            url: String(item?.url || '').trim(),
            publishedDate: String(item?.publishedDate || item?.published_date || '').trim()
          }))
          .filter((item) => item.title || item.url)
        : []
    })
  } finally {
    chatLoading.value = false
  }
}

async function handleClearHistory() {
  await clearAgentHistory({})
  messages.value = []
  ElMessage.success('会话历史已清空')
}

async function refreshEquipmentPrediction() {
  equipmentRefreshing.value = true
  try {
    await refreshAdminAiEquipmentHealth({ horizonDaysList: [7, 30] })
    ElMessage.success('设备健康预测已刷新')
    await fetchEquipmentHealth()
  } finally {
    equipmentRefreshing.value = false
  }
}

async function reloadAll() {
  pageLoading.value = true
  try {
    await Promise.all([
      fetchDailyBrief(),
      fetchRiskAlerts(),
      fetchEquipmentHealth(),
      loadHistory(),
      submitAiQuery()
    ])
  } finally {
    pageLoading.value = false
  }
}

onMounted(() => {
  reloadAll()
})
</script>

<style scoped lang="scss">
.ai-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-card,
.summary-card,
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
    radial-gradient(circle at top right, rgba(13, 148, 136, 0.12), transparent 32%),
    linear-gradient(135deg, #fbfffe 0%, #eef8f6 100%);
}

.hero-copy {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hero-badge {
  display: inline-flex;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: var(--app-primary-soft);
  color: #115e59;
  font-size: 12px;
  font-weight: 700;
}

.hero-card h2,
.panel-head h3 {
  margin: 0;
}

.hero-card p,
.hero-meta,
.panel-head span,
.summary-label,
.summary-sub {
  color: var(--app-muted);
}

.hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 13px;
}

.summary-grid,
.content-grid {
  display: grid;
  gap: 20px;
}

.summary-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 24px;
}

.summary-value {
  font-size: 32px;
}

.content-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.panel-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 24px;
}

.panel-span-2 {
  grid-column: span 2;
}

.panel-head,
.panel-actions,
.composer-actions,
.alert-title,
.alert-footer,
.query-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.panel-head {
  margin-bottom: 4px;
}

.prompt-list,
.action-list,
.source-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.prompt-item {
  margin: 0;
}

.chat-box {
  min-height: 340px;
  max-height: 520px;
  overflow: auto;
  padding: 8px;
  border-radius: 20px;
  background: #f8fafc;
}

.message-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.message-item {
  padding: 16px;
  border-radius: 18px;
  background: #fff;
}

.message-item--user {
  border: 1px solid rgba(15, 118, 110, 0.18);
  background: rgba(240, 253, 250, 0.9);
}

.message-item--assistant {
  border: 1px solid #e2e8f0;
}

.message-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--app-muted);
}

.message-item p,
.brief-text,
.alert-item p,
.query-result p {
  margin: 0;
  line-height: 1.7;
  color: #334155;
}

.message-extra {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.composer {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.composer-actions span {
  color: var(--app-muted);
  font-size: 13px;
}

.simple-list,
.alert-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.simple-item,
.alert-item {
  padding: 14px 16px;
  border-radius: 18px;
  background: #f8fafc;
}

.simple-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.dot {
  width: 8px;
  height: 8px;
  margin-top: 8px;
  border-radius: 50%;
  background: #14b8a6;
  flex-shrink: 0;
}

.query-result {
  padding: 16px;
  border-radius: 18px;
  background: #f8fafc;
}

.alert-footer {
  margin-top: 10px;
  color: var(--app-muted);
  font-size: 13px;
}

@media (max-width: 1280px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .content-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .hero-card,
  .panel-head,
  .panel-actions,
  .composer-actions,
  .alert-title,
  .alert-footer,
  .query-meta {
    flex-direction: column;
    align-items: flex-start;
  }

  .summary-grid,
  .content-grid {
    grid-template-columns: 1fr;
  }

  .panel-span-2 {
    grid-column: span 1;
  }
}
</style>
