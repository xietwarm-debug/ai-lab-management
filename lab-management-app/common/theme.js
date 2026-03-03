const THEME_KEY = "theme"
const TABBAR_ROUTES = new Set(["pages/index/index", "pages/agent/agent", "pages/my/my"])
const IS_H5_RUNTIME = typeof window !== "undefined" && typeof document !== "undefined"

export function normalizeTheme(theme) {
  return theme === "dark" ? "dark" : "light"
}

export function toThemeClass(theme) {
  return `theme-${normalizeTheme(theme)}`
}

function readThemeFromRuntime() {
  const app = typeof getApp === "function" ? getApp() : null
  if (app && typeof app.getTheme === "function") {
    return normalizeTheme(app.getTheme())
  }
  try {
    return normalizeTheme(uni.getStorageSync(THEME_KEY))
  } catch (e) {
    return "light"
  }
}

function getCurrentRoute() {
  try {
    const pages = typeof getCurrentPages === "function" ? getCurrentPages() || [] : []
    const current = pages.length ? pages[pages.length - 1] : null
    const route = current && (current.route || (current.$page && current.$page.route) || "")
    return String(route || "").replace(/^\//, "")
  } catch (e) {
    return ""
  }
}

function isTabBarRouteActive() {
  try {
    const pages = typeof getCurrentPages === "function" ? getCurrentPages() || [] : []
    const current = pages.length ? pages[pages.length - 1] : null
    const isTabBarMeta = !!(current && current.$page && current.$page.meta && current.$page.meta.isTabBar)
    if (isTabBarMeta) return true
  } catch (e) {}
  const route = getCurrentRoute()
  return !!route && TABBAR_ROUTES.has(route)
}

function safeInvokeUni(apiFn, options) {
  if (typeof apiFn !== "function") return
  const callOptions = { ...(options || {}) }
  const oldFail = callOptions.fail
  callOptions.fail = (err) => {
    if (typeof oldFail === "function") {
      try {
        oldFail(err)
      } catch (e) {}
    }
  }
  try {
    const maybePromise = apiFn(callOptions)
    if (maybePromise && typeof maybePromise.catch === "function") {
      maybePromise.catch(() => {})
    }
  } catch (e) {}
}

function syncNativeBars(theme) {
  if (IS_H5_RUNTIME) return

  const isDark = normalizeTheme(theme) === "dark"
  const navFront = isDark ? "#ffffff" : "#000000"
  const navBg = isDark ? "#141d2a" : "#f8f8f8"
  const bg = isDark ? "#0a1018" : "#f5f7fb"
  const tabBg = isDark ? "#141d2a" : "#ffffff"
  const tabColor = isDark ? "#9aa7ba" : "#64748b"
  const tabSelected = isDark ? "#5ca2ff" : "#1677ff"
  const tabText = ["首页", "智能助手", "我的"]
  const hasPage = !!getCurrentRoute()

  if (hasPage) {
    safeInvokeUni(uni.setNavigationBarColor, {
      frontColor: navFront,
      backgroundColor: navBg
    })
  }

  if (hasPage) {
    safeInvokeUni(uni.setBackgroundColor, {
      backgroundColor: bg,
      backgroundColorTop: bg,
      backgroundColorBottom: bg
    })
  }

  const applyTabRuntime = () => {
    if (!isTabBarRouteActive()) return
    safeInvokeUni(uni.setTabBarStyle, {
      color: tabColor,
      selectedColor: tabSelected,
      backgroundColor: tabBg,
      borderStyle: isDark ? "white" : "black"
    })

    tabText.forEach((text, index) => {
      safeInvokeUni(uni.setTabBarItem, { index, text })
    })
  }

  applyTabRuntime()
  setTimeout(() => {
    applyTabRuntime()
  }, 80)
}

export const themePageMixin = {
  data() {
    return {
      themeClass: toThemeClass("light")
    }
  },
  onLoad() {
    this.syncThemeClass()
    uni.$on("theme:change", this.__onThemeChanged)
  },
  onShow() {
    this.syncThemeClass()
  },
  onUnload() {
    uni.$off("theme:change", this.__onThemeChanged)
  },
  methods: {
    syncThemeClass() {
      const theme = readThemeFromRuntime()
      this.themeClass = toThemeClass(theme)
      syncNativeBars(theme)
    },
    __onThemeChanged(payload) {
      const theme = payload && payload.theme ? payload.theme : "light"
      this.themeClass = toThemeClass(theme)
    }
  }
}
