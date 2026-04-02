import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { isAllowedAccess } from '@/utils/auth'
import {
  APP_TITLE,
  PERMISSION_ASSET_MANAGER,
  PERMISSION_AUDIT_VIEWER,
  PERMISSION_DUTY_OPERATOR,
  PERMISSION_SCHEDULE_MANAGER
} from '@/utils/constants'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/login/index.vue'),
    meta: {
      title: '登录'
    }
  },
  {
    path: '/',
    component: () => import('@/layout/AdminLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '\u4eea\u8868\u76d8', roles: ['admin', 'teacher'] }
      },
      {
        path: 'operations-center',
        name: 'operationsCenter',
        component: () => import('@/views/operations-center/index.vue'),
        meta: { title: '\u8fd0\u8425\u4e2d\u5fc3', roles: ['admin', 'teacher'], permissions: [PERMISSION_DUTY_OPERATOR] }
      },
      {
        path: 'todo-center',
        name: 'todoCenter',
        redirect: {
          path: '/operations-center',
          query: { tab: 'todo' }
        },
        meta: { title: '\u5f85\u529e\u4e2d\u5fc3', roles: ['admin'] }
      },
      {
        path: 'notification-center',
        name: 'notificationCenter',
        component: () => import('@/views/notification-center/index.vue'),
        meta: { title: '\u901a\u77e5\u4e2d\u5fc3', roles: ['admin'] }
      },
      {
        path: 'operations-board',
        name: 'operationsBoard',
        redirect: {
          path: '/operations-center',
          query: { tab: 'board' }
        },
        meta: { title: '\u8fd0\u8425\u770b\u677f', roles: ['admin', 'teacher'], permissions: [PERMISSION_DUTY_OPERATOR] }
      },
      {
        path: 'duty-emergency',
        name: 'dutyEmergency',
        redirect: {
          path: '/operations-center',
          query: { tab: 'duty' }
        },
        meta: { title: '\u503c\u73ed\u5e94\u6025', roles: ['admin'], permissions: [PERMISSION_DUTY_OPERATOR] }
      },
      {
        path: 'lostfound',
        name: 'lostFound',
        component: () => import('@/views/lostfound/index.vue'),
        meta: { title: '失物招领', roles: ['admin'] }
      },
      {
        path: 'ai-assistant',
        name: 'aiAssistant',
        redirect: (to) => ({
          path: '/ai-knowledge-center',
          query: { ...to.query, tab: 'assistant' }
        }),
        meta: { title: 'AI 助手', roles: ['admin'] }
      },
      {
        path: 'knowledge-base',
        name: 'knowledgeBase',
        redirect: (to) => ({
          path: '/ai-knowledge-center',
          query: { ...to.query, tab: 'knowledge' }
        }),
        meta: { title: '知识库管理', roles: ['admin'] }
      },
      {
        path: 'ai-knowledge-center',
        name: 'aiKnowledgeCenter',
        component: () => import('@/views/ai-knowledge-center/index.vue'),
        meta: { title: 'AI 知识助手', roles: ['admin'] }
      },
      {
        path: 'labs',
        name: 'labs',
        component: () => import('@/views/labs/index.vue'),
        meta: { title: '实验室管理', roles: ['admin'] }
      },
      {
        path: 'room-map',
        name: 'roomMap',
        component: () => import('@/views/room-map/index.vue'),
        meta: { title: '平面图管理', roles: ['admin'] }
      },
      {
        path: 'schedule-manage',
        name: 'scheduleManage',
        component: () => import('@/views/schedule-manage/index.vue'),
        meta: { title: '排课管理', roles: ['admin'], permissions: [PERMISSION_SCHEDULE_MANAGER] }
      },
      {
        path: 'approval-center',
        name: 'approvalCenter',
        component: () => import('@/views/approval-center/index.vue'),
        meta: { title: '\u5ba1\u6279\u4e2d\u5fc3', roles: ['admin', 'teacher'] }
      },
      {
        path: 'reservations',
        name: 'reservations',
        redirect: {
          path: '/approval-center',
          query: { tab: 'reservations' }
        },
        meta: { title: '\u9884\u7ea6\u5ba1\u6279', roles: ['admin', 'teacher'] }
      },
      {
        path: 'borrow-approval',
        name: 'borrowApproval',
        redirect: {
          path: '/approval-center',
          query: { tab: 'borrow' }
        },
        meta: { title: '\u501f\u7528\u5ba1\u6279', roles: ['admin'], permissions: [PERMISSION_ASSET_MANAGER] }
      },
      {
        path: 'equipments',
        name: 'equipments',
        component: () => import('@/views/equipments/index.vue'),
        meta: { title: '\u8d44\u4ea7\u7ba1\u7406', roles: ['admin'], permissions: [PERMISSION_ASSET_MANAGER] }
      },
      {
        path: 'warehouses',
        name: 'warehouses',
        component: () => import('@/views/warehouses/index.vue'),
        meta: { title: '仓库管理', roles: ['admin'], permissions: [PERMISSION_ASSET_MANAGER] }
      },
      {
        path: 'reservation-rules',
        name: 'reservationRules',
        redirect: {
          path: '/approval-center',
          query: { tab: 'rules' }
        },
        meta: { title: '\u5ba1\u6279\u6d41\u914d\u7f6e', roles: ['admin'], permissions: [PERMISSION_SCHEDULE_MANAGER] }
      },
      {
        path: 'data-governance',
        name: 'dataGovernance',
        component: () => import('@/views/data-governance/index.vue'),
        meta: { title: '导入治理', roles: ['admin'], permissions: [PERMISSION_ASSET_MANAGER, PERMISSION_SCHEDULE_MANAGER] }
      },
      {
        path: 'repairs',
        name: 'repairs',
        component: () => import('@/views/repairs/index.vue'),
        meta: { title: '报修工单', roles: ['admin'] }
      },
      {
        path: 'announcements',
        name: 'announcements',
        component: () => import('@/views/announcements/index.vue'),
        meta: { title: '公告管理', roles: ['admin'] }
      },
      {
        path: 'audit-logs',
        name: 'auditLogs',
        component: () => import('@/views/audit-logs/index.vue'),
        meta: { title: '审计日志', roles: ['admin'], permissions: [PERMISSION_AUDIT_VIEWER] }
      },
      {
        path: 'users',
        name: 'users',
        component: () => import('@/views/users/index.vue'),
        meta: { title: '用户管理', roles: ['admin'] }
      },
      {
        path: 'permission-center',
        name: 'permissionCenter',
        component: () => import('@/views/permission-center/index.vue'),
        meta: { title: '权限中心', roles: ['admin'] }
      },
      {
        path: 'reports',
        name: 'reports',
        component: () => import('@/views/reports/index.vue'),
        meta: { title: '报表中心', roles: ['admin'] }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const authStore = useAuthStore()
  const appStore = useAppStore()
  authStore.restore()
  appStore.setTitle(`${APP_TITLE} · ${to.meta?.title || '管理后台'}`)

  if (to.path === '/login') {
    if (authStore.isLoggedIn) {
      return '/dashboard'
    }
    return true
  }

  if (!authStore.isLoggedIn) {
    return {
      path: '/login',
      query: {
        redirect: to.fullPath
      }
    }
  }

  if (!isAllowedAccess(authStore.user, to.meta || {})) {
    return '/dashboard'
  }

  return true
})

export default router
