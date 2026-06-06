import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { useAuthStore } from '@/store/auth'

// 创建axios实例
const instance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 30000
})

// 请求拦截器
instance.interceptors.request.use(
  config => {
    // 添加token到请求头
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    // 避免浏览器缓存 GET 请求导致刷新无效
    if (config.method === 'get') {
      config.params = {
        ...(config.params || {}),
        _t: Date.now()
      }
    }
    return config
  },
  error => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
let isTokenExpired = false // 标记是否已经处理过token过期

instance.interceptors.response.use(
  response => {
    return response
  },
  error => {
    if (error.response) {
      const { status, data } = error.response

      // 只处理401错误（token过期），且仅当有有效token时
      if (status === 401) {
        const token = localStorage.getItem('token')
        // 只有当有token且detail包含"expired"或"invalid token"时才认为是token过期
        const isRealTokenExpired = token && (
          data?.detail?.toLowerCase().includes('expired') || 
          data?.detail?.toLowerCase().includes('invalid token') ||
          data?.detail?.toLowerCase().includes('not authenticated')
        )
        
        if (isRealTokenExpired && !isTokenExpired) {
          isTokenExpired = true
          const authStore = useAuthStore()
          authStore.logout()
          ElMessage.warning({
            message: '登录已过期，即将跳转到登录页面...',
            duration: 2000,
            onClose: () => {
              router.push({ name: 'Login' })
              // 延迟重置标记，避免跳转后立即触发
              setTimeout(() => {
                isTokenExpired = false
              }, 1000)
            }
          })
          // 2秒后自动跳转（防止用户不关闭消息）
          setTimeout(() => {
            router.push({ name: 'Login' })
            setTimeout(() => {
              isTokenExpired = false
            }, 1000)
          }, 2000)
        }
      }
    }

    return Promise.reject(error)
  }
)

export default instance
