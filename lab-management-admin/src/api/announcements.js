import request from '@/utils/request'

export function getAdminAnnouncements(params) {
  return request.get('/admin/announcements', { params })
}

export function createAnnouncement(payload) {
  return request.post('/announcements', payload)
}

export function updateAnnouncement(id, payload) {
  return request.put(`/announcements/${id}`, payload)
}

export function pinAnnouncement(id, payload) {
  return request.post(`/announcements/${id}/pin`, payload)
}

export function deleteAnnouncement(id) {
  return request.delete(`/announcements/${id}`)
}

export function createAnnouncementDraft(payload) {
  return request.post('/announcements/ai-draft', payload)
}
