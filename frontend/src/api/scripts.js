import request from '@/utils/axios'

// 获取脚本列表（支持分页、关键词搜索）
export const getScripts = (params) =>
  request.get('/api/scripts', { params })

// 获取脚本详情（含完整 content）
export const getScript = (id) =>
  request.get(`/api/scripts/${id}`)

// 创建脚本
export const createScript = (data) =>
  request.post('/api/scripts', data)

// 更新脚本
export const updateScript = (id, data) =>
  request.put(`/api/scripts/${id}`, data)

// 删除脚本
export const deleteScript = (id) =>
  request.delete(`/api/scripts/${id}`)
