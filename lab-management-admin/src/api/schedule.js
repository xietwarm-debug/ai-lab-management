import request from '@/utils/request'

export function getScheduleTemplates() {
  return request.get('/admin/schedule/templates')
}

export function getScheduleTemplateDetail(id) {
  return request.get(`/admin/schedule/templates/${id}`)
}

export function activateScheduleTemplate(id) {
  return request.post(`/admin/schedule/templates/${id}/activate`, {})
}

export function deleteScheduleTemplate(id) {
  return request.post(`/admin/schedule/templates/${id}/delete`, {})
}

export function importSchedule(payload = {}) {
  return request.post('/admin/schedule/import', payload)
}

export function getDoorRemindersToday(params = {}) {
  return request.get('/admin/door-reminders/today', { params })
}

export function getDoorRemindersWeek(params = {}) {
  return request.get('/admin/door-reminders/week', { params })
}

export function getDoorReminderRecords(params = {}) {
  return request.get('/admin/door-reminders/records', { params })
}

export function confirmDoorReminderOpen(id, payload = {}) {
  return request.post(`/admin/door-reminders/${id}/confirm-open`, payload)
}

export function ignoreDoorReminder(id, payload = {}) {
  return request.post(`/admin/door-reminders/${id}/ignore`, payload)
}

export function getLabScheduleDay(labId, params = {}) {
  return request.get(`/admin/labs/${labId}/schedule/day`, { params })
}

export function getLabScheduleWeek(labId, params = {}) {
  return request.get(`/admin/labs/${labId}/schedule/week`, { params })
}
