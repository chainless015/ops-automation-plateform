import request from '@/utils/axios'

// 获取定时任务列表（支持分页、脚本/服务器/启用状态筛选）
export const getScheduledTasks = (params) =>
  request.get('/api/scheduled-tasks', { params })

// 创建定时任务
export const createScheduledTask = (data) =>
  request.post('/api/scheduled-tasks', data)

// 更新定时任务
export const updateScheduledTask = (id, data) =>
  request.put(`/api/scheduled-tasks/${id}`, data)

// 删除定时任务
export const deleteScheduledTask = (id) =>
  request.delete(`/api/scheduled-tasks/${id}`)

// 切换任务启用/禁用状态
export const toggleScheduledTask = (id) =>
  request.post(`/api/scheduled-tasks/${id}/toggle`)
