import request from '@/utils/request'

export function getTodoCenter(params = {}) {
  return request.get('/admin/todo-center', { params })
}

export function reviewLostFoundClaim(id, payload = {}) {
  return request.post(`/lostfound/${id}/claim-review`, payload)
}

export function notifyMissingCourseTask(courseId, taskId) {
  return request.post(`/teacher/courses/${courseId}/tasks/${taskId}/notify-missing`, {})
}
