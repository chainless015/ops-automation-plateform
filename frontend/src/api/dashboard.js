import request from '@/utils/axios'

// 获取仪表盘统计数据（当前告警数、今日告警、执行数、定时任务数、7天趋势、级别分布）
export const getDashboardStats = () =>
  request.get('/api/dashboard/stats')

// 获取最近执行记录
export const getRecentExecutions = () =>
  request.get('/api/dashboard/recent-executions')

// 获取资源使用 Top 5 服务器（CPU/内存/磁盘）
export const getTopServers = () =>
  request.get('/api/dashboard/top-servers')
