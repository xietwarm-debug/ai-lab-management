import request from '@/utils/request'

export function getReservationList(params) {
  return request.get('/reservations', { params })
}

export function getReservationDetail(id) {
  return request.get(`/reservations/${id}`)
}

export function approveReservation(id) {
  return request.post(`/reservations/${id}/approve`)
}

export function rejectReservation(id, payload) {
  return request.post(`/reservations/${id}/reject`, payload)
}

export function batchApproveReservations(ids) {
  return request.post('/reservations/batch', {
    action: 'approve',
    ids
  })
}

export function addReservationNote(id, payload) {
  return request.post(`/reservations/${id}/note`, payload)
}

export function getReservationAiSuggestion(id) {
  return request.get(`/reservations/${id}/ai-suggestion`)
}
