<script>
import { BASE_URL } from "@/common/api.js"

let wrappersInstalled = false
let refreshPromise = null
let reloginScheduled = false
let rawRequest = null
let rawUploadFile = null
let rawDownloadFile = null

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
  onLaunch() {
    installNetworkWrappers()
    const session = getSession()
    if (!session.username || !session.token || !session.refreshToken) {
      uni.reLaunch({ url: "/pages/login/login" })
    }
  }
}
</script>

<style lang="scss">
@import "./styles/components.scss";
</style>
