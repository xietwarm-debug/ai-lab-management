export const APP_TITLE = import.meta.env.VITE_APP_TITLE || 'AI实验室管理助手后台'
export const TOKEN_KEY = 'lab_admin_access_token'
export const REFRESH_TOKEN_KEY = 'lab_admin_refresh_token'
export const USER_KEY = 'lab_admin_user'

export const ROLE_ADMIN = 'admin'
export const ROLE_TEACHER = 'teacher'

export const ROLE_LABEL_MAP = {
  admin: '管理员',
  teacher: '教师',
  student: '学生'
}

export const MENU_ITEMS = [
  {
    key: 'dashboard',
    label: '仪表盘',
    icon: 'DataBoard',
    path: '/dashboard',
    roles: [ROLE_ADMIN, ROLE_TEACHER]
  },
  {
    key: 'aiAssistant',
    label: 'AI 助手',
    icon: 'ChatDotRound',
    path: '/ai-assistant',
    roles: [ROLE_ADMIN]
  },
  {
    key: 'reservations',
    label: '预约审批管理',
    icon: 'Calendar',
    path: '/reservations',
    roles: [ROLE_ADMIN, ROLE_TEACHER]
  },
  {
    key: 'equipments',
    label: '设备管理',
    icon: 'Monitor',
    path: '/equipments',
    roles: [ROLE_ADMIN]
  },
  {
    key: 'repairs',
    label: '报修工单管理',
    icon: 'Tools',
    path: '/repairs',
    roles: [ROLE_ADMIN]
  },
  {
    key: 'announcements',
    label: '公告管理',
    icon: 'Bell',
    path: '/announcements',
    roles: [ROLE_ADMIN]
  },
  {
    key: 'users',
    label: '用户管理',
    icon: 'User',
    path: '/users',
    roles: [ROLE_ADMIN]
  },
  {
    key: 'reports',
    label: '报表中心',
    icon: 'Histogram',
    path: '/reports',
    roles: [ROLE_ADMIN]
  }
]
