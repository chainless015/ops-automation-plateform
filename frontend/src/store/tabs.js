import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useTabsStore = defineStore('tabs', () => {
  // 从localStorage恢复标签页状态
  const savedTabs = localStorage.getItem('tabs')
  const savedActiveTab = localStorage.getItem('activeTab')
  
  const activeTabs = ref(savedTabs ? JSON.parse(savedTabs) : [])
  const activeTabName = ref(savedActiveTab || '')

  // 保存到localStorage
  const saveToLocalStorage = () => {
    localStorage.setItem('tabs', JSON.stringify(activeTabs.value))
    localStorage.setItem('activeTab', activeTabName.value)
  }

  // 添加标签页
  const addTab = (tab) => {
    const exists = activeTabs.value.find(t => t.name === tab.name)
    if (!exists) {
      activeTabs.value.push(tab)
    }
    activeTabName.value = tab.name
    saveToLocalStorage()
  }

  // 移除标签页
  const removeTab = (targetName) => {
    const tabs = activeTabs.value
    let activeTab = activeTabName.value
    
    if (activeTab === targetName) {
      tabs.forEach((tab, index) => {
        if (tab.name === targetName) {
          const nextTab = tabs[index + 1] || tabs[index - 1]
          if (nextTab) {
            activeTab = nextTab.name
          }
        }
      })
    }
    
    activeTabName.value = activeTab
    activeTabs.value = tabs.filter(tab => tab.name !== targetName)
    saveToLocalStorage()
  }

  // 清空所有标签页
  const clearTabs = () => {
    activeTabs.value = []
    activeTabName.value = ''
    localStorage.removeItem('tabs')
    localStorage.removeItem('activeTab')
  }

  // 重新排序标签页
  const reorderTabs = (newTabs) => {
    activeTabs.value = newTabs
    saveToLocalStorage()
  }

  return {
    activeTabs,
    activeTabName,
    addTab,
    removeTab,
    clearTabs,
    reorderTabs
  }
})
