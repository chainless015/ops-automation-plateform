import { defineStore } from 'pinia'

export const useSidebarStore = defineStore('sidebar', {
  state: () => ({
    isCollapsed: false
  }),

  actions: {
    toggleCollapse() {
      this.isCollapsed = !this.isCollapsed
    }
  }
})
