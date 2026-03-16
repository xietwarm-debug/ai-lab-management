import request from '@/utils/request'

export function loginApi(payload) {
  return request.post('/login', payload, {
    headers: {
      Authorization: ''
    }
  })
}

export function logoutApi(payload) {
  return request.post('/auth/logout', payload, {
    silentError: true
  })
}

export function refreshTokenApi(payload) {
  return request.post('/auth/refresh', payload, {
    headers: {
      Authorization: ''
    }
  })
}
