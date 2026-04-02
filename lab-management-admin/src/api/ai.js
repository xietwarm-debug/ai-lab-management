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
  return request.post('/agent/chat', payload, {
    timeout: 45000,
    silentError: true
  })
}

export function getAgentHistory(params = {}) {
  return request.get('/agent/history', {
    params
  })
}

export function clearAgentHistory(payload = {}) {
  return request.post('/agent/history/clear', payload)
}

export function uploadAgentFile(formData) {
  return request.post('/agent/files/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    timeout: 60000
  })
}

export function getAgentFiles() {
  return request.get('/agent/files')
}

export function deleteAgentFile(id) {
  return request.delete(`/agent/files/${id}`)
}

export function toggleAgentFileKnowledge(id, payload = {}) {
  return request.post(`/agent/files/${id}/knowledge`, payload)
}

export function executeAgentImport(payload = {}) {
  return request.post('/agent/import-assets/execute', payload)
}
