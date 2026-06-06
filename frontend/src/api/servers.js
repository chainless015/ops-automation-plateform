import request from '@/utils/axios'

// 获取服务器列表（支持分页、关键词搜索、状态筛选）
export const getServers = (params) =>
  request.get('/api/servers', { params })

// 获取单台服务器详情
export const getServer = (id) =>
  request.get(`/api/servers/${id}`)

// 添加服务器
export const createServer = (data) =>
  request.post('/api/servers', data)

// 更新服务器信息
export const updateServer = (id, data) =>
  request.put(`/api/servers/${id}`, data)

// 删除服务器
export const deleteServer = (id) =>
  request.delete(`/api/servers/${id}`)

// 检测服务器在线状态
export const pingServer = (id) =>
  request.get(`/api/servers/${id}/ping`)
