import request, { buildApiUrl } from '@/utils/request'

export function getReportCenter(params) {
  return request.get('/admin/reports/center', { params })
}

export function getReportExportUrl(params) {
  return buildApiUrl('/admin/reports/center/export', params)
}

export function exportReportFile(params) {
  return request.get('/admin/reports/center/export', {
    params,
    responseType: 'blob'
  })
}
