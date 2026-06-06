import request from '@/utils/axios'

// 获取服务器监控时序数据（CPU/内存/磁盘使用率）
// duration: '30m' | '1h' | '6h' | '24h' | '7d'
export const getServerMonitoring = (serverId, params) =>
  request.get(`/api/monitoring/server/${serverId}`, { params })
