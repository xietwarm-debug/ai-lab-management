import request from '@/utils/request'

export function getWorkbenchOverview() {
  return request.get('/overview')
}

export function getAdminDashboard() {
  return request.get('/admin/stats/dashboard')
}
