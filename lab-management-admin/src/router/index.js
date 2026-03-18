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
        meta: { title: '仪表盘', roles: ['admin', 'teacher'] }
      },
      {
        path: 'todo-center',
        name: 'todoCenter',
        component: () => import('@/views/todo-center/index.vue'),
        meta: { title: '待办中心', roles: ['admin'] }
      },
      {
        path: 'notification-center',
        name: 'notificationCenter',
        component: () => import('@/views/notification-center/index.vue'),
        meta: { title: '通知中心', roles: ['admin'] }
      },
      {
        path: 'operations-board',
        name: 'operationsBoard',
        component: () => import('@/views/operations-board/index.vue'),
        meta: { title: '运营看板', roles: ['admin', 'teacher'], permissions: [PERMISSION_DUTY_OPERATOR] }
      },
      {
        path: 'duty-emergency',
        name: 'dutyEmergency',
        component: () => import('@/views/duty-emergency/index.vue'),
        meta: { title: '值班应急', roles: ['admin'], permissions: [PERMISSION_DUTY_OPERATOR] }
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
        component: () => import('@/views/ai-assistant/index.vue'),
        meta: { title: 'AI 助手', roles: ['admin'] }
      },
      {
        path: 'knowledge-base',
        name: 'knowledgeBase',
        component: () => import('@/views/knowledge-base/index.vue'),
        meta: { title: '知识库管理', roles: ['admin'] }
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
        path: 'reservations',
        name: 'reservations',
        component: () => import('@/views/reservations/index.vue'),
        meta: { title: '预约审批', roles: ['admin', 'teacher'] }
      },
      {
        path: 'borrow-approval',
        name: 'borrowApproval',
        component: () => import('@/views/borrow-approval/index.vue'),
        meta: { title: '借用审批', roles: ['admin'], permissions: [PERMISSION_ASSET_MANAGER] }
      },
      {
        path: 'equipments',
        name: 'equipments',
        component: () => import('@/views/equipments/index.vue'),
        meta: { title: '资产管理', roles: ['admin'], permissions: [PERMISSION_ASSET_MANAGER] }
      },
      {
        path: 'reservation-rules',
        name: 'reservationRules',
        component: () => import('@/views/reservation-rules/index.vue'),
        meta: { title: '审批流配置', roles: ['admin'], permissions: [PERMISSION_SCHEDULE_MANAGER] }
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
