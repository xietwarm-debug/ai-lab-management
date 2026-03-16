import request from '@/utils/request'

export function getRepairOrders(params) {
  return request.get('/repair-orders', { params })
}

export function getRepairOrderDetail(id) {
  return request.get(`/repair-orders/${id}`)
}

export function updateRepairOrderStatus(id, payload) {
  return request.post(`/repair-orders/${id}/status`, payload)
}
