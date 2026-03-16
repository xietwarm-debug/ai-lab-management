import { defineStore } from 'pinia'
import { APP_TITLE } from '@/utils/constants'

export const useAppStore = defineStore('app', {
  state: () => ({
    title: APP_TITLE
  }),
  actions: {
    setTitle(title) {
      this.title = title || APP_TITLE
      document.title = this.title
    }
  }
})
