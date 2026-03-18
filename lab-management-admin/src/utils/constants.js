export const APP_TITLE = import.meta.env.VITE_APP_TITLE || 'AI实验室管理助手后台'
export const TOKEN_KEY = 'lab_admin_access_token'
export const REFRESH_TOKEN_KEY = 'lab_admin_refresh_token'
export const USER_KEY = 'lab_admin_user'

export const ROLE_ADMIN = 'admin'
export const ROLE_TEACHER = 'teacher'
export const ROLE_STUDENT = 'student'

export const PERMISSION_DUTY_OPERATOR = 'duty.operator'
export const PERMISSION_ASSET_MANAGER = 'asset.manager'
export const PERMISSION_SCHEDULE_MANAGER = 'schedule.manager'
export const PERMISSION_AUDIT_VIEWER = 'audit.viewer'

export const ROLE_LABEL_MAP = {
  admin: '管理员',
  teacher: '教师',
  student: '学生'
}

export const PERMISSION_LABEL_MAP = {
  [PERMISSION_DUTY_OPERATOR]: '值班员',
  [PERMISSION_ASSET_MANAGER]: '资产管理员',
  [PERMISSION_SCHEDULE_MANAGER]: '排课管理员',
  [PERMISSION_AUDIT_VIEWER]: '审计查看员'
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
    key: 'operationsBoard',
    label: '运营看板',
    icon: 'TrendCharts',
    path: '/operations-board',
    roles: [ROLE_ADMIN, ROLE_TEACHER],
    permissions: [PERMISSION_DUTY_OPERATOR]
  },
  {
    key: 'todoCenter',
    label: '待办中心',
    icon: 'Memo',
    path: '/todo-center',
    roles: [ROLE_ADMIN]
  },
  {
    key: 'notificationCenter',
    label: '通知中心',
    icon: 'Bell',
    path: '/notification-center',
    roles: [ROLE_ADMIN]
  },
  {
    key: 'dutyEmergency',
    label: '值班应急',
    icon: 'Warning',
    path: '/duty-emergency',
    roles: [ROLE_ADMIN],
    permissions: [PERMISSION_DUTY_OPERATOR]
  },
  {
    key: 'lostFound',
    label: '失物招领',
    icon: 'Box',
    path: '/lostfound',
    roles: [ROLE_ADMIN]
  },
  {
    key: 'aiAssistant',
    label: 'AI 助手',
    icon: 'ChatDotRound',
    path: '/ai-assistant',
    roles: [ROLE_ADMIN]
  },
  {
    key: 'knowledgeBase',
    label: '知识库',
    icon: 'Document',
    path: '/knowledge-base',
    roles: [ROLE_ADMIN]
  },
  {
    key: 'labs',
    label: '实验室管理',
    icon: 'OfficeBuilding',
    path: '/labs',
    roles: [ROLE_ADMIN]
  },
  {
    key: 'roomMap',
    label: '平面图管理',
    icon: 'Grid',
    path: '/room-map',
    roles: [ROLE_ADMIN]
  },
  {
    key: 'scheduleManage',
    label: '排课管理',
    icon: 'Reading',
    path: '/schedule-manage',
    roles: [ROLE_ADMIN],
    permissions: [PERMISSION_SCHEDULE_MANAGER]
  },
  {
    key: 'reservations',
    label: '预约审批',
    icon: 'Calendar',
    path: '/reservations',
    roles: [ROLE_ADMIN, ROLE_TEACHER]
  },
  {
    key: 'reservationRules',
    label: '审批流配置',
    icon: 'Operation',
    path: '/reservation-rules',
    roles: [ROLE_ADMIN],
    permissions: [PERMISSION_SCHEDULE_MANAGER]
  },
  {
    key: 'borrowApproval',
    label: '借用审批',
    icon: 'DocumentChecked',
    path: '/borrow-approval',
    roles: [ROLE_ADMIN],
    permissions: [PERMISSION_ASSET_MANAGER]
  },
  {
    key: 'equipments',
    label: '资产管理',
    icon: 'Monitor',
    path: '/equipments',
    roles: [ROLE_ADMIN],
    permissions: [PERMISSION_ASSET_MANAGER]
  },
  {
    key: 'dataGovernance',
    label: '导入治理',
    icon: 'UploadFilled',
    path: '/data-governance',
    roles: [ROLE_ADMIN],
    permissions: [PERMISSION_ASSET_MANAGER, PERMISSION_SCHEDULE_MANAGER]
  },
  {
    key: 'repairs',
    label: '报修工单',
    icon: 'Tools',
    path: '/repairs',
    roles: [ROLE_ADMIN]
  },
  {
    key: 'announcements',
    label: '公告管理',
    icon: 'BellFilled',
    path: '/announcements',
    roles: [ROLE_ADMIN]
  },
  {
    key: 'auditLogs',
    label: '审计日志',
    icon: 'Tickets',
    path: '/audit-logs',
    roles: [ROLE_ADMIN],
    permissions: [PERMISSION_AUDIT_VIEWER]
  },
  {
    key: 'users',
    label: '用户管理',
    icon: 'User',
    path: '/users',
    roles: [ROLE_ADMIN]
  },
  {
    key: 'permissionCenter',
    label: '权限中心',
    icon: 'Lock',
    path: '/permission-center',
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
