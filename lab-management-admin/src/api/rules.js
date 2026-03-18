import request from '@/utils/request'

export function getReservationRules() {
  return request.get('/admin/reservation-rules')
}

export function saveReservationRules(payload = {}) {
  return request.post('/admin/reservation-rules', payload)
}

export function getReservationPriorityRules() {
  return request.get('/admin/reservation-priority-rules')
}

export function saveReservationPriorityRules(payload = {}) {
  return request.post('/admin/reservation-priority-rules', payload)
}

export function previewReservationPriority(payload = {}) {
  return request.post('/admin/reservation-priority-preview', payload)
}

export function getReservationWaitlist(params = {}) {
  return request.get('/reservations/waitlist', { params })
}

export function cancelReservationWaitlist(id) {
  return request.post(`/reservations/waitlist/${id}/cancel`, {})
}

export function promoteReservationWaitlist(id) {
  return request.post(`/admin/reservation-waitlist/${id}/promote`, {})
}
