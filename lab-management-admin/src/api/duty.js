import request from '@/utils/request'

export function getDutyRoster(params = {}) {
  return request.get('/admin/duty-roster', { params })
}

export function saveDutyRoster(payload = {}) {
  return request.post('/admin/duty-roster', payload)
}

export function updateDutyRosterStatus(id, payload = {}) {
  return request.post(`/admin/duty-roster/${id}/status`, payload)
}

export function getEmergencyContacts(params = {}) {
  return request.get('/admin/emergency-contacts', { params })
}

export function saveEmergencyContact(payload = {}) {
  return request.post('/admin/emergency-contacts', payload)
}

export function deleteEmergencyContact(id) {
  return request.post(`/admin/emergency-contacts/${id}/delete`, {})
}

export function getIncidents(params = {}) {
  return request.get('/admin/incidents', { params })
}

export function saveIncident(payload = {}) {
  return request.post('/admin/incidents', payload)
}

export function updateIncidentStatus(id, payload = {}) {
  return request.post(`/admin/incidents/${id}/status`, payload)
}
