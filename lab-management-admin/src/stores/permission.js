import { defineStore } from 'pinia'
import { MENU_ITEMS } from '@/utils/constants'

export const usePermissionStore = defineStore('permission', {
  state: () => ({
    sidebarCollapsed: false
  }),
  getters: {
    menus: () => (role) => MENU_ITEMS.filter((item) => item.roles.includes(role))
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
