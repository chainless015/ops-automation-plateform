/** 告警级别：4级最高，1级最低 */
export const SEVERITY_LABELS = {
  level1: '1级告警',
  level2: '2级告警',
  level3: '3级告警',
  level4: '4级告警'
}

const SEVERITY_TAG_TYPES = {
  level4: 'danger',
  level3: 'warning',
  level2: 'primary',
  level1: 'info'
}

export const SEVERITY_CHART_COLORS = {
  level4: '#F56C6C',
  level3: '#E6A23C',
  level2: '#409EFF',
  level1: '#909399'
}

export function getSeverityTagType(severity) {
  return SEVERITY_TAG_TYPES[severity] || 'info'
}

export function getSeverityLabel(severity) {
  return SEVERITY_LABELS[severity] || severity
}

const TCP_TYPE_LABELS = {
  CurrEstab: '已建立',
  AllEstab: '所有'
}

export function isCountMetric(metricType) {
  return metricType === 'tcp_conn' || metricType === 'host_up'
}

export function getMetricUnit(metricType) {
  if (metricType === 'tcp_conn') return '个'
  if (metricType === 'host_up') return ''
  return '%'
}

export function getMetricTagLabel(metricType, metricLabel) {
  if (metricType === 'cpu') return 'CPU使用率'
  if (metricType === 'memory') return '内存使用率'
  if (metricType === 'disk_mount') return `磁盘:${metricLabel || ''}`
  if (metricType === 'tcp_conn') return `TCP:${TCP_TYPE_LABELS[metricLabel] || metricLabel || ''}`
  if (metricType === 'host_up') return '主机存活'
  return metricType
}

export function formatMetricValue(value, metricType) {
  if (metricType === 'tcp_conn') return `${Math.round(value)}个`
  if (metricType === 'host_up') return value < 1 ? '离线' : '在线'
  return `${value.toFixed(2)}%`
}

export function formatMetricThreshold(operator, threshold, metricType) {
  if (metricType === 'tcp_conn') return `${operator} ${Math.round(threshold)}个`
  if (metricType === 'host_up') return `${operator} ${Math.round(threshold)}`
  return `${operator} ${Number(threshold).toFixed(2)}%`
}
