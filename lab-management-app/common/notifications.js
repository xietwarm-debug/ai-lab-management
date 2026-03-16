import { BASE_URL, getApiListData, readStorageCache, requestWithRetry, writeStorageCache } from "@/common/api.js"

const NOTICE_TAB_INDEX = 0
const NOTIFICATION_TYPES = ["reservation", "repair", "sensor_alarm", "lostfound", "course_task", "asset_borrow"]
const NOTIFICATION_LIST_CACHE_PREFIX = "notifications.list."
const DEFAULT_NOTIFICATION_CACHE_MAX_AGE_MS = 60 * 1000
const NOTIFICATION_READ_STORAGE_KEYS = {
  reservation: "notifications_last_read_reservation_",
  repair: "notifications_last_read_repair_",
  sensor_alarm: "notifications_last_read_sensor_alarm_",
  lostfound: "notifications_last_read_lostfound_",
  course_task: "notifications_last_read_course_task_",
  asset_borrow: "notifications_last_read_asset_borrow_"
}

function safeInvokeUni(apiFn, options) {
  if (typeof apiFn !== "function") return
  try {
    const maybePromise = apiFn({ ...(options || {}) })
    if (maybePromise && typeof maybePromise.catch === "function") {
      maybePromise.catch(() => {})
    }
  } catch (e) {}
}

function parseRows(payload) {
  return getApiListData(payload)
}

function getNotificationListCacheKey(username, typeFilter = "all") {
  const user = String(username || "").trim() || "guest"
  const filter = String(typeFilter || "").trim() || "all"
  return `${NOTIFICATION_LIST_CACHE_PREFIX}${user}.${filter}`
}

export function normalizeNotificationReadState(raw, fallback = {}) {
  const state = {
    reservation: String((fallback && fallback.reservation) || "").trim(),
    repair: String((fallback && fallback.repair) || "").trim(),
    sensor_alarm: String((fallback && fallback.sensor_alarm) || "").trim(),
    lostfound: String((fallback && fallback.lostfound) || "").trim(),
    course_task: String((fallback && fallback.course_task) || "").trim(),
    asset_borrow: String((fallback && fallback.asset_borrow) || "").trim()
  }

  if (!raw || typeof raw !== "object") return state

  Object.keys(state).forEach((key) => {
    if (!Object.prototype.hasOwnProperty.call(raw, key)) return
    state[key] = String(raw[key] || "").trim()
  })
  return state
}

export function normalizeNotificationReadPatch(raw) {
  const patch = {}
  if (!raw || typeof raw !== "object") return patch
  NOTIFICATION_TYPES.forEach((type) => {
    const value = String(raw[type] || "").trim()
    if (!value) return
    patch[type] = value
  })
  return patch
}

export function getNotificationReadStorageKeys(username) {
  const user = String(username || "").trim()
  const keys = {}
  NOTIFICATION_TYPES.forEach((type) => {
    keys[type] = `${NOTIFICATION_READ_STORAGE_KEYS[type]}${user}`
  })
  return keys
}

export function loadNotificationReadStateFromStorage(username, fallback = {}) {
  const state = normalizeNotificationReadState(null, fallback)
  const user = String(username || "").trim()
  if (!user) return state

  const keys = getNotificationReadStorageKeys(user)
  NOTIFICATION_TYPES.forEach((type) => {
    try {
      state[type] = String(uni.getStorageSync(keys[type]) || state[type] || "").trim()
    } catch (e) {}
  })
  return state
}

export function persistNotificationReadStateToStorage(username, readState) {
  const user = String(username || "").trim()
  if (!user) return

  const keys = getNotificationReadStorageKeys(user)
  const normalized = normalizeNotificationReadState(readState)
  NOTIFICATION_TYPES.forEach((type) => {
    try {
      uni.setStorageSync(keys[type], normalized[type] || "")
    } catch (e) {}
  })
}

export function mergeNotificationReadState(currentState, patch) {
  const state = normalizeNotificationReadState(currentState)
  const normalizedPatch = normalizeNotificationReadPatch(patch)
  const nextState = { ...state }

  Object.keys(normalizedPatch).forEach((type) => {
    const incoming = normalizedPatch[type]
    const current = String(state[type] || "").trim()
    nextState[type] = !current || incoming > current ? incoming : current
  })
  return nextState
}

export function buildNotificationReadPatchForRow(row) {
  const noticeType = String((row && row.type) || "").trim()
  const createdAt = String((row && row.createdAt) || "").trim()
  if (!NOTIFICATION_TYPES.includes(noticeType) || !createdAt) return {}
  return { [noticeType]: createdAt }
}

export function isNotificationUnread(row, readState) {
  const noticeType = String((row && row.type) || "").trim()
  if (!NOTIFICATION_TYPES.includes(noticeType)) return false
  const createdAt = String((row && row.createdAt) || "").trim()
  const lastReadAt = String((readState && readState[noticeType]) || "").trim()
  if (!createdAt) return false
  if (!lastReadAt) return true
  return createdAt > lastReadAt
}

export function countNotificationUnread(rows, readState) {
  const list = Array.isArray(rows) ? rows : []
  return list.reduce((sum, row) => (isNotificationUnread(row, readState) ? sum + 1 : sum), 0)
}

export function applyNotificationTabBadge(unreadTotal) {
  const total = Number(unreadTotal || 0)
  if (total > 0) {
    safeInvokeUni(uni.showTabBarRedDot, { index: NOTICE_TAB_INDEX })
    return
  }
  safeInvokeUni(uni.hideTabBarRedDot, { index: NOTICE_TAB_INDEX })
}

export function loadNotificationRowsFromCache(username, typeFilter = "all", maxAgeMs = DEFAULT_NOTIFICATION_CACHE_MAX_AGE_MS) {
  const rows = readStorageCache(getNotificationListCacheKey(username, typeFilter), { maxAgeMs })
  return Array.isArray(rows) ? rows : []
}

export function persistNotificationRowsToCache(username, rows, typeFilter = "all") {
  const normalizedRows = Array.isArray(rows) ? rows : []
  writeStorageCache(getNotificationListCacheKey(username, typeFilter), normalizedRows)
  return normalizedRows
}

export async function fetchNotificationRows(username, options = {}) {
  const user = String(username || "").trim()
  const typeFilter = String((options || {}).typeFilter || "").trim()
  const retries = Math.max(0, Number((options || {}).retries || 1))
  const delayMs = Math.max(0, Number((options || {}).delayMs || 250))
  const maxAgeMs = Math.max(0, Number((options || {}).maxAgeMs || DEFAULT_NOTIFICATION_CACHE_MAX_AGE_MS))
  const cacheFilter = typeFilter || "all"
  const cachedRows = loadNotificationRowsFromCache(user, cacheFilter, maxAgeMs)
  const query = typeFilter ? `?type=${encodeURIComponent(typeFilter)}` : ""

  try {
    const res = await requestWithRetry(
      () => uni.request({ url: `${BASE_URL}/notifications${query}`, method: "GET" }),
      { retries, delayMs }
    )
    const rows = parseRows((res && res.data) || [])
    persistNotificationRowsToCache(user, rows, cacheFilter)
    return { rows, stale: false, source: "network" }
  } catch (error) {
    if (cachedRows.length > 0) {
      return { rows: cachedRows, stale: true, source: "cache" }
    }
    throw error
  }
}

export async function fetchNotificationReadState(fallback = {}) {
  const res = await uni.request({ url: `${BASE_URL}/notifications/read-state`, method: "GET" })
  const payload = (res && res.data) || {}
  if (!payload.ok) {
    throw new Error(payload.msg || "Failed to fetch notification read state")
  }
  return normalizeNotificationReadState(payload.data, fallback)
}

export async function updateNotificationReadStatePatch(patch, fallback = {}) {
  const normalizedPatch = normalizeNotificationReadPatch(patch)
  if (!Object.keys(normalizedPatch).length) {
    return normalizeNotificationReadState(null, fallback)
  }

  const res = await uni.request({
    url: `${BASE_URL}/notifications/read-state`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: { readState: normalizedPatch }
  })
  const payload = (res && res.data) || {}
  if (!payload.ok) {
    throw new Error(payload.msg || "Failed to update notification read state")
  }
  return normalizeNotificationReadState(payload.data, fallback)
}

export async function refreshNotificationTabBadge() {
  const session = uni.getStorageSync("session") || {}
  if (!session.username || !session.token) {
    applyNotificationTabBadge(0)
    return { total: 0, rows: [], readState: normalizeNotificationReadState(null) }
  }

  const fallbackReadState = loadNotificationReadStateFromStorage(session.username || "", normalizeNotificationReadState(null))
  const [readRes, listRes] = await Promise.all([
    fetchNotificationReadState(fallbackReadState).catch(() => fallbackReadState),
    fetchNotificationRows(session.username || "", { retries: 1, maxAgeMs: DEFAULT_NOTIFICATION_CACHE_MAX_AGE_MS })
  ])

  const readState = normalizeNotificationReadState(readRes, fallbackReadState)
  const rows = Array.isArray(listRes && listRes.rows) ? listRes.rows : []
  const total = countNotificationUnread(rows, readState)
  applyNotificationTabBadge(total)
  return { total, rows, readState }
}
