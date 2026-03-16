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
