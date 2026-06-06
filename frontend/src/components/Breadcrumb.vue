<template>
  <div class="breadcrumb-container">
    <el-breadcrumb separator="/">
      <el-breadcrumb-item to="/dashboard">
        <span>首页</span>
      </el-breadcrumb-item>
      
      <el-breadcrumb-item 
        v-for="(item, index) in breadcrumbs" 
        :key="index" 
        :to="item.clickable ? item.path : null"
        :class="{ 'not-clickable': !item.clickable }"
      >
        {{ item.label }}
      </el-breadcrumb-item>
    </el-breadcrumb>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const getDetailLabel = (path) => {
  const labels = {
    '/servers': '服务器管理',
    '/servers/:id/monitoring': '服务器监控',
    '/alerts/current': '当前告警',
    '/alerts/history': '历史告警',
    '/alerts/silences': '告警屏蔽',
    '/alerts/rules': '告警规则',
    '/notifications/contacts': '通知对象',
    '/notifications/groups': '通知组',
    '/automation/scheduled-tasks': '定时任务',
    '/automation/executions': '执行记录',
    '/automation/scripts': '脚本管理'
  }
  return labels[path] || '页面'
}

const breadcrumbs = computed(() => {
  const path = route.path

  if (path === '/dashboard') {
    return []
  }

  const items = []

  if (path.includes('/servers/') && path.includes('/monitoring')) {
    items.push({
      label: '服务器管理',
      path: '/servers',
      clickable: false
    })
    items.push({
      label: '服务器监控',
      path: path,
      clickable: true
    })
  } else if (path.startsWith('/alerts/')) {
    items.push({
      label: '告警管理',
      path: '/alerts/current',
      clickable: false
    })
    items.push({
      label: getDetailLabel(path),
      path: path,
      clickable: true
    })
  } else if (path.startsWith('/notifications/')) {
    items.push({
      label: '通知管理',
      path: '/notifications/contacts',
      clickable: false
    })
    items.push({
      label: getDetailLabel(path),
      path: path,
      clickable: true
    })
  } else if (path.startsWith('/automation/')) {
    items.push({
      label: '自动化运维',
      path: '/automation/scheduled-tasks',
      clickable: false
    })
    items.push({
      label: getDetailLabel(path),
      path: path,
      clickable: true
    })
  } else {
    items.push({
      label: getDetailLabel(path),
      path: path,
      clickable: true
    })
  }

  return items
})
</script>

<style scoped>
.breadcrumb-container {
  padding: 0;
  margin: 0;
  display: flex;
  align-items: center;
  height: 100%;
}

:deep(.el-breadcrumb) {
  display: flex;
  align-items: center;
  height: 100%;
}

:deep(.el-breadcrumb__inner) {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #606266;
  line-height: 1;
}

:deep(.el-breadcrumb__separator) {
  margin: 0 8px;
  color: #c0c4cc;
  display: flex;
  align-items: center;
}

:deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: #303133;
  font-weight: 500;
}

:deep(.el-breadcrumb__item:not(:last-child) .el-breadcrumb__inner) {
  cursor: pointer;
  transition: color 0.2s;
}

:deep(.el-breadcrumb__item:not(:last-child) .el-breadcrumb__inner:hover) {
  color: #409eff;
}

:deep(.el-breadcrumb__item.not-clickable .el-breadcrumb__inner) {
  cursor: default;
  color: #909399;
}

:deep(.el-breadcrumb__item.not-clickable .el-breadcrumb__inner:hover) {
  color: #909399;
}
</style>
