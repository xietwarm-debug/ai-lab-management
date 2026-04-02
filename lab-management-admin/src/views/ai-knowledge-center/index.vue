<template>
  <div class="page-container ai-knowledge-center">
    <section class="hero-card overview-section">
      <div class="hero-content">
        <div class="hero-copy">
          <span class="eyebrow">AI 知识助手</span>
          <h1 class="page-title">智能问答、知识维护与未命中运营统一工作台</h1>
          <p class="page-desc">把知识入库、问答验证、反馈复盘和未命中补齐集中到一个入口，方便管理员持续优化 AI 效果。</p>
        </div>
        <div class="hero-actions">
          <el-button class="custom-btn-plain" :loading="overviewLoading" @click="loadOverview">刷新概览</el-button>
        </div>
      </div>
    </section>

    <section class="overview-grid">
      <article class="overview-card">
        <span class="overview-label">知识文档数</span>
        <strong class="overview-value">{{ overview.documentTotal }}</strong>
        <span class="overview-sub">当前已接入的知识文档总量</span>
      </article>
      <article class="overview-card">
        <span class="overview-label">启用文档</span>
        <strong class="overview-value text-primary">{{ overview.activeDocuments }}</strong>
        <span class="overview-sub">正在参与问答命中的有效知识源</span>
      </article>
      <article class="overview-card">
        <span class="overview-label">反馈条数</span>
        <strong class="overview-value">{{ overview.feedbackTotal }}</strong>
        <span class="overview-sub">用于优化问答质量的人工反馈</span>
      </article>
      <article class="overview-card">
        <span class="overview-label">AI 简报亮点</span>
        <strong class="overview-value">{{ overview.briefHighlights }}</strong>
        <span class="overview-sub">今日自动归纳出的重点事项</span>
      </article>
    </section>

    <section class="panel-card center-toolbar">
      <div class="toolbar-main">
        <div class="toolbar-copy">
          <h3>{{ activeTabTitle }}</h3>
          <p>{{ activeTabDesc }}</p>
        </div>
        <div class="toolbar-actions">
          <el-button-group>
            <el-button :type="activeTab === 'assistant' ? 'primary' : 'default'" @click="activeTab = 'assistant'">智能问答</el-button>
            <el-button :type="activeTab === 'knowledge' ? 'primary' : 'default'" @click="activeTab = 'knowledge'">知识库管理</el-button>
            <el-button :type="activeTab === 'feedback' ? 'primary' : 'default'" @click="activeTab = 'feedback'">检索反馈</el-button>
            <el-button :type="activeTab === 'miss' ? 'primary' : 'default'" @click="activeTab = 'miss'">未命中问题</el-button>
          </el-button-group>
          <el-button class="custom-btn-plain" @click="refreshCurrentTab">刷新当前视图</el-button>
        </div>
      </div>
    </section>

    <section class="panel-card center-shell">
      <el-tabs v-model="activeTab" class="center-tabs" @tab-change="handleTabChange">
        <el-tab-pane label="智能问答" name="assistant">
          <div class="tab-stage">
            <AiAssistantView :key="tabRefreshKeys.assistant" />
          </div>
        </el-tab-pane>
        <el-tab-pane label="知识库管理" name="knowledge">
          <div class="tab-stage">
            <KnowledgeBaseView :key="tabRefreshKeys.knowledge" hide-feedback-section />
          </div>
        </el-tab-pane>
        <el-tab-pane label="检索反馈" name="feedback">
          <div class="tab-stage">
            <KnowledgeFeedbackPanel :key="tabRefreshKeys.feedback" />
          </div>
        </el-tab-pane>
        <el-tab-pane label="未命中问题" name="miss">
          <div class="tab-stage">
            <UnmatchedQuestionPanel :key="tabRefreshKeys.miss" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AiAssistantView from '@/views/ai-assistant/index.vue'
import KnowledgeBaseView from '@/views/knowledge-base/index.vue'
import { getAdminAiDailyBrief } from '@/api/ai'
import { getKnowledgeDocuments, getKnowledgeFeedbackList } from '@/api/knowledge'
import KnowledgeFeedbackPanel from './KnowledgeFeedbackPanel.vue'
import UnmatchedQuestionPanel from './UnmatchedQuestionPanel.vue'

const route = useRoute()
const router = useRouter()
const tabSet = new Set(['assistant', 'knowledge', 'feedback', 'miss'])
const overviewLoading = ref(false)
const overview = reactive({
  documentTotal: 0,
  activeDocuments: 0,
  feedbackTotal: 0,
  briefHighlights: 0
})
const tabRefreshKeys = reactive({
  assistant: 0,
  knowledge: 0,
  feedback: 0,
  miss: 0
})

const activeTab = computed({
  get() {
    const tab = String(route.query.tab || 'assistant')
    return tabSet.has(tab) ? tab : 'assistant'
  },
  set(value) {
    const tab = tabSet.has(value) ? value : 'assistant'
    router.replace({
      path: '/ai-knowledge-center',
      query: {
        ...route.query,
        tab
      }
    })
  }
})

const activeTabTitle = computed(() => {
  if (activeTab.value === 'knowledge') return '知识库管理'
  if (activeTab.value === 'feedback') return '检索反馈'
  if (activeTab.value === 'miss') return '未命中问题池'
  return '智能问答'
})

const activeTabDesc = computed(() => {
  if (activeTab.value === 'knowledge') {
    return '集中维护知识文档、状态和索引，让 AI 回答建立在稳定的知识来源之上。'
  }
  if (activeTab.value === 'feedback') {
    return '查看问答效果反馈，快速定位知识缺口和回答质量问题。'
  }
  if (activeTab.value === 'miss') {
    return '集中查看知识库没有命中的问题，按频次、来源和处理状态持续补齐缺失内容。'
  }
  return '直接测试 AI 问答和数据检索，快速验证当前知识是否可用。'
})

function handleTabChange(tab) {
  activeTab.value = String(tab || 'assistant')
}

function refreshCurrentTab() {
  const key = activeTab.value
  tabRefreshKeys[key] += 1
}

async function loadOverview() {
  overviewLoading.value = true
  try {
    const [docRes, feedbackRes, briefRes] = await Promise.all([
      getKnowledgeDocuments({}),
      getKnowledgeFeedbackList({ page: 1, pageSize: 1 }),
      getAdminAiDailyBrief().catch(() => ({ data: { data: {} } }))
    ])
    const documents = Array.isArray(docRes.data?.data) ? docRes.data.data : []
    const feedbackTotal = Number(feedbackRes.data?.meta?.total || feedbackRes.data?.data?.length || 0)
    const brief = briefRes.data?.data || {}

    overview.documentTotal = documents.length
    overview.activeDocuments = documents.filter((item) => item.status === 'active').length
    overview.feedbackTotal = feedbackTotal
    overview.briefHighlights = Array.isArray(brief.highlights) ? brief.highlights.length : 0
  } finally {
    overviewLoading.value = false
  }
}

onMounted(() => {
  loadOverview()
})
</script>

<style scoped lang="scss">
.ai-knowledge-center {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.overview-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 20px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
  border: 1px solid rgba(226, 232, 240, 0.9);
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.06);
}

.overview-label {
  color: #64748b;
  font-size: 13px;
}

.overview-value {
  color: #0f172a;
  font-size: 30px;
  font-weight: 700;
  line-height: 1;
}

.overview-sub {
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.5;
}

.center-shell {
  padding: 16px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
}

.center-toolbar {
  padding: 18px 20px;
}

.toolbar-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.toolbar-copy {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.toolbar-copy h3 {
  margin: 0;
  color: #0f172a;
  font-size: 18px;
}

.toolbar-copy p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

:deep(.center-tabs > .el-tabs__header) {
  margin-bottom: 18px;
}

:deep(.center-tabs .el-tabs__nav-wrap::after) {
  height: 1px;
  background: rgba(226, 232, 240, 0.9);
}

:deep(.center-tabs .el-tabs__item) {
  height: 42px;
  padding: 0 18px;
  font-weight: 600;
  color: #64748b;
}

:deep(.center-tabs .el-tabs__item.is-active) {
  color: #2563eb;
}

:deep(.center-tabs .el-tabs__active-bar) {
  height: 3px;
  border-radius: 999px;
  background: linear-gradient(90deg, #2563eb, #7c3aed);
}

:deep(.center-tabs > .el-tabs__content) {
  padding-top: 12px;
}

.tab-stage {
  border-radius: 22px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.96));
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.06);
  overflow: hidden;
}

:deep(.tab-stage > .page-container),
:deep(.tab-stage > .knowledge-page),
:deep(.tab-stage > .workspace-shell),
:deep(.tab-stage > .panel-card) {
  border-radius: 0;
}

:deep(.center-tabs .el-tab-pane > .page-container),
:deep(.center-tabs .el-tab-pane > .knowledge-page),
:deep(.center-tabs .el-tab-pane > .workspace-shell) {
  min-height: auto;
}

:deep(.center-tabs .el-tab-pane > .page-container) {
  padding: 0;
}

:deep(.center-tabs .knowledge-page) {
  background: transparent;
}

@media (max-width: 1200px) {
  .overview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }

  .toolbar-main {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
