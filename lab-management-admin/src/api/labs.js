import request from '@/utils/request'

export function getLabs(params) {
  return request.get('/labs', { params })
}
