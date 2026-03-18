import { defineStore } from 'pinia'
import { MENU_ITEMS } from '@/utils/constants'
import { isAllowedAccess } from '@/utils/auth'

export const usePermissionStore = defineStore('permission', {
  state: () => ({
    sidebarCollapsed: false
  }),
  getters: {
    menus: () => (user) => MENU_ITEMS.filter((item) => isAllowedAccess(user, item))
  },
  actions: {
    toggleSidebar(value) {
      if (typeof value === 'boolean') {
        this.sidebarCollapsed = value
        return
      }
      this.sidebarCollapsed = !this.sidebarCollapsed
    }
  }
})
