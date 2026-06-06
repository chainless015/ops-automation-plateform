import request from '@/utils/axios'

// 获取执行记录列表（支持分页、服务器/类型/时间筛选）
export const getExecutions = (params) =>
  request.get('/api/executions', { params })

// 获取单次执行详情（含 output、error 输出）
export const getExecution = (id) =>
  request.get(`/api/executions/${id}`)

// 手动触发脚本执行
export const createExecution = (data) =>
  request.post('/api/executions', data)

// 导出执行记录为 Excel（按 ids 或筛选条件）
export const exportExecutions = (params) =>
  request.get('/api/executions/export', { params, responseType: 'blob' })
