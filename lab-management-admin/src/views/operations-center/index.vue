<template>
  <div class="operations-center">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="eyebrow">Operations Hub</span>
        <h2>运营中心</h2>
        <p>集运营待办值班应急多功能一体的运营中心</p>
      </div>
      <div class="hero-actions">
        <el-button :loading="loading" @click="loadOverview">刷新概览</el-button>
        <el-button-group>
          <el-button
            v-for="tab in visibleTabs"
            :key="tab.name"
            :type="activeTab === tab.name ? 'primary' : 'default'"
            @click="activeTab = tab.name"
          >
            {{ tab.label }}
          </el-button>
        </el-button-group>
      </div>
    </section>

    <section class="overview-grid">
      <article v-for="card in overviewCards" :key="card.label" class="overview-card">
        <span class="overview-label">{{ card.label }}</span>
        <strong class="overview-value">{{ card.value }}</strong>
        <p class="overview-desc">{{ card.desc }}</p>
      </article>
    </section>

    <section class="tabs-card">
      <el-tabs v-model="activeTab" class="operations-tabs">
        <el-tab-pane
          v-for="tab in visibleTabs"
          :key="tab.name"
          :label="tab.label"
          :name="tab.name"
        >
          <component :is="tab.component" />
        </el-tab-pane>
      </el-tabs>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getOperationsBoard } from '@/api/operations'
import { getTodoCenter } from '@/api/todo'
import { useAuthStore } from '@/stores/auth'
import OperationsBoardPage from '@/views/operations-board/index.vue'
import TodoCenterPage from '@/views/todo-center/index.vue'
import DutyEmergencyPage from '@/views/duty-emergency/index.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const activeTab = ref('board')
const boardOverview = ref({})
const todoSummary = ref({})

const canViewTodo = computed(() => authStore.role === 'admin')
const canViewDuty = computed(() => authStore.role === 'admin')

const visibleTabs = computed(() => {
  const tabs = [
    {
      name: 'board',
      label: '运营看板',
      component: OperationsBoardPage
    }
  ]

  if (canViewTodo.value) {
    tabs.push({
      name: 'todo',
      label: '待办中心',
      component: TodoCenterPage
    })
  }

  if (canViewDuty.value) {
    tabs.push({
      name: 'duty',
      label: '值班应急',
      component: DutyEmergencyPage
    })
  }

  return tabs
})

const overviewCards = computed(() => [
  {
    label: '今日预约',
    value: Number(boardOverview.value.todayReservations || 0),
    desc: '帮助快速感知当天实验室预约活跃度。'
  },
  {
    label: '设备风险',
    value: Number(boardOverview.value.highRiskAlerts || boardOverview.value.riskAlerts || 0),
    desc: '优先关注高风险告警与需要联动处理的设备异常。'
  },
  {
    label: '待办总量',
    value: canViewTodo.value ? Number(todoSummary.value.total || 0) : '-',
    desc: canViewTodo.value ? '集中查看当前待处理事项的整体规模。' : '当前账号无待办处置权限。'
  },
  {
    label: '超时事项',
    value: canViewTodo.value ? Number(todoSummary.value.timeoutTotal || 0) : '-',
    desc: canViewTodo.value ? '超时事项适合优先处理，减少后续连锁影响。' : '当前账号无待办处置权限。'
  },
  

])

function normalizeTab(tabName) {
  const target = String(tabName || '').trim()
  const fallback = visibleTabs.value[0]?.name || 'board'
  return visibleTabs.value.some((tab) => tab.name === target) ? target : fallback
}

async function loadOverview() {
  loading.value = true
  try {
    const requests = [
      getOperationsBoard(),
      canViewTodo.value ? getTodoCenter({ sortBy: 'priority', sortOrder: 'desc', limitPerCard: 1 }) : Promise.resolve(null)
    ]

    const [boardResp, todoResp] = await Promise.all(requests)
    boardOverview.value = boardResp?.data?.data?.overview || {}
    todoSummary.value = todoResp?.data?.data?.summary || {}
  } finally {
    loading.value = false
  }
}

watch(
  visibleTabs,
  () => {
    activeTab.value = normalizeTab(route.query.tab)
  },
  { immediate: true }
)

watch(
  () => route.query.tab,
  (tab) => {
    activeTab.value = normalizeTab(tab)
  }
)

watch(activeTab, (tab) => {
  const normalized = normalizeTab(tab)
  if (normalized !== activeTab.value) {
    activeTab.value = normalized
    return
  }
  if (route.query.tab !== normalized) {
    router.replace({
      path: route.path,
      query: {
        ...route.query,
        tab: normalized
      }
    })
  }
})

loadOverview()
</script>

<style scoped lang="scss">
.operations-center {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-card,
.overview-card,
.tabs-card {
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
    radial-gradient(circle at top right, rgba(14, 116, 144, 0.14), transparent 30%),
    linear-gradient(135deg, #fbfeff 0%, #eef9fd 100%);
}

.hero-copy {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hero-copy h2,
.overview-card p {
  margin: 0;
}

.hero-copy p,
.overview-desc {
  color: var(--app-muted);
}

.eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(8, 145, 178, 0.12);
  color: #0e7490;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
}

.overview-card {
  padding: 22px;
}

.overview-label {
  display: block;
  color: var(--app-muted);
  font-size: 13px;
}

.overview-value {
  display: block;
  margin-top: 12px;
  font-size: 30px;
  color: #0f172a;
}

.overview-desc {
  margin-top: 10px;
  line-height: 1.7;
}

.tabs-card {
  padding: 10px 20px 20px;
}

:deep(.operations-tabs > .el-tabs__content) {
  overflow: visible;
}

@media (max-width: 1200px) {
  .overview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .hero-card {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 640px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }
}
</style>
