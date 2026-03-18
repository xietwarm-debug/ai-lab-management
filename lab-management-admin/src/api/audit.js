import { buildApiUrl } from '@/utils/request'
import request from '@/utils/request'

export function getAuditLogs(params = {}) {
  return request.get('/audit-logs', { params })
}

export function getAuditExportUrl(params = {}) {
  return buildApiUrl('/audit-logs/export', params)
}
