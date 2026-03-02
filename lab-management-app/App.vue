<script>
import { BASE_URL } from "@/common/api.js"

const THEME_KEY = "theme"
const THEME_LIGHT = "light"
const THEME_DARK = "dark"

let wrappersInstalled = false
let refreshPromise = null
let reloginScheduled = false
let rawRequest = null
let rawUploadFile = null
let rawDownloadFile = null
let currentTheme = THEME_LIGHT

function normalizeTheme(theme) {
  return theme === THEME_DARK ? THEME_DARK : THEME_LIGHT
}

function getStoredTheme() {
  try {
    return normalizeTheme(uni.getStorageSync(THEME_KEY))
  } catch (e) {
    return THEME_LIGHT
  }
}

function syncThemeToRuntime(nextTheme) {
  const isDark = nextTheme === THEME_DARK
  const navFront = isDark ? "#ffffff" : "#000000"
  const navBg = isDark ? "#141d2a" : "#f8f8f8"
  const bg = isDark ? "#0a1018" : "#f5f7fb"
  const tabBg = isDark ? "#141d2a" : "#ffffff"
  const tabColor = isDark ? "#9aa7ba" : "#64748b"
  const tabSelected = isDark ? "#5ca2ff" : "#1677ff"
  const tabText = ["首页", "智能助手", "我的"]

  const applyTabBarRuntime = () => {
    try {
      uni.setTabBarStyle({
        color: tabColor,
        selectedColor: tabSelected,
        backgroundColor: tabBg,
        borderStyle: isDark ? "white" : "black"
      })
    } catch (e) {}

    tabText.forEach((text, index) => {
      try {
        uni.setTabBarItem({ index, text })
      } catch (e) {}
    })
  }

  // #ifdef H5
  if (typeof document !== "undefined" && document.documentElement) {
    const root = document.documentElement
    root.classList.remove("theme-light", "theme-dark")
    root.classList.add(`theme-${nextTheme}`)
    root.setAttribute("data-theme", nextTheme)
    if (document.body) {
      document.body.classList.remove("theme-light", "theme-dark")
      document.body.classList.add(`theme-${nextTheme}`)
      document.body.setAttribute("data-theme", nextTheme)
    }
  }
  // #endif

  try {
    uni.setNavigationBarColor({
      frontColor: navFront,
      backgroundColor: navBg
    })
  } catch (e) {}

  try {
    uni.setBackgroundColor({
      backgroundColor: bg,
      backgroundColorTop: bg,
      backgroundColorBottom: bg
    })
  } catch (e) {}

  applyTabBarRuntime()
  setTimeout(() => {
    applyTabBarRuntime()
  }, 80)
}

function applyTheme(theme) {
  const nextTheme = normalizeTheme(theme)
  currentTheme = nextTheme
  try {
    uni.setStorageSync(THEME_KEY, nextTheme)
  } catch (e) {}
  syncThemeToRuntime(nextTheme)
  try {
    uni.$emit("theme:change", { theme: nextTheme })
  } catch (e) {}
  return nextTheme
}

function getSession() {
  return uni.getStorageSync("session") || {}
}

function getToken() {
  const s = getSession()
  return s.token || ""
}

function scheduleRelogin() {
  if (reloginScheduled) return
  reloginScheduled = true
  uni.removeStorageSync("session")
  uni.showToast({ title: "登录已过期，请重新登录", icon: "none" })
  setTimeout(() => {
    uni.reLaunch({ url: "/pages/login/login" })
    reloginScheduled = false
  }, 250)
}

function callRaw(rawFn, args) {
  return new Promise((resolve) => {
    rawFn({
      ...args,
      success: (res) => resolve({ ok: true, data: res }),
      fail: (err) => resolve({ ok: false, data: err })
    })
  })
}

function refreshAccessToken() {
  if (refreshPromise) return refreshPromise

  const s = getSession()
  if (!s.refreshToken || !s.username || !rawRequest) {
    return Promise.resolve(false)
  }

  refreshPromise = new Promise((resolve) => {
    rawRequest({
      url: `${BASE_URL}/auth/refresh`,
      method: "POST",
      header: { "Content-Type": "application/json" },
      data: { refreshToken: s.refreshToken },
      success: (res) => {
        if (res.data && res.data.ok && res.data.data && res.data.data.token && res.data.data.refreshToken) {
          uni.setStorageSync("session", res.data.data)
          resolve(true)
          return
        }
        resolve(false)
      },
      fail: () => resolve(false),
      complete: () => {
        refreshPromise = null
      }
    })
  })

  return refreshPromise
}

async function requestWithAutoRetry(rawFn, baseArgs, skipAuth) {
  const runOnce = async () => {
    const callArgs = {
      ...baseArgs,
      header: { ...(baseArgs.header || {}) }
    }
    if (!skipAuth) {
      const token = getToken()
      if (token) {
        callArgs.header.Authorization = `Bearer ${token}`
      }
    }
    return callRaw(rawFn, callArgs)
  }

  let result = await runOnce()
  if (result.ok && result.data && result.data.statusCode === 401 && !skipAuth) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      result = await runOnce()
    } else {
      scheduleRelogin()
    }
  }

  return result
}

function wrapNetworkApi(rawFn) {
  return function wrapped(options = {}) {
    const oldSuccess = options.success
    const oldFail = options.fail
    const oldComplete = options.complete

    const headers = { ...(options.header || {}) }
    const skipAuth = headers["X-Skip-Auth"] === "1"
    delete headers["X-Skip-Auth"]

    const baseArgs = {
      ...options,
      header: headers
    }
    delete baseArgs.success
    delete baseArgs.fail
    delete baseArgs.complete

    const p = requestWithAutoRetry(rawFn, baseArgs, skipAuth).then((result) => {
      if (result.ok) {
        oldSuccess && oldSuccess(result.data)
        oldComplete && oldComplete(result.data)
        return result.data
      }
      oldFail && oldFail(result.data)
      oldComplete && oldComplete(result.data)
      return result.data
    })

    return p
  }
}

function installNetworkWrappers() {
  if (wrappersInstalled) return
  wrappersInstalled = true

  rawRequest = uni.request.bind(uni)
  rawUploadFile = uni.uploadFile.bind(uni)
  rawDownloadFile = uni.downloadFile.bind(uni)

  uni.request = wrapNetworkApi(rawRequest)
  uni.uploadFile = wrapNetworkApi(rawUploadFile)
  uni.downloadFile = wrapNetworkApi(rawDownloadFile)
}

export default {
  globalData: {
    theme: THEME_LIGHT
  },
  setTheme(theme) {
    const nextTheme = applyTheme(theme)
    this.globalData.theme = nextTheme
    return nextTheme
  },
  getTheme() {
    return normalizeTheme((this.globalData && this.globalData.theme) || currentTheme)
  },
  onLaunch() {
    installNetworkWrappers()
    const nextTheme = applyTheme(getStoredTheme())
    this.globalData.theme = nextTheme

    const session = getSession()
    if (!session.username || !session.token || !session.refreshToken) {
      uni.reLaunch({ url: "/pages/login/login" })
    }
  },
  onShow() {
    const nextTheme = applyTheme(normalizeTheme((this.globalData && this.globalData.theme) || getStoredTheme()))
    this.globalData.theme = nextTheme
  }
}
</script>

<style lang="scss">
@import "./styles/tokens.scss";
@import "./styles/components.scss";

page {
  background: var(--color-bg-page);
  color: var(--color-text-primary);
  font-family: var(--font-family-sans);
}

view,
text {
  color: inherit;
}

.theme-dark .card,
.theme-dark .section,
.theme-dark .featureCard,
.theme-dark .activityItem,
.theme-dark .noticeItem,
.theme-dark .lostItem,
.theme-dark .labCard,
.theme-dark .searchCard,
.theme-dark .formCard,
.theme-dark .summaryCard,
.theme-dark .toolbarCard,
.theme-dark .filterCard,
.theme-dark .actionCard,
.theme-dark .menuList,
.theme-dark .profileBar,
.theme-dark .menuItem,
.theme-dark .feedPreviewItem,
.theme-dark .entryCard {
  background: var(--color-bg-card) !important;
  border-color: var(--color-border-primary) !important;
  color: var(--color-text-primary) !important;
}

.theme-dark .heroCard {
  background: var(--color-bg-soft) !important;
  border-color: var(--color-border-focus) !important;
}

.theme-dark .headerSection,
.theme-dark .titleBar,
.theme-dark .chatCard,
.theme-dark .inputSection,
.theme-dark .pageInner {
  background: var(--color-bg-card) !important;
}

.theme-dark .menuButton,
.theme-dark .inputWrap,
.theme-dark .assistantBubble,
.theme-dark .defaultText {
  background: var(--color-bg-soft) !important;
}

.theme-dark .searchInputWrap,
.theme-dark .valueBox,
.theme-dark .recommendItem,
.theme-dark .skeleton,
.theme-dark .skeletonCard {
  background: var(--color-bg-soft) !important;
  border-color: var(--color-border-primary) !important;
}

.theme-dark .title,
.theme-dark .cardTitle,
.theme-dark .heroTitle,
.theme-dark .labName,
.theme-dark .itemName,
.theme-dark .noticeName,
.theme-dark .activityName,
.theme-dark .entryName,
.theme-dark .featureName,
.theme-dark .overviewValue {
  color: var(--color-text-primary) !important;
}

.theme-dark .subtitle,
.theme-dark .muted,
.theme-dark .meta,
.theme-dark .heroSub,
.theme-dark .entryDesc,
.theme-dark .featureDesc,
.theme-dark .noticeMessage,
.theme-dark .activityMessage,
.theme-dark .accountLine,
.theme-dark .feedMore,
.theme-dark .feedEmpty,
.theme-dark .feedPreviewMeta {
  color: var(--color-text-muted) !important;
}
</style>

