export function resolveAdminJumpUrl(rawUrl = '') {
  const raw = String(rawUrl || '').trim()
  if (!raw) return ''

  const [pathPart, searchPart = ''] = raw.split('?')
  const withQuery = (path) => (searchPart ? `${path}?${searchPart}` : path)

  if (pathPart.startsWith('/pages/admin/approve')) return withQuery('/reservations')
  if (pathPart.startsWith('/pages/admin/equipments')) return withQuery('/equipments')
  if (pathPart.startsWith('/pages/admin/borrow_approval')) return withQuery('/borrow-approval')
  if (pathPart.startsWith('/pages/admin/lostfound')) return withQuery('/lostfound')
  if (pathPart.startsWith('/pages/admin/labs')) return withQuery('/labs')
  if (pathPart.startsWith('/pages/admin/room_map')) return withQuery('/room-map')
  if (pathPart.startsWith('/pages/admin/knowledge_base')) return withQuery('/knowledge-base')
  if (pathPart.startsWith('/pages/admin/schedule_')) return withQuery('/schedule-manage')
  if (pathPart.startsWith('/pages/admin/door_')) return withQuery('/schedule-manage')
  if (pathPart.startsWith('/pages/admin/reservation_rules')) return withQuery('/reservation-rules')
  if (pathPart.startsWith('/pages/admin/reservation_priority')) return withQuery('/reservation-rules')
  if (pathPart.startsWith('/pages/admin/audit')) return withQuery('/audit-logs')
  if (pathPart.startsWith('/pages/admin/users')) return withQuery('/users')
  if (pathPart.startsWith('/pages/admin/announcements')) return withQuery('/announcements')
  if (pathPart.startsWith('/pages/admin/repairs')) return withQuery('/repairs')
  if (pathPart.startsWith('/pages/admin/stats')) return withQuery('/operations-board')
  if (pathPart.startsWith('/pages/admin/todo_center')) return withQuery('/todo-center')
  if (pathPart.startsWith('/pages/admin')) return withQuery('/dashboard')

  return raw.startsWith('/') ? raw : ''
}
