import request from '@/utils/request'

export function getLabPcRuntimeStatus(params = {}) {
  return request.get('/pcs/status', { params })
}
