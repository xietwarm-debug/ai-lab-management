import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { isAllowedRole } from '@/utils/auth'

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
        meta: {
          title: '仪表盘',
          roles: ['admin', 'teacher']
        }
      },
      {
        path: 'ai-assistant',
        name: 'aiAssistant',
        component: () => import('@/views/ai-assistant/index.vue'),
        meta: {
          title: 'AI 助手',
          roles: ['admin']
        }
      },
      {
        path: 'reservations',
        name: 'reservations',
        component: () => import('@/views/reservations/index.vue'),
        meta: {
          title: '预约审批管理',
          roles: ['admin', 'teacher']
        }
      },
      {
        path: 'equipments',
        name: 'equipments',
        component: () => import('@/views/equipments/index.vue'),
        meta: {
          title: '设备管理',
          roles: ['admin']
        }
      },
      {
        path: 'repairs',
        name: 'repairs',
        component: () => import('@/views/repairs/index.vue'),
        meta: {
          title: '报修工单管理',
          roles: ['admin']
        }
      },
      {
        path: 'announcements',
        name: 'announcements',
        component: () => import('@/views/announcements/index.vue'),
        meta: {
          title: '公告管理',
          roles: ['admin']
        }
      },
      {
        path: 'users',
        name: 'users',
        component: () => import('@/views/users/index.vue'),
        meta: {
          title: '用户管理',
          roles: ['admin']
        }
      },
      {
        path: 'reports',
        name: 'reports',
        component: () => import('@/views/reports/index.vue'),
        meta: {
          title: '报表中心',
          roles: ['admin']
        }
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
  appStore.setTitle(`AI实验室管理助手后台 · ${to.meta?.title || '管理后台'}`)

  if (to.path === '/login') {
    if (authStore.isLoggedIn) {
      return authStore.role === 'teacher' ? '/dashboard' : '/dashboard'
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

  if (!isAllowedRole(authStore.role, to.meta?.roles || [])) {
    return '/dashboard'
  }

  return true
})

export default router
