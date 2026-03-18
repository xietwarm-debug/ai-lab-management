import request from '@/utils/request'

export function getEquipmentList(params) {
  return request.get('/equipments', { params })
}

export function getEquipmentDetail(id) {
  return request.get(`/equipments/${id}`)
}

export function createEquipment(payload) {
  return request.post('/equipments', payload)
}

export function updateEquipment(id, payload) {
  return request.post(`/equipments/${id}`, payload)
}

export function deleteEquipment(id) {
  return request.post(`/equipments/${id}/delete`)
}

export function getEquipmentEvents(id, params = {}) {
  return request.get(`/equipments/${id}/events`, { params })
}

export function createEquipmentEvent(id, payload = {}) {
  return request.post(`/equipments/${id}/events`, payload)
}

export function updateEquipmentMaintenancePlan(id, payload = {}) {
  return request.post(`/equipments/${id}/maintenance-plan`, payload)
}

export function getDueMaintenanceEquipments(params = {}) {
  return request.get('/equipments/maintenance/due', { params })
}

export function getEquipmentCode(id) {
  return request.get(`/equipments/${id}/code`)
}

export function scrapEquipment(id, payload = {}) {
  return request.post(`/equipments/${id}/scrap`, payload)
}

export function transferEquipment(id, payload = {}) {
  return request.post(`/equipments/${id}/transfer`, payload)
}
