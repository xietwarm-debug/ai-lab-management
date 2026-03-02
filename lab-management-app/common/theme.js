const THEME_KEY = "theme"

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

function syncNativeBars(theme) {
  const isDark = normalizeTheme(theme) === "dark"
  const navFront = isDark ? "#ffffff" : "#000000"
  const navBg = isDark ? "#141d2a" : "#f8f8f8"
  const bg = isDark ? "#0a1018" : "#f5f7fb"
  const tabBg = isDark ? "#141d2a" : "#ffffff"
  const tabColor = isDark ? "#9aa7ba" : "#64748b"
  const tabSelected = isDark ? "#5ca2ff" : "#1677ff"
  const tabText = ["首页", "智能助手", "我的"]

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

  const applyTabRuntime = () => {
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
