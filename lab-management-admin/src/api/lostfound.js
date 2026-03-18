import request from '@/utils/request'

export function getLostFoundList(params = {}) {
  return request.get('/lostfound', { params })
}

export function reviewLostFoundClaim(id, payload = {}) {
  return request.post(`/lostfound/${id}/claim-review`, payload)
}

export function updateLostFoundStatus(id, payload = {}) {
  return request.post(`/lostfound/${id}/status`, payload)
}

export function deleteLostFoundItem(id) {
  return request.post(`/lostfound/${id}/delete`)
}
