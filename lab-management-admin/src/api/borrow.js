import request from '@/utils/request'

export function getBorrowRequests(params = {}) {
  return request.get('/borrow-requests', { params })
}

export function getBorrowRequestDetail(id) {
  return request.get(`/borrow-requests/${id}`)
}

export function approveBorrowRequest(id, payload = {}) {
  return request.post(`/borrow-requests/${id}/approve`, payload)
}

export function rejectBorrowRequest(id, payload = {}) {
  return request.post(`/borrow-requests/${id}/reject`, payload)
}

export function noteBorrowRequest(id, payload = {}) {
  return request.post(`/borrow-requests/${id}/note`, payload)
}

export function remindBorrowRequest(id, payload = {}) {
  return request.post(`/borrow-requests/${id}/remind`, payload)
}

export function aiRemindBorrowRequest(id) {
  return request.post(`/borrow-requests/${id}/ai-remind`, {})
}

export function markBorrowReturned(id, payload = {}) {
  return request.post(`/borrow-requests/${id}/mark-returned`, payload)
}

export function scanReturnBorrowRequest(payload = {}) {
  return request.post('/borrow-requests/scan-return', payload)
}

export function getBorrowRenewRequests(params = {}) {
  return request.get('/borrow-requests/extensions', { params })
}

export function approveBorrowRenewRequest(id, payload = {}) {
  return request.post(`/borrow-requests/extensions/${id}/approve`, payload)
}

export function rejectBorrowRenewRequest(id, payload = {}) {
  return request.post(`/borrow-requests/extensions/${id}/reject`, payload)
}

export function getBorrowCompensations(params = {}) {
  return request.get('/borrow-compensations', { params })
}

export function createBorrowCompensation(id, payload = {}) {
  return request.post(`/borrow-requests/${id}/compensations`, payload)
}

export function updateBorrowCompensationStatus(id, payload = {}) {
  return request.post(`/borrow-compensations/${id}/status`, payload)
}
