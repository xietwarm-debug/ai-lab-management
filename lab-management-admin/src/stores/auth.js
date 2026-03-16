import { defineStore } from 'pinia'
import { loginApi, logoutApi } from '@/api/auth'
import { clearSession, getUserInfo, saveSession } from '@/utils/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: getUserInfo(),
    loading: false
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.user?.username),
    role: (state) => state.user?.role || '',
    username: (state) => state.user?.username || ''
  },
  actions: {
    restore() {
      this.user = getUserInfo()
    },
    async login(payload) {
      this.loading = true
      try {
        const response = await loginApi(payload)
        const data = response.data?.data || {}
        this.user = saveSession(data)
        return this.user
      } finally {
        this.loading = false
      }
    },
    async logout() {
      const refreshToken = localStorage.getItem('lab_admin_refresh_token') || ''
      try {
        if (refreshToken) {
          await logoutApi({ refreshToken })
        }
      } catch (error) {
        // ignore logout error to keep local cleanup reliable
      } finally {
        clearSession()
        this.user = null
      }
    }
  }
})
