import axios from 'axios'
import { ElMessage } from 'element-plus'
import { clearSession, getAccessToken, getRefreshToken, saveSession } from './auth'

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000'

const request = axios.create({
  baseURL,
  timeout: 15000
})

let refreshPromise = null

function isRefreshEndpoint(config = {}) {
  const url = String(config.url || '')
  return url.includes('/auth/refresh')
}

function redirectToLogin() {
  if (typeof window === 'undefined') return
  const currentPath = `${window.location.pathname || '/'}${window.location.search || ''}`
  const redirect = encodeURIComponent(currentPath)
  if (!window.location.pathname.startsWith('/login')) {
    window.location.href = `/login?redirect=${redirect}`
  }
}

async function refreshAccessToken() {
  if (refreshPromise) return refreshPromise

  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    return false
  }

  refreshPromise = request.post('/auth/refresh', { refreshToken }, {
    headers: {
      Authorization: ''
    }
  }).then((response) => {
    const payload = response.data || {}
    if (!payload.ok || !payload.data) {
      clearSession()
      return false
    }
    saveSession(payload.data)
    return true
  }).catch(() => {
    clearSession()
    return false
  }).finally(() => {
    refreshPromise = null
  })

  return refreshPromise
}

export function buildApiUrl(path = '', params = null) {
  const normalizedBase = String(baseURL || '').replace(/\/+$/, '')
  const normalizedPath = String(path || '').startsWith('/') ? String(path || '') : `/${String(path || '')}`
  const searchParams = new URLSearchParams()

  if (params && typeof params === 'object') {
    Object.keys(params).forEach((key) => {
      const value = params[key]
      if (value === undefined || value === null || value === '') return
      searchParams.set(key, String(value))
    })
  }

  const queryString = searchParams.toString()
  const resolvedPath = `${normalizedBase}${normalizedPath}`
  return queryString ? `${resolvedPath}?${queryString}` : resolvedPath
}

request.interceptors.request.use((config) => {
  const nextConfig = { ...config }
  nextConfig.headers = nextConfig.headers || {}

  const token = getAccessToken()
  if (token && !Object.prototype.hasOwnProperty.call(nextConfig.headers, 'Authorization')) {
    nextConfig.headers.Authorization = `Bearer ${token}`
  }

  return nextConfig
})

request.interceptors.response.use(
  async (response) => {
    const payload = response.data
    if (payload && payload.ok === false) {
      const error = new Error(payload.msg || '请求失败')
      error.response = response
      throw error
    }
    return response
  },
  async (error) => {
    const response = error?.response
    const originalRequest = error?.config || {}

    if (response?.status === 401 && !originalRequest.__retried && !isRefreshEndpoint(originalRequest)) {
      originalRequest.__retried = true
      const refreshed = await refreshAccessToken()
      if (refreshed) {
        originalRequest.headers = originalRequest.headers || {}
        originalRequest.headers.Authorization = `Bearer ${getAccessToken()}`
        return request(originalRequest)
      }
      redirectToLogin()
    }

    const message = response?.data?.msg || error.message || '请求失败'
    if (!originalRequest.silentError) {
      ElMessage.error(message)
    }
    return Promise.reject(error)
  }
)

export default request
