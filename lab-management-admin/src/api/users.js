import request from '@/utils/request'

export function getUsers(params) {
  return request.get('/users', { params })
}

export function getUserGovernanceStats(params) {
  return request.get('/users/governance-stats', { params })
}

export function createUser(payload) {
  return request.post('/users', payload)
}

export function batchGenerateStudents(payload) {
  return request.post('/users/batch-generate-students', payload)
}

export function getUserDetail(id, params) {
  return request.get(`/users/${id}/detail`, { params })
}

export function getUserAiPermissions(id) {
  return request.get(`/users/${id}/ai-permissions`)
}

export function grantUserAiPermission(id, payload) {
  return request.post(`/users/${id}/ai-permissions/grant`, payload)
}

export function revokeUserAiPermission(id, payload) {
  return request.post(`/users/${id}/ai-permissions/revoke`, payload)
}

export function setUserRole(id, payload) {
  return request.post(`/users/${id}/set-role`, payload)
}

export function freezeUser(id) {
  return request.post(`/users/${id}/freeze`)
}

export function unfreezeUser(id) {
  return request.post(`/users/${id}/unfreeze`)
}

export function resetUserPassword(id, payload = {}) {
  return request.post(`/users/${id}/reset-password`, payload)
}

export function deleteUser(id) {
  return request.post(`/users/${id}/delete`)
}

export function importUsers(payload) {
  return request.post('/users/import', payload)
}

export function batchDeactivateGraduates(payload) {
  return request.post('/users/batch-deactivate-graduates', payload)
}
