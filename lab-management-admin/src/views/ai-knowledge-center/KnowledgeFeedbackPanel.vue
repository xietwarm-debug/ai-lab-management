<template>
  <section class="panel-card list-card">
    <div class="panel-head">
      <div class="head-title">
        <h3>检索反馈</h3>
        <p class="sub-text">集中查看知识问答反馈，便于持续补文档、调优索引与优化回答质量。</p>
      </div>
      <el-button class="custom-btn-plain" :loading="feedbackLoading" @click="loadFeedback">刷新反馈</el-button>
    </div>

    <div class="feedback-overview">
      <div class="feedback-metric">
        <span class="metric-label">总反馈</span>
        <strong class="metric-value">{{ feedbackRows.length }}</strong>
      </div>
      <div class="feedback-metric is-positive">
        <span class="metric-label">有帮助</span>
        <strong class="metric-value">{{ helpfulCount }}</strong>
      </div>
      <div class="feedback-metric is-negative">
        <span class="metric-label">待优化</span>
        <strong class="metric-value">{{ unhelpfulCount }}</strong>
      </div>
    </div>

    <div class="filter-bar">
      <el-form inline class="filter-form">
        <el-form-item label="反馈结果">
          <el-select v-model="feedbackFilters.helpful" clearable placeholder="全部反馈" class="filter-select">
            <el-option label="全部" value="" />
            <el-option label="有帮助" :value="true" />
            <el-option label="没帮助" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="feedbackFilters.keyword"
            clearable
            placeholder="问题 / 答案 / 反馈内容 / 用户"
            @keyup.enter="loadFeedback"
            class="filter-input-long"
          />
        </el-form-item>
        <el-form-item class="filter-actions">
          <el-button @click="resetFeedbackFilters">清空</el-button>
          <el-button type="primary" :loading="feedbackLoading" @click="loadFeedback">查询</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-table
      v-loading="feedbackLoading"
      :data="feedbackRows"
      class="custom-table"
      :header-cell-style="{ background: '#f8fafc', color: '#64748b', fontWeight: 600 }"
    >
      <el-table-column label="反馈" width="120">
        <template #default="{ row }">
          <el-tag size="small" :type="row.helpful ? 'success' : 'danger'" effect="light" class="feedback-tag">
            {{ row.helpful ? '有帮助' : '没帮助' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="question" label="问题" min-width="220" show-overflow-tooltip />
      <el-table-column prop="answer" label="回答摘要" min-width="260" show-overflow-tooltip />
      <el-table-column prop="comment" label="反馈说明" min-width="220" show-overflow-tooltip />
      <el-table-column prop="createdBy" label="反馈人" width="120" show-overflow-tooltip />
      <el-table-column prop="createdAt" label="反馈时间" width="180" show-overflow-tooltip />
      <template #empty>
        <el-empty description="暂无知识问答反馈" :image-size="100" />
      </template>
    </el-table>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { getKnowledgeFeedbackList } from '@/api/knowledge'

const feedbackLoading = ref(false)
const feedbackRows = ref([])

const feedbackFilters = reactive({
  helpful: '',
  keyword: ''
})

const helpfulCount = computed(() => feedbackRows.value.filter((item) => item.helpful).length)
const unhelpfulCount = computed(() => feedbackRows.value.filter((item) => !item.helpful).length)

function resetFeedbackFilters() {
  feedbackFilters.helpful = ''
  feedbackFilters.keyword = ''
  loadFeedback()
}

async function loadFeedback() {
  feedbackLoading.value = true
  try {
    const response = await getKnowledgeFeedbackList({
      helpful: feedbackFilters.helpful || undefined,
      keyword: feedbackFilters.keyword || undefined,
      page: 1,
      pageSize: 20
    })
    feedbackRows.value = Array.isArray(response.data?.data) ? response.data.data : []
  } finally {
    feedbackLoading.value = false
  }
}

onMounted(() => {
  loadFeedback()
})
</script>

<style scoped lang="scss">
.feedback-overview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.feedback-metric {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 18px;
  border-radius: 16px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
}

.feedback-metric.is-positive {
  background: linear-gradient(180deg, rgba(240, 253, 244, 0.95), rgba(255, 255, 255, 0.98));
}

.feedback-metric.is-negative {
  background: linear-gradient(180deg, rgba(254, 242, 242, 0.95), rgba(255, 255, 255, 0.98));
}

.metric-label {
  color: #64748b;
  font-size: 13px;
}

.metric-value {
  color: #0f172a;
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}

@media (max-width: 900px) {
  .feedback-overview {
    grid-template-columns: 1fr;
  }
}
</style>
