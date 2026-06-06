<template>
    <el-container class="layout-container">
      <el-aside :width="sidebarStore.isCollapsed ? '64px' : '200px'" class="sidebar-transition">
      <div 
        class="logo" 
        @click="sidebarStore.isCollapsed && sidebarStore.toggleCollapse()"
        :class="{ 'logo-clickable': sidebarStore.isCollapsed }"
      >
        <transition name="fade" mode="out-in">
          <div v-if="!sidebarStore.isCollapsed" class="logo-expanded">
            <img :src="appConfig.logo" :alt="appConfig.name" class="logo-image" />
            <h5>{{ appConfig.name }}</h5>
            <el-icon class="collapse-icon" @click.stop="sidebarStore.toggleCollapse()">
              <Fold />
            </el-icon>
          </div>
          <div v-else class="logo-collapsed-wrapper">
            <img :src="appConfig.logo" :alt="appConfig.name" class="logo-image-collapsed" />
            <el-icon class="expand-icon">
              <Expand />
            </el-icon>
          </div>
        </transition>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        :default-openeds="sidebarStore.isCollapsed ? [] : ['alerts', 'notifications', 'automation']"
        :collapse="sidebarStore.isCollapsed"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataLine /></el-icon>
          <template #title>
            <span>仪表盘</span>
          </template>
        </el-menu-item>
        
        <el-menu-item index="/servers">
          <el-icon><Monitor /></el-icon>
          <template #title>
            <span>服务器管理</span>
          </template>
        </el-menu-item>
        
        <el-sub-menu index="alerts">
          <template #title>
            <el-icon><Bell /></el-icon>
            <span>告警管理</span>
          </template>
          <el-menu-item index="/alerts/current">当前告警</el-menu-item>
          <el-menu-item index="/alerts/history">历史告警</el-menu-item>
          <el-menu-item index="/alerts/silences">告警屏蔽</el-menu-item>
          <el-menu-item index="/alerts/rules">告警规则</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="notifications">
          <template #title>
            <el-icon><Message /></el-icon>
            <span>通知管理</span>
          </template>
          <el-menu-item index="/notifications/contacts">通知对象</el-menu-item>
          <el-menu-item index="/notifications/groups">通知组</el-menu-item>
        </el-sub-menu>
        
        <el-sub-menu index="automation">
          <template #title>
            <el-icon><Document /></el-icon>
            <span>自动化运维</span>
          </template>
          <el-menu-item index="/automation/scripts">脚本管理</el-menu-item>
          <el-menu-item index="/automation/scheduled-tasks">定时任务</el-menu-item>
          <el-menu-item index="/automation/executions">执行记录</el-menu-item>
        </el-sub-menu>
        
      </el-menu>
    </el-aside>
    
    <el-container class="main-panel">
      <el-header>
        <div class="header-content">
          <Breadcrumb />
          
          <div class="user-info">
            <el-dropdown @command="handleCommand">
              <span class="user-name">
                <div class="user-avatar">{{ authStore.user?.username.charAt(0).toUpperCase() }}</div>
                {{ authStore.user?.username }}
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </el-header>
      
      <el-main>
        <div class="tabs-container">
          <div class="tabs-wrapper">
            <el-tabs
              v-model="tabsStore.activeTabName"
              type="card"
              @tab-remove="removeTab"
              @tab-click="handleTabClick"
              class="main-tabs"
            >
              <el-tab-pane
                v-for="tab in tabsStore.activeTabs"
                :key="tab.name"
                :label="tab.label"
                :name="tab.name"
                :closable="tab.closable !== false"
              >
                <template #label>
                  <span
                    class="tab-label"
                    @contextmenu.prevent="handleContextMenu($event, tab)"
                  >
                    <span class="tab-label-text">{{ tab.label }}</span>
                  </span>
                </template>
              </el-tab-pane>
            </el-tabs>
          </div>
          
          <div class="tabs-actions-wrapper">
            <el-dropdown trigger="click" class="tabs-actions" @command="handleTabsCommand">
              <el-button size="small" text>
                <el-icon><Operation /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="closeOthers">
                    <el-icon><CircleClose /></el-icon>
                    关闭其他
                  </el-dropdown-item>
                  <el-dropdown-item command="closeAll">
                    <el-icon><Close /></el-icon>
                    关闭全部
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
        
        <div class="tab-content">
          <router-view v-slot="{ Component }">
            <keep-alive>
              <component :is="Component" :key="route.path" />
            </keep-alive>
          </router-view>
        </div>
      </el-main>
      
      <!-- 右键菜单 -->
      <ul
        v-show="contextMenuVisible"
        :style="{ left: contextMenuLeft + 'px', top: contextMenuTop + 'px' }"
        class="context-menu"
      >
        <li @click="closeCurrentTab">关闭当前</li>
        <li @click="closeOtherTabs">关闭其他</li>
        <li @click="closeAllTabs">关闭全部</li>
      </ul>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, watch, ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { useTabsStore } from '@/store/tabs'
import { useSidebarStore } from '@/store/sidebar'
import { ElMessageBox } from 'element-plus'
import { Fold, Expand } from '@element-plus/icons-vue'
import Sortable from 'sortablejs'
import { appConfig } from '@/config/app'
import Breadcrumb from '@/components/Breadcrumb.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const tabsStore = useTabsStore()
const sidebarStore = useSidebarStore()

const activeMenu = computed(() => route.path)

// 右键菜单相关
const contextMenuVisible = ref(false)
const contextMenuLeft = ref(0)
const contextMenuTop = ref(0)
const currentContextTab = ref(null)

// 拖动相关
let sortableInstance = null

// 监听路由变化，自动添加标签页
watch(() => route.path, (newPath) => {
  if (newPath && route.meta.title) {
    tabsStore.addTab({
      name: newPath,
      label: route.meta.title,
      closable: newPath !== '/dashboard' // 仪表盘不可关闭
    })
  }
}, { immediate: true })

// 初始化拖动功能
const initSortable = async () => {
  await nextTick()
  const tabsNav = document.querySelector('.el-tabs__nav')
  if (tabsNav && !sortableInstance) {
    sortableInstance = Sortable.create(tabsNav, {
      animation: 200,
      ghostClass: 'sortable-ghost',
      dragClass: 'sortable-drag',
      onEnd: (evt) => {
        const { oldIndex, newIndex } = evt
        if (oldIndex !== newIndex) {
          // 重新排序标签
          const tabs = [...tabsStore.activeTabs]
          const [movedTab] = tabs.splice(oldIndex, 1)
          tabs.splice(newIndex, 0, movedTab)
          tabsStore.reorderTabs(tabs)
        }
      }
    })
  }
}

const handleTabClick = (tab) => {
  router.push(tab.props.name)
}

const removeTab = (targetName) => {
  const tabs = tabsStore.activeTabs
  let activeTab = tabsStore.activeTabName
  
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
  
  tabsStore.removeTab(targetName)
  if (activeTab !== targetName) {
    router.push(activeTab)
  }
}

const handleCommand = (command) => {
  if (command === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(() => {
      authStore.logout()
      tabsStore.clearTabs()
      router.push('/login')
    }).catch(() => {})
  }
}

// 右键菜单处理
const handleContextMenu = (event, tab) => {
  currentContextTab.value = tab
  contextMenuLeft.value = event.clientX
  contextMenuTop.value = event.clientY
  contextMenuVisible.value = true
}

const closeCurrentTab = () => {
  if (currentContextTab.value && currentContextTab.value.closable !== false) {
    removeTab(currentContextTab.value.name)
  }
  contextMenuVisible.value = false
}

const closeOtherTabs = () => {
  if (currentContextTab.value) {
    tabsStore.activeTabs.forEach(tab => {
      if (tab.name !== currentContextTab.value.name && tab.closable !== false) {
        tabsStore.removeTab(tab.name)
      }
    })
    router.push(currentContextTab.value.name)
  }
  contextMenuVisible.value = false
}

const closeAllTabs = () => {
  const dashboardTab = tabsStore.activeTabs.find(tab => tab.name === '/dashboard')
  tabsStore.activeTabs.forEach(tab => {
    if (tab.closable !== false) {
      tabsStore.removeTab(tab.name)
    }
  })
  if (dashboardTab) {
    router.push('/dashboard')
  }
  contextMenuVisible.value = false
}

// 下拉菜单命令处理
const handleTabsCommand = (command) => {
  if (command === 'closeOthers') {
    const currentTab = tabsStore.activeTabs.find(tab => tab.name === route.path)
    if (currentTab) {
      currentContextTab.value = currentTab
      closeOtherTabs()
    }
  } else if (command === 'closeAll') {
    closeAllTabs()
  }
}

// 点击其他地方关闭右键菜单
const closeContextMenu = () => {
  contextMenuVisible.value = false
}

onMounted(() => {
  document.addEventListener('click', closeContextMenu)
  initSortable()
})

onUnmounted(() => {
  document.removeEventListener('click', closeContextMenu)
  if (sortableInstance) {
    sortableInstance.destroy()
    sortableInstance = null
  }
})
</script>

<style scoped>
.layout-container {
  height: 100vh;
  height: 100dvh;
  min-width: var(--app-min-width);
  background-color: #f0f2f5;
  overflow: hidden;
}

.main-panel {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.el-aside {
  background-color: #304156;
  color: #bfcbd9;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
  z-index: 100;
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
  transition: width 0.3s ease;
}

/* 隐藏侧边栏滚动条 */
.el-aside::-webkit-scrollbar {
  width: 0;
  display: none;
}

.el-aside {
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

/* 移除菜单边框 */
:deep(.el-menu) {
  border: none !important;
}

/* Logo区域 - Gemini风格交互 */
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #2b3a4b;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  transition: all 0.3s;
}

.logo-clickable {
  cursor: pointer;
}

.logo-clickable:hover {
  background-color: #3a4a5e;
}

/* 展开状态的logo */
.logo-expanded {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  gap: 12px;
}

.logo-image {
  width: 32px;
  height: 32px;
  object-fit: contain;
  flex-shrink: 0;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.1);
  padding: 4px;
  box-sizing: border-box;
}

.logo-expanded h3 {
  margin: 0;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.5px;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.collapse-icon {
  font-size: 18px;
  color: #bfcbd9;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s;
  flex-shrink: 0;
}

.collapse-icon:hover {
  background-color: rgba(255, 255, 255, 0.1);
  color: #fff;
}

/* 收起状态的logo */
.logo-collapsed-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-image-collapsed {
  width: 32px;
  height: 32px;
  object-fit: contain;
  transition: opacity 0.3s;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.1);
  padding: 4px;
  box-sizing: border-box;
}

.logo-collapsed-wrapper:hover .logo-image-collapsed {
  opacity: 0;
}

.expand-icon {
  position: absolute;
  font-size: 20px;
  color: #bfcbd9;
  opacity: 0;
  transition: opacity 0.3s;
}

.logo-clickable:hover .expand-icon {
  opacity: 1;
  color: #fff;
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.el-header {
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  display: flex;
  align-items: center;
  padding: 0 24px;
  z-index: 99;
}

.header-content {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
}

.user-name {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 4px;
  transition: all 0.2s;
}

.user-name:hover {
  background-color: #f5f7fa;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
}

.el-main {
  background-color: #f0f2f5;
  padding: 0;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.tabs-container {
  display: flex;
  align-items: center;
  background: #ffffff;
  padding: 8px 12px;
  border-bottom: 1px solid #e4e7ed;
  gap: 12px;
}

.tabs-wrapper {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.main-tabs {
  margin-bottom: 0;
}

/* 移除Element Plus默认的所有边框 */
:deep(.el-tabs__header) {
  border-bottom: none !important;
  margin: 0 !important;
}

:deep(.el-tabs__nav-wrap::after) {
  display: none !important;
  height: 0 !important;
}

:deep(.el-tabs__nav) {
  border: none !important;
}

:deep(.el-tabs--card > .el-tabs__header) {
  border-bottom: none !important;
}

:deep(.el-tabs--card > .el-tabs__header .el-tabs__nav) {
  border: none !important;
}

:deep(.el-tabs--card > .el-tabs__header .el-tabs__item) {
  border-left: none !important;
  border-top: none !important;
  border-right: none !important;
  border-bottom: none !important;
}

/* 标签页滚动容器 - 使用更细的滚动条 */
:deep(.el-tabs__nav-wrap) {
  overflow-x: auto;
  overflow-y: hidden;
}

:deep(.el-tabs__nav-wrap::-webkit-scrollbar) {
  height: 4px;
}

:deep(.el-tabs__nav-wrap::-webkit-scrollbar-thumb) {
  background-color: #c1c1c1;
  border-radius: 2px;
}

:deep(.el-tabs__nav-wrap::-webkit-scrollbar-thumb:hover) {
  background-color: #909399;
}

/* 标签页导航箭头居中 */
:deep(.el-tabs__nav-prev),
:deep(.el-tabs__nav-next) {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 32px;
  line-height: 32px;
  top: 0;
}

:deep(.el-tabs__nav-prev .el-icon),
:deep(.el-tabs__nav-next .el-icon) {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 标签页样式优化 - 胶囊/跑道形状 */
:deep(.el-tabs__item) {
  height: 32px;
  line-height: 32px;
  padding: 0 20px;
  margin-right: 8px;
  border: none !important;
  border-radius: 16px;
  background-color: #f5f7fa;
  color: #606266;
  font-size: 13px;
  transition: all 0.2s ease;
  position: relative;
  overflow: visible;
}

:deep(.el-tabs__item::after) {
  display: none;
}

:deep(.el-tabs__item:hover) {
  background-color: #e8f4ff;
  color: #409eff;
}

/* 激活标签页样式 - 蓝色胶囊 */
:deep(.el-tabs__item.is-active) {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  color: #ffffff;
  font-weight: 500;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
}

:deep(.el-tabs__item.is-active .tab-label) {
  color: #ffffff;
}

:deep(.el-tabs__item.is-active .el-icon-close) {
  color: #ffffff;
}

:deep(.el-tabs__item.is-active .el-icon-close:hover) {
  background-color: rgba(255, 255, 255, 0.3);
  color: #ffffff;
}

/* 关闭按钮样式 */
:deep(.el-icon-close) {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-left: 6px;
}

:deep(.el-icon-close:hover) {
  background-color: rgba(0, 0, 0, 0.06);
  color: #f56c6c;
}

.tab-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  user-select: none;
}

.tab-label-text {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 操作按钮区域 */
.tabs-actions-wrapper {
  display: flex;
  align-items: center;
  padding-left: 12px;
  border-left: 1px solid #e4e7ed;
}

.tabs-actions {
  display: flex;
  align-items: center;
}

:deep(.tabs-actions .el-button) {
  padding: 6px 10px;
  border-radius: 4px;
  transition: all 0.2s;
}

:deep(.tabs-actions .el-button:hover) {
  background-color: #ecf5ff;
  color: #409eff;
}

:deep(.tabs-actions .el-icon) {
  font-size: 16px;
}

/* 下拉菜单样式 */
:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
}

:deep(.el-dropdown-menu__item .el-icon) {
  font-size: 14px;
}

.tab-content {
  flex: 1;
  overflow: auto;
  padding: 16px;
}

/* 右键菜单样式 */
.context-menu {
  position: fixed;
  background-color: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  padding: 4px 0;
  margin: 0;
  list-style: none;
  z-index: 9999;
  min-width: 120px;
}

.context-menu li {
  padding: 8px 16px;
  cursor: pointer;
  font-size: 14px;
  color: #606266;
  transition: all 0.2s;
}

.context-menu li:hover {
  background-color: #f5f7fa;
  color: #409eff;
}

/* 拖动反馈样式 */
:deep(.sortable-ghost) {
  opacity: 0.5;
  background-color: #e8f4ff !important;
}

:deep(.sortable-drag) {
  opacity: 0.8;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4) !important;
}
</style>
