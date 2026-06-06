<template>
  <div class="alert-history">
    <el-card>
      <template #header>
        <div class="header">
          <span>历史告警</span>
          <div style="display: flex; align-items: center; gap: 8px">
            <el-button type="primary" size="small" @click="fetchHistory" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-dropdown @command="handleExportCommand">
              <el-button size="small" :loading="loading">
                <el-icon><Download /></el-icon>
                导出
                <el-icon class="el-icon--right"><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="selected" :disabled="selectedRows.length === 0">
                    导出选中 ({{ selectedRows.length }})
                  </el-dropdown-item>
                  <el-dropdown-item command="filtered">
                    导出所有 ({{ total }})
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </template>

      <!-- 筛选条件 -->
      <el-form :inline="true" class="filter-form">
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            format="YYYY-MM-DD HH:mm:ss"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 400px"
          />
        </el-form-item>
        <el-form-item label="服务器">
          <el-select v-model="serverId" placeholder="全部" clearable style="width: 200px">
            <el-option
              v-for="server in servers"
              :key="server.id"
              :label="`${server.hostname} (${server.ip_address})`"
              :value="server.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchHistory">查询</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="alerts" v-loading="loading" style="width: 100%" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" />
        <el-table-column label="规则名称" min-width="100" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.rule_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="服务器" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            {{ getServerName(row.server_id) }}
          </template>
        </el-table-column>
        <el-table-column label="指标" min-width="100" show-overflow-tooltip>
          <template #default="{ row }">
            <el-tag v-if="row.metric_type === 'cpu'" type="primary">CPU使用率</el-tag>
            <el-tag v-else-if="row.metric_type === 'memory'" type="success">内存使用率</el-tag>
            <el-tag v-else-if="row.metric_type === 'disk_mount'" type="warning">磁盘:{{ row.metric_label }}</el-tag>
            <el-tag v-else-if="row.metric_type === 'tcp_conn'" type="info">TCP:{{ row.metric_label === 'CurrEstab' ? '已建立' : row.metric_label === 'AllEstab' ? '所有' : row.metric_label }}</el-tag>
            <el-tag v-else-if="row.metric_type === 'host_up'" type="danger">主机存活</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="当前值" width="100">
          <template #default="{ row }">
            {{ formatMetricValue(row.current_value, row.metric_type) }}
          </template>
        </el-table-column>
        <el-table-column label="阈值" width="100">
          <template #default="{ row }">
            {{ formatMetricThreshold(row.operator, row.threshold, row.metric_type) }}
          </template>
        </el-table-column>
        <el-table-column label="级别" width="100">
          <template #default="{ row }">
            <el-tag :type="getSeverityTagType(row.severity)">{{ getSeverityLabel(row.severity) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="触发时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.fired_at) }}
          </template>
        </el-table-column>
        <el-table-column label="恢复时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.resolved_at) }}
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        :prev-text="'上一页'"
        :next-text="'下一页'"
        style="margin-top: 20px; justify-content: flex-end; display: flex"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getAlertHistory, exportAlertHistory } from '@/api/alerts'
import { getServers } from '@/api/servers'
import { getSeverityTagType, getSeverityLabel, formatMetricValue, formatMetricThreshold } from '@/utils/alertSeverity'

const loading = ref(false)
const alerts = ref([])
const servers = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const dateRange = ref([])
const serverId = ref(null)
const selectedRows = ref([])

const fetchHistory = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    
    if (serverId.value) {
      params.server_id = serverId.value
    }
    
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_time = new Date(dateRange.value[0]).toISOString()
      params.end_time = new Date(dateRange.value[1]).toISOString()
    }
    
    const response = await getAlertHistory(params)
    alerts.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    ElMessage.error('获取历史告警失败')
  } finally {
    loading.value = false
  }
}

const fetchServers = async () => {
  try {
    const response = await getServers({ page: 1, page_size: 100 })
    servers.value = response.data.items
  } catch (error) {
    console.error('获取服务器列表失败', error)
  }
}

const getServerName = (serverId) => {
  const server = servers.value.find(s => s.id === serverId)
  return server ? `${server.hostname} (${server.ip_address})` : '未知'
}

const formatTime = (time) => {
  if (!time) return '-'
  const date = new Date(time)
  return date.toLocaleString('zh-CN', { 
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

const resetFilter = () => {
  dateRange.value = []
  serverId.value = null
  currentPage.value = 1
  fetchHistory()
}

const handleSelectionChange = (selection) => {
  selectedRows.value = selection
}

const handleExportCommand = async (command) => {
  if (command === 'selected') {
    if (selectedRows.value.length === 0) {
      ElMessage.warning('请先选择要导出的数据')
      return
    }
    ElMessage.info('选中导出功能暂不支持，请使用"导出所有"')
  } else if (command === 'filtered') {
    await exportAllFiltered()
  }
}

const exportAllFiltered = async () => {
  loading.value = true
  try {
    const params = {}
    
    if (serverId.value) {
      params.server_id = serverId.value
    }
    
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_time = new Date(dateRange.value[0]).toISOString()
      params.end_time = new Date(dateRange.value[1]).toISOString()
    }
    
    const response = await exportAlertHistory(params)
    
    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `alert_history_${Date.now()}.xlsx`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  } finally {
    loading.value = false
  }
}

const handleExport = () => {
  exportData(alerts.value)
}

onMounted(() => {
  fetchServers()
  fetchHistory()
})

watch([currentPage, pageSize], () => {
  fetchHistory()
})
</script>

<style scoped>
.alert-history {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.alert-history :deep(.el-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.alert-history :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.alert-history :deep(.el-table) {
  flex: 1;
}

.alert-history :deep(.el-table__wrapper) {
  flex: 1;
  overflow: auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-form {
  margin-bottom: 20px;
  flex-shrink: 0;
}
</style>
