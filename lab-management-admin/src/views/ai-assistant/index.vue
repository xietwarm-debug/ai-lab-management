<template>
  <div class="ai-page">
    <section class="workspace-shell">
      <div class="workspace-main">
        <article class="chat-panel">
          <header class="chat-header">
            <div class="assistant-identity">
              <div class="assistant-avatar">
                <span>AI</span>
              </div>
              <div class="assistant-copy">
                <div class="assistant-title-row">
                  <h2>宁宁</h2>
                  <span class="assistant-badge">管理后台助手</span>
                </div>
                <p>
                  我可以帮你处理预约、改期、取消、报修、查进度和规则解释，也能联网搜索最新资讯、官网和文档。
                  页面体验向手机端靠拢，但保留后台网页端的工作台信息密度。
                </p>
              </div>
            </div>

            <div class="header-actions">
              <el-button text @click="loadHistory">刷新记录</el-button>
              <el-button :loading="pageLoading" @click="reloadAll">刷新全部</el-button>
              <el-popconfirm title="确认清空当前会话历史？" @confirm="handleClearHistory">
                <template #reference>
                  <el-button type="danger" plain>清空历史</el-button>
                </template>
              </el-popconfirm>
            </div>
          </header>

          <section class="summary-strip">
            <article class="summary-pill">
              <span class="summary-label">今日速览</span>
              <strong>{{ dailyBrief.highlights?.length || 0 }}</strong>
              <small>重点摘要</small>
            </article>
            <article class="summary-pill">
              <span class="summary-label">风险提醒</span>
              <strong>{{ riskAlerts.length }}</strong>
              <small>{{ riskLevelText }}</small>
            </article>
            <article class="summary-pill">
              <span class="summary-label">设备健康</span>
              <strong>{{ equipmentHealth.length }}</strong>
              <small>预测样本</small>
            </article>
            <article class="summary-pill">
              <span class="summary-label">对话消息</span>
              <strong>{{ messages.length }}</strong>
              <small>当前会话</small>
            </article>
          </section>

          <div ref="chatBodyRef" class="chat-body">
            <div class="welcome-card" :class="{ 'welcome-card--compact': messages.length > 0 }">
              <div class="welcome-orb">
                <div class="welcome-orb-core">AI</div>
              </div>
              <div class="welcome-text">
                <p>
                  {{ messages.length > 0
                    ? '你可以继续追问、让它联网搜索，或者从下方快捷入口继续处理后台事务。'
                    : '这里沿用了手机端的对话体验：先问问题，再在右侧看日报、风险和统计结果。' }}
                </p>
              </div>
            </div>

            <div v-if="messages.length" class="message-list">
              <div
                v-for="item in messages"
                :key="item.id"
                class="message-row"
                :class="`message-row--${item.role}`"
              >
                <div class="message-bubble" :class="`message-bubble--${item.role}`">
                  <div class="message-topline">
                    <strong>{{ item.role === 'user' ? '我' : '宁宁' }}</strong>
                    <span>{{ item.createdAt || '-' }}</span>
                  </div>
                  <p class="message-text">{{ item.text }}</p>

                  <div v-if="item.action || item.sources?.length" class="message-extra">
                    <el-tag v-if="item.action" size="small" type="info">{{ item.action }}</el-tag>

                    <div v-if="item.sources?.length" class="source-panel">
                      <span class="source-header">联网来源</span>
                      <component
                        v-for="(source, index) in item.sources"
                        :key="`${item.id}-${index}`"
                        :is="source.url ? 'a' : 'div'"
                        class="source-item"
                        :class="{ 'source-item--static': !source.url }"
                        :href="source.url || undefined"
                        :target="source.url ? '_blank' : undefined"
                        :rel="source.url ? 'noopener noreferrer' : undefined"
                      >
                        <span class="source-index">{{ index + 1 }}</span>
                        <span class="source-body">
                          <strong>{{ source.title || source.url }}</strong>
                          <small>
                            {{ sourceHost(source.url) }}
                            <template v-if="source.publishedDate"> · {{ source.publishedDate }}</template>
                          </small>
                        </span>
                      </component>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <el-empty
              v-else
              description="还没有对话记录，可以从下方快捷提问开始。"
            />
          </div>

          <footer class="composer-panel">
            <div class="quick-actions">
              <button
                v-for="prompt in quickPrompts"
                :key="prompt"
                type="button"
                class="quick-chip"
                @click="usePrompt(prompt)"
              >
                {{ prompt }}
              </button>
            </div>

            <div class="composer-box">
              <el-input
                v-model="chatInput"
                class="composer-input"
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
                <div class="composer-buttons">
                  <el-button :disabled="chatLoading" @click="submitWebSearch">联网搜</el-button>
                  <el-button type="primary" :loading="chatLoading" @click="submitChat">发送</el-button>
                </div>
              </div>
            </div>
          </footer>
        </article>

        <aside class="insight-panel">
          <article class="insight-card">
            <div class="insight-head">
              <div>
                <h3>AI 每日简报</h3>
                <span>{{ dailyBrief.generatedAt || '暂无生成时间' }}</span>
              </div>
            </div>

            <p class="insight-copy">
              {{ dailyBrief.summaryText || '暂时还没有日报摘要，可以刷新后再看。' }}
            </p>

            <div v-if="dailyBrief.highlights?.length" class="bullet-list">
              <div v-for="(item, index) in dailyBrief.highlights" :key="index" class="bullet-item">
                <span class="bullet-dot" />
                <span>{{ item }}</span>
              </div>
            </div>
            <el-empty v-else description="暂无重点摘要" />

            <div v-if="dailyBrief.focusActions?.length" class="link-actions">
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

          <article class="insight-card">
            <div class="insight-head">
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
              <div class="query-tags">
                <el-tag size="small">{{ statsAnswer.intent || 'summary' }}</el-tag>
                <el-tag size="small" :type="statsAnswer.matched ? 'success' : 'info'">
                  {{ statsAnswer.matched ? '已命中规则问法' : '通用摘要回答' }}
                </el-tag>
              </div>
              <p>{{ statsAnswer.answer || '输入问题后，AI 会基于后台统计快照返回简短回答。' }}</p>
            </div>
          </article>

          <article class="insight-card">
            <div class="insight-head">
              <div>
                <h3>风险提醒</h3>
                <span>按风险分数排序</span>
              </div>
            </div>

            <div v-if="riskAlerts.length" class="alert-list">
              <div v-for="(item, index) in riskAlerts" :key="`${item.title}-${index}`" class="alert-item">
                <div class="alert-head">
                  <strong>{{ item.title || '未命名提醒' }}</strong>
                  <el-tag size="small" :type="riskTagType(item.level)">{{ riskLevelLabel(item.level) }}</el-tag>
                </div>
                <p>{{ item.description || '-' }}</p>
                <div class="alert-foot">
                  <span>风险分：{{ item.score ?? '-' }}</span>
                  <el-button
                    v-if="normalizeJumpUrl(item.jumpUrl)"
                    text
                    type="primary"
                    @click="jumpFromBackend(item.jumpUrl)"
                  >
                    查看页面
                  </el-button>
                </div>
              </div>
            </div>
            <el-empty v-else description="暂无风险提醒" />
          </article>
          <article class="insight-card">
            <div class="insight-head">
              <div>
                <h3>知识问答联动</h3>
                <span>直接调用知识库检索并提交反馈</span>
              </div>
              <el-button text :loading="knowledgeLoading" @click="submitKnowledgeAsk">提问</el-button>
            </div>

            <el-input
              v-model="knowledgeQuestion"
              placeholder="例如：借用设备逾期后怎么处理？"
              maxlength="120"
              @keyup.enter="submitKnowledgeAsk"
            />

            <div class="query-result">
              <div class="query-tags">
                <el-tag size="small">{{ knowledgeMatched ? 'knowledge' : 'no-hit' }}</el-tag>
                <el-tag size="small" :type="knowledgeMatched ? 'success' : 'info'">
                  {{ knowledgeMatched ? '命中知识库' : '暂未命中' }}
                </el-tag>
              </div>
              <p>{{ knowledgeAnswer || '这里会展示知识库返回的制度、规范和规则答案。' }}</p>
            </div>

            <div v-if="knowledgeSources.length" class="knowledge-source-list">
              <div v-for="(item, index) in knowledgeSources" :key="`${item.documentId}-${item.chunkNo}-${index}`" class="knowledge-source-item">
                <strong>{{ index + 1 }}. {{ item.title || '-' }}</strong>
                <span>{{ item.excerpt || '-' }}</span>
              </div>
            </div>

            <div class="knowledge-actions">
              <el-button text type="primary" @click="router.push('/knowledge-base')">去知识库管理</el-button>
            </div>

            <div v-if="knowledgeQueryLogId" class="knowledge-feedback-box">
              <el-radio-group v-model="knowledgeFeedbackForm.helpful">
                <el-radio-button :label="true">有帮助</el-radio-button>
                <el-radio-button :label="false">没帮助</el-radio-button>
              </el-radio-group>
              <el-input
                v-model="knowledgeFeedbackForm.comment"
                type="textarea"
                :rows="3"
                maxlength="255"
                show-word-limit
                placeholder="可选：补充反馈，帮助完善知识库内容"
              />
              <el-button type="primary" :loading="knowledgeFeedbackLoading" @click="submitKnowledgeFeedbackForm">
                提交反馈
              </el-button>
            </div>
          </article>
        </aside>
      </div>

      <article class="equipment-panel">
        <div class="equipment-head">
          <div>
            <h3>设备健康预测</h3>
            <p>保留后台网页端的数据视图，方便你在聊天之外快速核对具体设备风险。</p>
          </div>
          <div class="equipment-actions">
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
          <el-table-column label="失效概率" min-width="120">
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
import { useRoute, useRouter } from 'vue-router'
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
import { askKnowledgeQuestion, submitKnowledgeFeedback } from '@/api/knowledge'
import { resolveAdminJumpUrl } from '@/utils/admin-links'

const route = useRoute()
const router = useRouter()
const chatBodyRef = ref(null)

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
const knowledgeQuestion = ref('实验室预约最多可提前几天？')
const knowledgeAnswer = ref('')
const knowledgeSources = ref([])
const knowledgeQueryLogId = ref(0)
const knowledgeMatched = ref(false)
const knowledgeLoading = ref(false)
const knowledgeFeedbackLoading = ref(false)
const knowledgeFeedbackForm = reactive({
  helpful: true,
  comment: ''
})

const quickPrompts = [
  '请总结今天后台最值得优先处理的事项',
  '当前待审批预约有多少？',
  '最近 24 小时有哪些风险提醒？',
  '有哪些设备故障风险较高？',
  '联网搜索今天 AI 行业最新新闻'
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
  if (normalized === 'high') return '高风险'
  if (normalized === 'medium') return '中风险'
  return '低风险'
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
  return resolveAdminJumpUrl(jumpUrl)
}

function jumpFromBackend(jumpUrl) {
  const target = normalizeJumpUrl(jumpUrl)
  if (!target) {
    ElMessage.info('当前建议没有可跳转的后台页面')
    return
  }
  router.push(target)
}

function normalizeSources(rawSources) {
  return Array.isArray(rawSources)
    ? rawSources
      .map((item) => ({
        title: String(item?.title || '').trim(),
        url: String(item?.url || '').trim(),
        publishedDate: String(item?.publishedDate || item?.published_date || '').trim()
      }))
      .filter((item) => item.title || item.url)
    : []
}

function sourceHost(rawUrl) {
  const url = String(rawUrl || '').trim()
  if (!url) return '未提供链接'
  const compact = url.replace(/^https?:\/\//i, '').replace(/^www\./i, '')
  const host = compact.split('/')[0]
  return host || compact || url
}

function createLocalMessage(role, text, extra = {}) {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    role,
    text: String(text || '').trim(),
    action: String(extra.action || '').trim(),
    createdAt: String(extra.createdAt || new Date().toLocaleString()).trim(),
    sources: normalizeSources(extra.sources)
  }
}

function normalizeMessage(row, index) {
  const meta = row?.meta && typeof row.meta === 'object' ? row.meta : {}
  return {
    id: row?.id || `${row?.role || 'message'}-${row?.createdAt || index}`,
    role: String(row?.role || '').trim() === 'user' ? 'user' : 'assistant',
    text: String(row?.text || '').trim(),
    action: String(row?.action || '').trim(),
    createdAt: String(row?.createdAt || '').trim(),
    sources: normalizeSources(meta.sources)
  }
}

async function scrollChatToBottom() {
  await nextTick()
  const container = chatBodyRef.value
  if (!container) return
  container.scrollTo({
    top: container.scrollHeight,
    behavior: 'smooth'
  })
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
  await scrollChatToBottom()
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

function normalizeKnowledgeSources(rawSources) {
  return Array.isArray(rawSources)
    ? rawSources
      .map((item) => ({
        documentId: Number(item?.documentId || 0),
        chunkNo: Number(item?.chunkNo || 0),
        title: String(item?.title || '').trim(),
        excerpt: String(item?.excerpt || '').trim()
      }))
      .filter((item) => item.title || item.excerpt)
    : []
}

async function submitKnowledgeAsk() {
  const question = String(knowledgeQuestion.value || '').trim()
  if (!question) {
    ElMessage.warning('请输入知识库问题')
    return
  }
  knowledgeLoading.value = true
  try {
    const response = await askKnowledgeQuestion({ question })
    const data = response.data?.data || {}
    knowledgeMatched.value = Boolean(data.matched)
    knowledgeAnswer.value = String(data.answer || '')
    knowledgeSources.value = normalizeKnowledgeSources(data.sources)
    knowledgeQueryLogId.value = Number(data.queryLogId || 0)
    knowledgeFeedbackForm.helpful = true
    knowledgeFeedbackForm.comment = ''
    if (!knowledgeMatched.value) {
      ElMessage.info('当前知识库暂未命中该问题')
    }
  } finally {
    knowledgeLoading.value = false
  }
}

async function submitKnowledgeFeedbackForm() {
  if (!knowledgeQueryLogId.value) return
  knowledgeFeedbackLoading.value = true
  try {
    await submitKnowledgeFeedback({
      queryLogId: knowledgeQueryLogId.value,
      helpful: knowledgeFeedbackForm.helpful,
      comment: String(knowledgeFeedbackForm.comment || '').trim()
    })
    ElMessage.success('知识问答反馈已提交')
  } finally {
    knowledgeFeedbackLoading.value = false
  }
}

function usePrompt(prompt) {
  chatInput.value = prompt
  submitChat()
}

function buildWebSearchText(rawText) {
  const text = String(rawText || '').trim()
  if (!text) return ''
  const normalized = text.replace(/^联网搜索[\s:：]*/i, '')
  return /^联网搜索[\s:：]/.test(text) ? text : `联网搜索 ${normalized}`
}

async function submitWebSearch() {
  const text = buildWebSearchText(chatInput.value)
  if (!text) {
    ElMessage.warning('请先输入要搜索的内容')
    return
  }
  chatInput.value = text
  await submitChat()
}

async function submitChat() {
  const text = String(chatInput.value || '').trim()
  if (!text) {
    ElMessage.warning('请先输入问题')
    return
  }
  if (chatLoading.value) return

  chatLoading.value = true
  try {
    messages.value.push(createLocalMessage('user', text))
    chatInput.value = ''
    await scrollChatToBottom()

    const response = await chatWithAgent({ text })
    const payload = response.data || {}
    const data = payload.data || {}

    if (Number(payload.code || 0) !== 0) {
      messages.value.push(createLocalMessage('assistant', data.reply || payload.msg || '请求失败', {
        action: data.action || 'error'
      }))
      await scrollChatToBottom()
      return
    }

    messages.value.push(createLocalMessage('assistant', data.reply || '已处理完成。', {
      action: data.action || 'reply',
      sources: data.sources
    }))
    await scrollChatToBottom()
  } finally {
    chatLoading.value = false
  }
}

async function handleClearHistory() {
  await clearAgentHistory({})
  messages.value = []
  await scrollChatToBottom()
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
    const results = await Promise.allSettled([
      fetchDailyBrief(),
      fetchRiskAlerts(),
      fetchEquipmentHealth(),
      loadHistory(),
      submitAiQuery()
    ])
    if (results.some((item) => item.status === 'rejected')) {
      ElMessage.warning('部分数据刷新失败，页面已展示可用内容')
    }
  } finally {
    pageLoading.value = false
  }
}

onMounted(() => {
  if (route.query.question) {
    knowledgeQuestion.value = String(route.query.question || '').trim() || knowledgeQuestion.value
  }
  reloadAll()
  if (route.query.tab === 'knowledge') {
    submitKnowledgeAsk()
  }
})
</script>

<style scoped lang="scss">
.ai-page {
  min-height: 100%;
}

.workspace-shell {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.workspace-main {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.82fr);
  gap: 20px;
  align-items: start;
}

.chat-panel,
.insight-card,
.equipment-panel {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 28px;
  background:
    radial-gradient(circle at top right, rgba(15, 118, 110, 0.1), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(247, 250, 252, 0.96) 100%);
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(12px);
}

.chat-panel {
  min-height: calc(100vh - 152px);
  padding: 24px;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  gap: 18px;
}

.chat-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.assistant-identity {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.assistant-avatar {
  width: 58px;
  height: 58px;
  border-radius: 22px;
  background:
    linear-gradient(135deg, rgba(15, 118, 110, 0.95) 0%, rgba(20, 184, 166, 0.72) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  box-shadow: 0 14px 26px rgba(15, 118, 110, 0.24);
  flex-shrink: 0;
}

.assistant-copy {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.assistant-title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.assistant-title-row h2,
.insight-head h3,
.equipment-head h3 {
  margin: 0;
}

.assistant-copy p,
.insight-copy,
.equipment-head p {
  margin: 0;
  line-height: 1.7;
  color: var(--app-muted);
}

.assistant-badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.1);
  color: #0f766e;
  font-size: 12px;
  font-weight: 700;
}

.header-actions,
.composer-buttons,
.equipment-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.summary-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-pill {
  padding: 16px 18px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.18);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.summary-label,
.summary-pill small,
.insight-head span,
.composer-actions span,
.query-tags,
.alert-foot {
  color: var(--app-muted);
}

.summary-pill strong {
  font-size: 30px;
  line-height: 1;
  color: #0f172a;
}

.chat-body {
  min-height: 360px;
  max-height: calc(100vh - 420px);
  overflow: auto;
  padding-right: 6px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.welcome-card {
  padding: 28px 24px;
  border-radius: 28px;
  background:
    radial-gradient(circle at center, rgba(20, 184, 166, 0.18), transparent 54%),
    linear-gradient(180deg, rgba(239, 250, 248, 0.92) 0%, rgba(255, 255, 255, 0.92) 100%);
  border: 1px solid rgba(148, 163, 184, 0.18);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
  text-align: center;
}

.welcome-card--compact {
  padding: 18px;
  border-radius: 24px;
  flex-direction: row;
  justify-content: flex-start;
  text-align: left;
}

.welcome-orb {
  width: 176px;
  height: 176px;
  border-radius: 50%;
  background:
    radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.92), transparent 30%),
    radial-gradient(circle at 70% 70%, rgba(20, 184, 166, 0.3), transparent 32%),
    linear-gradient(135deg, rgba(15, 118, 110, 0.16) 0%, rgba(20, 184, 166, 0.08) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.welcome-card--compact .welcome-orb {
  width: 72px;
  height: 72px;
}

.welcome-orb-core {
  width: 78%;
  height: 78%;
  border-radius: 50%;
  background: linear-gradient(135deg, #0f766e 0%, #2dd4bf 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
  box-shadow: inset 0 0 24px rgba(255, 255, 255, 0.16);
}

.welcome-card--compact .welcome-orb-core {
  font-size: 18px;
}

.welcome-text {
  max-width: 580px;
}

.welcome-text p,
.message-text,
.query-result p,
.alert-item p {
  margin: 0;
  line-height: 1.72;
  color: #334155;
  white-space: pre-wrap;
}

.message-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message-row {
  display: flex;
}

.message-row--user {
  justify-content: flex-end;
}

.message-row--assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: min(78%, 720px);
  padding: 16px 18px;
  border-radius: 24px;
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
}

.message-bubble--user {
  background: linear-gradient(135deg, #0f766e 0%, #14b8a6 100%);
  color: #fff;
  border-bottom-right-radius: 10px;
}

.message-bubble--user .message-text,
.message-bubble--user .message-topline span,
.message-bubble--user .message-topline strong {
  color: #fff;
}

.message-bubble--assistant {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-bottom-left-radius: 10px;
}

.message-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  font-size: 12px;
}

.message-topline span {
  color: var(--app-muted);
}

.message-extra {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.source-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.source-header {
  font-size: 12px;
  color: var(--app-muted);
}

.source-item {
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(241, 245, 249, 0.84);
  display: flex;
  align-items: flex-start;
  gap: 12px;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.source-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.08);
}

.source-item--static {
  cursor: default;
}

.source-item--static:hover {
  transform: none;
  box-shadow: none;
}

.source-index {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(20, 184, 166, 0.14);
  color: #0f766e;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.source-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.source-body strong,
.source-body small {
  word-break: break-word;
}

.source-body small {
  color: var(--app-muted);
}

.composer-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.quick-chip {
  border: 0;
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.14);
  color: #334155;
  cursor: pointer;
  transition: transform 0.16s ease, background-color 0.16s ease, color 0.16s ease;
}

.quick-chip:hover {
  transform: translateY(-1px);
  background: rgba(20, 184, 166, 0.14);
  color: #0f766e;
}

.composer-box {
  padding: 16px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(148, 163, 184, 0.18);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.composer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.insight-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.insight-card,
.equipment-panel {
  padding: 22px;
}

.insight-head,
.alert-head,
.alert-foot,
.equipment-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.insight-head {
  margin-bottom: 14px;
}

.bullet-list,
.alert-list,
.link-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bullet-item,
.alert-item,
.query-result {
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.bullet-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.bullet-dot {
  width: 8px;
  height: 8px;
  margin-top: 8px;
  border-radius: 50%;
  background: #14b8a6;
  flex-shrink: 0;
}

.link-actions {
  margin-top: 14px;
}

.query-result {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.query-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.knowledge-source-list,
.knowledge-feedback-box {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 14px;
}

.knowledge-source-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.knowledge-source-item span {
  color: var(--app-muted);
  line-height: 1.6;
}

.knowledge-actions {
  margin-top: 8px;
}

.alert-list {
  max-height: 420px;
  overflow: auto;
  padding-right: 4px;
}

.equipment-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.equipment-head p {
  margin-top: 6px;
}

@media (max-width: 1440px) {
  .summary-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1200px) {
  .workspace-main {
    grid-template-columns: 1fr;
  }

  .chat-panel {
    min-height: auto;
  }

  .chat-body {
    max-height: 560px;
  }
}

@media (max-width: 768px) {
  .chat-panel,
  .insight-card,
  .equipment-panel {
    border-radius: 22px;
  }

  .chat-panel {
    padding: 18px;
  }

  .chat-header,
  .assistant-identity,
  .header-actions,
  .composer-actions,
  .equipment-head,
  .equipment-actions,
  .alert-head,
  .alert-foot {
    flex-direction: column;
    align-items: flex-start;
  }

  .summary-strip {
    grid-template-columns: 1fr;
  }

  .chat-body {
    min-height: 300px;
    max-height: 520px;
  }

  .welcome-card,
  .welcome-card--compact {
    padding: 18px;
    flex-direction: column;
    text-align: center;
  }

  .welcome-orb {
    width: 132px;
    height: 132px;
  }

  .message-bubble {
    max-width: 100%;
  }

  .composer-buttons {
    width: 100%;
  }

  .composer-buttons :deep(.el-button) {
    flex: 1;
  }
}
</style>
