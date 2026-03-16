export const LOGIN_PAGE_URL = "/pages/login/login"
export const HOME_PAGE_URL = "/pages/index/index"
export const AGENT_PAGE_URL = "/pages/agent/agent"
export const WORKBENCH_PAGE_URL = "/pages/workbench/index"
export const MY_PAGE_URL = "/pages/my/my"

export const TABBAR_PAGE_URLS = [HOME_PAGE_URL, AGENT_PAGE_URL, WORKBENCH_PAGE_URL, MY_PAGE_URL]
export const TABBAR_PAGE_ROUTES = new Set(TABBAR_PAGE_URLS.map((url) => normalizeRoute(url)))
const KNOWN_ROLES = new Set(["admin", "teacher", "student"])

function normalizeRoute(url = "") {
  return String(url || "").trim().replace(/^\//, "").split("?")[0]
}

function getCurrentRoute() {
  try {
    const pages = typeof getCurrentPages === "function" ? getCurrentPages() || [] : []
    const current = pages.length ? pages[pages.length - 1] : null
    const route = current && (current.route || (current.$page && current.$page.route) || "")
    return normalizeRoute(route)
  } catch (e) {
    return ""
  }
}

function showNoneToast(message = "") {
  const title = String(message || "").trim()
  if (!title) return
  uni.showToast({ title, icon: "none" })
}

export function normalizeRole(role = "") {
  const text = String(role || "").trim().toLowerCase()
  return KNOWN_ROLES.has(text) ? text : ""
}

export function getSession() {
  try {
    const session = uni.getStorageSync("session")
    return session && typeof session === "object" ? session : {}
  } catch (e) {
    return {}
  }
}

export function hasValidSession(session = getSession()) {
  const current = session && typeof session === "object" ? session : {}
  return !!(String(current.username || "").trim() && String(current.token || "").trim())
}

export function isTabBarUrl(url = "") {
  return TABBAR_PAGE_ROUTES.has(normalizeRoute(url))
}

export function navigateByUrl(url = "", options = {}) {
  const target = String(url || "").trim()
  if (!target) return false

  const { replace = false } = options || {}
  if (normalizeRoute(target) === getCurrentRoute()) return true

  if (isTabBarUrl(target)) {
    if (replace) {
      uni.reLaunch({ url: target })
    } else {
      uni.switchTab({ url: target })
    }
    return true
  }

  if (replace) {
    uni.reLaunch({ url: target })
  } else {
    uni.navigateTo({ url: target })
  }
  return true
}

export function resolveRoleHomeUrl(role = "") {
  return normalizeRole(role) ? WORKBENCH_PAGE_URL : HOME_PAGE_URL
}

export function redirectByRole(role = "", options = {}) {
  return navigateByUrl(resolveRoleHomeUrl(role), options)
}

export function requireLogin(options = {}) {
  const { toast = true, message = "请先登录", redirect = true, replace = true } = options || {}
  const session = getSession()
  if (hasValidSession(session)) return session

  if (toast) showNoneToast(message)
  if (redirect && getCurrentRoute() !== normalizeRoute(LOGIN_PAGE_URL)) {
    navigateByUrl(LOGIN_PAGE_URL, { replace })
  }
  return null
}

export function requireRole(roles = [], options = {}) {
  const session =
    options.session ||
    requireLogin({
      toast: options.loginToast !== false,
      message: options.loginMessage || "请先登录",
      redirect: options.redirect !== false,
      replace: options.loginReplace !== false
    })

  if (!session) return null

  const role = normalizeRole(session.role)
  const allowedRoles = Array.isArray(roles) ? roles.map((item) => normalizeRole(item)).filter(Boolean) : []
  if (!allowedRoles.length || allowedRoles.includes(role)) {
    return {
      ...session,
      role
    }
  }

  if (options.toast !== false) {
    showNoneToast(options.message || "无权限访问")
  }

  if (options.redirect !== false) {
    const fallbackUrl = String(options.fallbackUrl || "").trim()
    if (fallbackUrl) {
      navigateByUrl(fallbackUrl, { replace: true })
    } else {
      redirectByRole(role, { replace: true })
    }
  }

  return null
}
