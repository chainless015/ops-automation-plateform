import request from '@/utils/axios'

// ─── 告警规则 ────────────────────────────────────────────────────────────────

// 获取所有告警规则（含 contacts、groups 关联对象）
export const getAlertRules = () =>
  request.get('/api/alerts/rules')

// 创建告警规则
export const createAlertRule = (data) =>
  request.post('/api/alerts/rules', data)

// 更新告警规则
export const updateAlertRule = (id, data) =>
  request.put(`/api/alerts/rules/${id}`, data)

// 删除告警规则
export const deleteAlertRule = (id) =>
  request.delete(`/api/alerts/rules/${id}`)

// ─── 通知对象 ────────────────────────────────────────────────────────────────

// 获取所有通知对象
export const getAlertContacts = () =>
  request.get('/api/alerts/contacts')

// 创建通知对象
export const createAlertContact = (data) =>
  request.post('/api/alerts/contacts', data)

// 更新通知对象
export const updateAlertContact = (id, data) =>
  request.put(`/api/alerts/contacts/${id}`, data)

// 删除通知对象
export const deleteAlertContact = (id) =>
  request.delete(`/api/alerts/contacts/${id}`)

// ─── 通知组 ──────────────────────────────────────────────────────────────────

// 获取所有通知组（含 contacts 成员信息）
export const getAlertGroups = () =>
  request.get('/api/alerts/groups')

// 创建通知组
export const createAlertGroup = (data) =>
  request.post('/api/alerts/groups', data)

// 更新通知组
export const updateAlertGroup = (id, data) =>
  request.put(`/api/alerts/groups/${id}`, data)

// 删除通知组
export const deleteAlertGroup = (id) =>
  request.delete(`/api/alerts/groups/${id}`)

// ─── 当前告警 ────────────────────────────────────────────────────────────────

// 获取当前活跃告警列表
export const getCurrentAlerts = (params) =>
  request.get('/api/alerts/current', { params })

// ─── 告警历史 ────────────────────────────────────────────────────────────────

// 获取历史告警记录（支持分页、服务器/时间筛选）
export const getAlertHistory = (params) =>
  request.get('/api/alerts/history', { params })

// 导出历史告警为 Excel
export const exportAlertHistory = (params) =>
  request.get('/api/alerts/history/export', { params, responseType: 'blob' })

// ─── 告警屏蔽 ────────────────────────────────────────────────────────────────

// 获取屏蔽记录列表
export const getAlertSilences = (params) =>
  request.get('/api/alerts/silences', { params })

// 创建屏蔽记录
export const createAlertSilence = (data) =>
  request.post('/api/alerts/silences', data)

// 取消屏蔽
export const deleteAlertSilence = (id) =>
  request.delete(`/api/alerts/silences/${id}`)
