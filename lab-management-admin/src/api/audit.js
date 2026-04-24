import { buildApiUrl } from '@/utils/request'
import request from '@/utils/request'

export function getAuditLogs(params = {}) {
  return request.get('/audit-logs', { params })
}

export function getAuditExportUrl(params = {}) {
  return buildApiUrl('/audit-logs/export', params)
}

export function explainAuditLogsAi(payload = {}) {
  return request.post('/admin/audit-logs/ai-explain', payload, {
    timeout: 45000,
    silentError: true
  })
}
