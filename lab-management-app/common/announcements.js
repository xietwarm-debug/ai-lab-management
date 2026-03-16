import { getApiListData, listAnnouncements, readStorageCache, requestWithRetry, writeStorageCache } from "@/common/api.js"

const ANNOUNCEMENT_CACHE_PREFIX = "announcements.cache."
const DEFAULT_ANNOUNCEMENT_CACHE_MAX_AGE_MS = 5 * 60 * 1000

function getAnnouncementCacheKey(limit) {
  const normalizedLimit = Math.max(1, Number(limit || 20) || 20)
  return `${ANNOUNCEMENT_CACHE_PREFIX}${normalizedLimit}`
}

export function loadAnnouncementRowsFromCache(limit, maxAgeMs = DEFAULT_ANNOUNCEMENT_CACHE_MAX_AGE_MS) {
  const rows = readStorageCache(getAnnouncementCacheKey(limit), { maxAgeMs })
  return Array.isArray(rows) ? rows : []
}

export function persistAnnouncementRowsToCache(limit, rows) {
  const normalizedRows = Array.isArray(rows) ? rows : []
  writeStorageCache(getAnnouncementCacheKey(limit), normalizedRows)
  return normalizedRows
}

export async function fetchAnnouncementRows(options = {}) {
  const limit = Math.max(1, Number((options || {}).limit || 20) || 20)
  const retries = Math.max(0, Number((options || {}).retries || 1))
  const delayMs = Math.max(0, Number((options || {}).delayMs || 250))
  const maxAgeMs = Math.max(0, Number((options || {}).maxAgeMs || DEFAULT_ANNOUNCEMENT_CACHE_MAX_AGE_MS))
  const cachedRows = loadAnnouncementRowsFromCache(limit, maxAgeMs)

  try {
    const res = await requestWithRetry(() => listAnnouncements({ limit }), { retries, delayMs })
    const rows = getApiListData(res && res.data)
    persistAnnouncementRowsToCache(limit, rows)
    return { rows, stale: false, source: "network" }
  } catch (error) {
    if (cachedRows.length > 0) {
      return { rows: cachedRows, stale: true, source: "cache" }
    }
    throw error
  }
}
