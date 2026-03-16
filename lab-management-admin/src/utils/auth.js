import { REFRESH_TOKEN_KEY, ROLE_LABEL_MAP, TOKEN_KEY, USER_KEY } from './constants'

function parseJson(value, fallback = null) {
  try {
    return JSON.parse(value)
  } catch (error) {
    return fallback
  }
}

export function getAccessToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY) || ''
}

export function getUserInfo() {
  return parseJson(localStorage.getItem(USER_KEY), null)
}

export function saveSession(session = {}) {
  const token = String(session.token || '').trim()
  const refreshToken = String(session.refreshToken || '').trim()
  const user = {
    userId: Number(session.userId || 0),
    username: String(session.username || '').trim(),
    role: String(session.role || '').trim(),
    expiresIn: Number(session.expiresIn || 0)
  }

  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
  localStorage.setItem(USER_KEY, JSON.stringify(user))

  return user
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function isAllowedRole(role, roles = []) {
  if (!Array.isArray(roles) || roles.length === 0) return true
  return roles.includes(role)
}

export function getRoleLabel(role) {
  return ROLE_LABEL_MAP[role] || role || '未知'
}
