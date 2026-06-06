import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/layouts/Layout.vue'),
    meta: { requiresAuth: true },
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '仪表盘' }
      },
      {
        path: 'servers',
        name: 'Servers',
        component: () => import('@/views/Servers.vue'),
        meta: { title: '服务器管理' }
      },
      {
        path: 'servers/:id/monitoring',
        name: 'ServerMonitoring',
        component: () => import('@/views/ServerMonitoring.vue'),
        meta: { title: '服务器监控' }
      },
      {
        path: 'alerts/current',
        name: 'AlertsCurrent',
        component: () => import('@/views/alerts/CurrentAlerts.vue'),
        meta: { title: '当前告警' }
      },
      {
        path: 'alerts/history',
        name: 'AlertsHistory',
        component: () => import('@/views/alerts/AlertHistory.vue'),
        meta: { title: '历史告警' }
      },
      {
        path: 'alerts/silences',
        name: 'AlertsSilences',
        component: () => import('@/views/alerts/AlertSilences.vue'),
        meta: { title: '告警屏蔽' }
      },
      {
        path: 'notifications/contacts',
        name: 'NotificationContacts',
        component: () => import('@/views/notifications/NotificationContacts.vue'),
        meta: { title: '通知对象' }
      },
      {
        path: 'notifications/groups',
        name: 'NotificationGroups',
        component: () => import('@/views/notifications/NotificationGroups.vue'),
        meta: { title: '通知组' }
      },
      {
        path: 'alerts/rules',
        name: 'AlertsRules',
        component: () => import('@/views/alerts/AlertRules.vue'),
        meta: { title: '告警规则' }
      },
      {
        path: 'automation/scheduled-tasks',
        name: 'ScheduledTasks',
        component: () => import('@/views/automation/ScheduledTasks.vue'),
        meta: { title: '定时任务' }
      },
      {
        path: 'automation/executions',
        name: 'Executions',
        component: () => import('@/views/automation/Executions.vue'),
        meta: { title: '执行记录' }
      },
      {
        path: 'automation/scripts',
        name: 'Scripts',
        component: () => import('@/views/automation/Scripts.vue'),
        meta: { title: '脚本管理' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { requiresAuth: false }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to) => {
  const authStore = useAuthStore()
  
  // 检查是否需要认证
  if (to.meta.requiresAuth !== false) {
    if (!authStore.isAuthenticated) {
      // 未登录，跳转到登录页
      return { name: 'Login', query: { redirect: to.fullPath } }
    }
  }
  
  // 已登录用户访问登录页，跳转到首页
  if (to.name === 'Login' && authStore.isAuthenticated) {
    return { name: 'Dashboard' }
  }
})

export default router
