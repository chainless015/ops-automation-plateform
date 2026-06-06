<template>
  <div class="current-alerts">
    <el-card>
      <template #header>
        <div class="header">
          <span>当前告警</span>
          <el-button type="primary" size="small" @click="handleRefresh" :loading="loading">
            <el-icon><Refresh /></el-icon>
            {{ countdown > 0 ? `刷新 (${countdown}s)` : '刷新' }}
          </el-button>
        </div>
      </template>

      <el-table :data="alerts" v-loading="loading" style="width: 100%">
        <el-table-column label="规则名称" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.rule_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="服务器" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            {{ getServerName(row.server_id) }}
          </template>
        </el-table-column>
        <el-table-column label="指标" min-width="140" show-overflow-tooltip>
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
        <el-table-column label="最后发生" width="180">
          <template #default="{ row }">
            {{ formatTime(row.last_occurred_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="warning" size="small" @click="handleSilence(row)">屏蔽</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 20px; justify-content: flex-end; display: flex"
      />
    </el-card>

    <!-- 屏蔽对话框 -->
    <el-dialog v-model="silenceDialogVisible" title="屏蔽告警" width="500px">
      <el-form :model="silenceForm" label-width="100px">
        <el-form-item label="屏蔽方式">
          <el-radio-group v-model="silenceForm.type">
            <el-radio value="duration">按时长</el-radio>
            <el-radio value="until">屏蔽至</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="silenceForm.type === 'duration'" label="屏蔽时长">
          <el-input-number v-model="silenceForm.duration_minutes" :min="1" :max="10080" />
          <span style="margin-left: 10px">分钟</span>
        </el-form-item>
        <el-form-item v-if="silenceForm.type === 'until'" label="屏蔽至">
          <el-date-picker
            v-model="silenceForm.expires_at"
            type="datetime"
            placeholder="选择日期时间"
            style="width: 100%"
            :disabledDate="disabledDate"
          />
        </el-form-item>
        <el-form-item label="屏蔽原因">
          <el-input
            v-model="silenceForm.reason"
            type="textarea"
            :rows="3"
            placeholder="请输入屏蔽原因"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="silenceDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitSilence" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCurrentAlerts, createAlertSilence } from '@/api/alerts'
import { getServers } from '@/api/servers'
import { getSeverityTagType, getSeverityLabel, formatMetricValue, formatMetricThreshold } from '@/utils/alertSeverity'

const loading = ref(false)
const submitting = ref(false)
const alerts = ref([])
const servers = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
let autoRefreshTimer = null
let countdownTimer = null
const countdown = ref(60)

const resolveDialogVisible = ref(false)
const silenceDialogVisible = ref(false)
const currentAlert = ref(null)

const silenceForm = reactive({
  type: 'duration',
  duration_minutes: 60,
  expires_at: null,
  reason: ''
})

const fetchAlerts = async () => {
  loading.value = true
  try {
    const response = await getCurrentAlerts({
      page: currentPage.value,
      page_size: pageSize.value
    })
    alerts.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    ElMessage.error('获取告警列表失败')
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

const handleSilence = (row) => {
  currentAlert.value = row
  silenceForm.type = 'duration'
  silenceForm.duration_minutes = 60
  silenceForm.expires_at = null
  silenceForm.reason = ''
  silenceDialogVisible.value = true
}

const disabledDate = (time) => {
  // 禁用当前时间之前的日期
  return time.getTime() < Date.now()
}

const submitSilence = async () => {
  submitting.value = true
  try {
    const data = {
      rule_id: currentAlert.value.rule_id,  // 使用rule_id而不是alert_id，屏蔽整个规则
      server_id: currentAlert.value.server_id,
      reason: silenceForm.reason
    }
    
    if (silenceForm.type === 'duration') {
      data.duration_minutes = silenceForm.duration_minutes
    } else {
      data.expires_at = silenceForm.expires_at
    }
    
    await createAlertSilence(data)
    ElMessage.success('告警已屏蔽')
    silenceDialogVisible.value = false
    fetchAlerts()
  } catch (error) {
    ElMessage.error('屏蔽失败')
  } finally {
    submitting.value = false
  }
}

const startAutoRefresh = () => {
  stopAutoRefresh()
  countdown.value = 60
  
  countdownTimer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      fetchAlerts()
      countdown.value = 60
    }
  }, 1000)
}

const stopAutoRefresh = () => {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
}

const handleRefresh = () => {
  countdown.value = 60
  fetchAlerts()
}

onMounted(() => {
  fetchServers()
  fetchAlerts()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.current-alerts {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.current-alerts :deep(.el-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.current-alerts :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.current-alerts :deep(.el-table) {
  flex: 1;
}

.current-alerts :deep(.el-table__wrapper) {
  flex: 1;
  overflow: auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
