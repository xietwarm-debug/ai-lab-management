import request from '@/utils/request'

export function getWarehouses(params) {
  return request({
    url: '/admin/warehouses',
    method: 'get',
    params
  })
}

export function createWarehouse(data) {
  return request({
    url: '/admin/warehouses',
    method: 'post',
    data
  })
}

export function updateWarehouse(id, data) {
  return request({
    url: `/admin/warehouses/${id}`,
    method: 'put',
    data
  })
}

export function deleteWarehouse(id) {
  return request({
    url: `/admin/warehouses/${id}`,
    method: 'delete'
  })
}

export function transferAssets(data) {
  return request({
    url: '/admin/assets/transfer',
    method: 'post',
    data
  })
}

export function getAssetTransfers(id) {
  return request({
    url: `/admin/assets/${id}/transfers`,
    method: 'get'
  })
}
