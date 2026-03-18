import request from '@/utils/request'

export function getLabs(params = {}) {
  return request.get('/labs', { params })
}

export function getLabSensorStatus(params = {}) {
  return request.get('/labs/sensor-status', { params })
}

export function createLab(payload = {}) {
  return request.post('/labs', payload)
}

export function updateLab(id, payload = {}) {
  return request.post(`/labs/${id}`, payload)
}

export function deleteLab(id) {
  return request.post(`/labs/${id}/delete`)
}

export function uploadLabImage(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}
