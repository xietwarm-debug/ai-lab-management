<template>
  <div class="approval-center">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="eyebrow">Approval Hub</span>
        <h2>审批中心</h2>
        <p>统一处理预约审批、借用审批和审批流配置，把日常审核工作集中到一个入口。</p>
      </div>
      <div class="hero-actions">
        <el-button :loading="overviewLoading" @click="loadOverview">刷新概览</el-button>
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
      <el-tabs v-model="activeTab" class="approval-tabs">
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
import { hasPermission } from '@/utils/auth'
import { useAuthStore } from '@/stores/auth'
import { getReservationList } from '@/api/reservations'
import { getBorrowRenewRequests, getBorrowRequests } from '@/api/borrow'
import { getReservationRules } from '@/api/rules'
import {
  PERMISSION_ASSET_MANAGER,
  PERMISSION_SCHEDULE_MANAGER
} from '@/utils/constants'
import ReservationsPage from '@/views/reservations/index.vue'
import BorrowApprovalPage from '@/views/borrow-approval/index.vue'
import ReservationRulesPage from '@/views/reservation-rules/index.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const overviewLoading = ref(false)
const reservationPending = ref(0)
const borrowPending = ref(0)
const renewPending = ref(0)
const approvalMode = ref('-')
const activeTab = ref('reservations')

const canViewBorrow = computed(() => {
  return authStore.role === 'admin' || hasPermission(authStore.user, PERMISSION_ASSET_MANAGER)
})

const canViewRules = computed(() => {
  return authStore.role === 'admin' || hasPermission(authStore.user, PERMISSION_SCHEDULE_MANAGER)
})

const visibleTabs = computed(() => {
  const tabs = [
    {
      name: 'reservations',
      label: '预约审批',
      component: ReservationsPage
    }
  ]

  if (canViewBorrow.value) {
    tabs.push({
      name: 'borrow',
      label: '借用审批',
      component: BorrowApprovalPage
    })
  }

  if (canViewRules.value) {
    tabs.push({
      name: 'rules',
      label: '审批流配置',
      component: ReservationRulesPage
    })
  }

  return tabs
})

const overviewCards = computed(() => [
  {
    label: '待审批预约',
    value: reservationPending.value,
    desc: '聚焦尚未处理的实验室预约申请。'
  },
  {
    label: '待审批借用',
    value: canViewBorrow.value ? borrowPending.value : '-',
    desc: canViewBorrow.value ? '集中处理设备借用和归还流转。' : '当前账号无借用审批权限。'
  },
  {
    label: '待审批续借',
    value: canViewBorrow.value ? renewPending.value : '-',
    desc: canViewBorrow.value ? '需要续借复核的申请会优先显示。' : '当前账号无续借审批权限。'
  },
  {
    label: '当前审批模式',
    value: canViewRules.value ? approvalMode.value : '-',
    desc: canViewRules.value ? '帮助快速确认预约规则的生效策略。' : '当前账号无审批流配置权限。'
  }
])

function normalizeTab(tabName) {
  const target = String(tabName || '').trim()
  const fallback = visibleTabs.value[0]?.name || 'reservations'
  return visibleTabs.value.some((tab) => tab.name === target) ? target : fallback
}

async function loadOverview() {
  overviewLoading.value = true
  try {
    const requests = [
      getReservationList({ page: 1, pageSize: 1, status: 'pending' }),
      canViewBorrow.value ? getBorrowRequests({ page: 1, pageSize: 1, status: 'pending' }) : Promise.resolve(null),
      canViewBorrow.value ? getBorrowRenewRequests({ status: 'pending' }) : Promise.resolve(null),
      canViewRules.value ? getReservationRules() : Promise.resolve(null)
    ]

    const [reservationResp, borrowResp, renewResp, rulesResp] = await Promise.all(requests)
    reservationPending.value = Number(reservationResp?.data?.meta?.total || 0)
    borrowPending.value = Number(borrowResp?.data?.meta?.total || 0)
    renewPending.value = Array.isArray(renewResp?.data?.data) ? renewResp.data.data.length : 0

    const mode = String(rulesResp?.data?.data?.global?.approval?.mode || '').trim()
    approvalMode.value = mode === 'teacher' ? '教师审批' : mode === 'auto' ? '自动通过' : mode === 'admin' ? '管理员审批' : '-'
  } finally {
    overviewLoading.value = false
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
.approval-center {
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
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.14), transparent 32%),
    linear-gradient(135deg, #fbfdff 0%, #f0f7ff 100%);
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
  background: rgba(37, 99, 235, 0.12);
  color: #1d4ed8;
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

:deep(.approval-tabs > .el-tabs__content) {
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
