import request from '@/utils/request'

export function getAdminAiDailyBrief() {
  return request.get('/admin/ai/daily-brief')
}

export function queryAdminStatsAi(payload = {}) {
  return request.post('/admin/stats/ai-query', payload)
}

export function getAdminAiRiskAlerts() {
  return request.get('/admin/ai/risk-alerts')
}

export function getAdminAiEquipmentHealth(params = {}) {
  return request.get('/admin/ai/equipment-health', {
    params
  })
}

export function refreshAdminAiEquipmentHealth(payload = {}) {
  return request.post('/admin/ai/equipment-health/refresh', payload)
}

export function chatWithAgent(payload = {}) {
  return request.post('/agent/chat', payload)
}

export function getAgentHistory(params = {}) {
  return request.get('/agent/history', {
    params
  })
}

export function clearAgentHistory(payload = {}) {
  return request.post('/agent/history/clear', payload)
}
