<template>
  <div class="alert-rules">
    <el-card>
      <template #header>
        <div class="header">
          <span>告警规则</span>
          <div style="display: flex; align-items: center; gap: 8px">
            <el-button type="primary" size="small" @click="handleRefresh" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button type="primary" size="small" @click="handleAdd">
              <el-icon><Plus /></el-icon>
              添加规则
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="rules" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="规则名称" min-width="100" show-overflow-tooltip />
        <el-table-column label="服务器" min-width="140" show-overflow-tooltip>
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
        <el-table-column label="条件" width="120">
          <template #default="{ row }">
            {{ formatCondition(row) }}
          </template>
        </el-table-column>
        <el-table-column label="持续时间" width="100">
          <template #default="{ row }">
            {{ row.duration }}分钟
          </template>
        </el-table-column>
        <el-table-column label="重发间隔" width="100">
          <template #default="{ row }">
            {{ row.repeat_interval || 30 }}分钟
          </template>
        </el-table-column>
        <el-table-column label="级别" width="100">
          <template #default="{ row }">
            <el-tag :type="getSeverityTagType(row.severity)">{{ getSeverityLabel(row.severity) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="通知对象" min-width="160">
          <template #default="{ row }">
            <el-tooltip
              :content="getNotificationTooltip(row)"
              placement="top"
              :disabled="!hasNotifications(row)"
            >
              <div class="notification-cell">
                <template v-if="hasNotifications(row)">
                  <el-tag
                    v-for="contact in getVisibleContacts(row)"
                    :key="`contact-${contact.id}`"
                    size="small"
                    class="notification-tag"
                  >
                    {{ contact.name }}
                  </el-tag>
                  <el-tag
                    v-for="group in getVisibleGroups(row)"
                    :key="`group-${group.id}`"
                    size="small"
                    type="success"
                    class="notification-tag"
                  >
                    {{ group.name }}
                  </el-tag>
                  <el-tag v-if="getNotificationExtraCount(row) > 0" size="small" type="info" class="notification-tag">
                    +{{ getNotificationExtraCount(row) }}
                  </el-tag>
                </template>
                <span v-else class="notification-empty">-</span>
              </div>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" @change="handleToggle(row)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="700px"
      destroy-on-close
      @closed="handleDialogClosed"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入规则名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            placeholder="请输入描述（可选）"
          />
        </el-form-item>
        <el-form-item label="服务器" prop="server_id">
          <el-select v-model="form.server_id" placeholder="请选择服务器" style="width: 100%">
            <el-option
              v-for="server in servers"
              :key="server.id"
              :label="`${server.hostname} (${server.ip_address})`"
              :value="server.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="监控指标" prop="metric_type">
          <el-select v-model="form.metric_type" placeholder="请选择监控指标" style="width: 100%" @change="handleMetricTypeChange">
            <el-option label="CPU使用率" value="cpu" />
            <el-option label="内存使用率" value="memory" />
            <el-option label="磁盘使用率(按挂载点)" value="disk_mount" />
            <el-option label="TCP连接数" value="tcp_conn" />
            <el-option label="主机存活" value="host_up" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.metric_type === 'host_up'" label="触发条件">
          <span class="host-up-hint">主机离线时触发（node_exporter 不可达或采集失败）</span>
        </el-form-item>
        <!-- 磁盘挂载点输入 -->
        <el-form-item v-if="form.metric_type === 'disk_mount'" label="挂载点" prop="metric_label">
          <el-input v-model="form.metric_label" placeholder="请输入挂载点，如 / 或 /data" />
        </el-form-item>
        <!-- TCP连接类型选择 -->
        <el-form-item v-if="form.metric_type === 'tcp_conn'" label="连接类型" prop="metric_label">
          <el-select v-model="form.metric_label" placeholder="请选择TCP连接类型" style="width: 100%">
            <el-option label="已建立连接(CurrEstab)" value="CurrEstab" />
            <el-option label="所有连接(AllEstab)" value="AllEstab" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.metric_type !== 'host_up'" label="条件" prop="operator">
          <div style="display: flex; align-items: center; gap: 10px; width: 100%;">
            <el-select v-model="form.operator" placeholder="请选择条件" style="width: 150px;">
              <el-option label="大于 (>)" value=">" />
              <el-option label="大于等于 (>=)" value=">=" />
              <el-option label="小于 (<)" value="<" />
              <el-option label="小于等于 (<=)" value="<=" />
              <el-option label="等于 (==)" value="==" />
            </el-select>
            <el-input-number
              :key="form.metric_type"
              v-model="form.threshold"
              :min="0"
              :max="isCountMetric(form.metric_type) ? undefined : 100"
              :precision="isCountMetric(form.metric_type) ? 0 : 2"
              style="flex: 1;"
            />
            <span>{{ thresholdUnit }}</span>
          </div>
        </el-form-item>
        <el-form-item label="持续时间" prop="duration">
          <el-input-number v-model="form.duration" :min="1" :max="1440" />
          <span style="margin-left: 10px">分钟</span>
        </el-form-item>
        <el-form-item label="重发间隔" prop="repeat_interval">
          <el-input-number v-model="form.repeat_interval" :min="1" :max="1440" />
          <span style="margin-left: 10px">分钟</span>
        </el-form-item>
        <el-form-item label="告警级别" prop="severity">
          <el-radio-group v-model="form.severity">
            <el-radio value="level1">1级告警</el-radio>
            <el-radio value="level2">2级告警</el-radio>
            <el-radio value="level3">3级告警</el-radio>
            <el-radio value="level4">4级告警</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="通知对象">
          <el-select
            v-model="form.contact_ids"
            multiple
            placeholder="请选择通知对象"
            style="width: 100%"
          >
            <el-option
              v-for="contact in contacts"
              :key="contact.id"
              :label="`${contact.name} (${contact.email})`"
              :value="contact.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="通知组">
          <el-select
            v-model="form.group_ids"
            multiple
            placeholder="请选择通知组"
            style="width: 100%"
          >
            <el-option
              v-for="group in groups"
              :key="group.id"
              :label="group.name"
              :value="group.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAlertRules, createAlertRule, updateAlertRule, deleteAlertRule, getAlertContacts, getAlertGroups } from '@/api/alerts'
import { getServers } from '@/api/servers'
import { getSeverityTagType, getSeverityLabel, isCountMetric, getMetricUnit } from '@/utils/alertSeverity'

const HOST_UP_OPERATOR = '<'
const HOST_UP_THRESHOLD = 1

const applyHostUpFixedCondition = () => {
  if (form.metric_type === 'host_up') {
    form.operator = HOST_UP_OPERATOR
    form.threshold = HOST_UP_THRESHOLD
    form.metric_label = ''
  }
}

const formatCondition = (row) => {
  if (row.metric_type === 'host_up') return '离线时触发'
  return `${row.operator} ${formatThreshold(row)}`
}

const formatThreshold = (row) => {
  const unit = getMetricUnit(row.metric_type)
  const value = isCountMetric(row.metric_type)
    ? Math.round(row.threshold)
    : Number(row.threshold).toFixed(2)
  return `${value}${unit}`
}

const thresholdUnit = computed(() => getMetricUnit(form.metric_type))

const NOTIFICATION_DISPLAY_LIMIT = 2

const hasNotifications = (row) => {
  return (row.contacts?.length || 0) + (row.groups?.length || 0) > 0
}

const getNotificationItems = (row) => {
  const contacts = (row.contacts || []).map(contact => contact.name)
  const groups = (row.groups || []).map(group => `${group.name}(组)`)
  return [...contacts, ...groups]
}

const getNotificationTooltip = (row) => getNotificationItems(row).join('、')

const getVisibleContacts = (row) => (row.contacts || []).slice(0, NOTIFICATION_DISPLAY_LIMIT)

const getVisibleGroups = (row) => {
  const contactCount = row.contacts?.length || 0
  if (contactCount >= NOTIFICATION_DISPLAY_LIMIT) {
    return []
  }
  return (row.groups || []).slice(0, NOTIFICATION_DISPLAY_LIMIT - contactCount)
}

const getNotificationExtraCount = (row) => {
  const total = (row.contacts?.length || 0) + (row.groups?.length || 0)
  const visible = getVisibleContacts(row).length + getVisibleGroups(row).length
  return Math.max(total - visible, 0)
}

const loading = ref(false)
const submitting = ref(false)
const rules = ref([])
const servers = ref([])
const contacts = ref([])
const groups = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('')
const formRef = ref(null)
const isEdit = ref(false)
const editId = ref(null)
const loadingMountPoints = ref(false)

const form = reactive({
  name: '',
  description: '',
  server_id: null,
  metric_type: '',
  metric_label: '',
  operator: '>',
  threshold: 80,
  duration: 5,
  repeat_interval: 30,
  severity: 'level3',
  contact_ids: [],
  group_ids: [],
  enabled: true
})

const formRules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  server_id: [{ required: true, message: '请选择服务器', trigger: 'change' }],
  metric_type: [{ required: true, message: '请选择监控指标', trigger: 'change' }],
  metric_label: [
    {
      validator: (rule, value, callback) => {
        if (form.metric_type === 'disk_mount' && !value) {
          callback(new Error('请选择磁盘挂载点'))
        } else if (form.metric_type === 'tcp_conn' && !value) {
          callback(new Error('请选择连接类型'))
        } else {
          callback()
        }
      },
      trigger: ['change', 'blur']
    }
  ],
  operator: [{ required: true, message: '请选择条件', trigger: 'change' }],
  threshold: [{ required: true, message: '请输入阈值', trigger: 'blur' }],
  duration: [{ required: true, message: '请输入持续时间', trigger: 'blur' }],
  repeat_interval: [{ required: true, message: '请输入重发间隔', trigger: 'blur' }]
}

const loadAllData = async () => {
  const [rulesRes, serversRes, contactsRes, groupsRes] = await Promise.all([
    getAlertRules(),
    getServers({ page: 1, page_size: 100 }),
    getAlertContacts(),
    getAlertGroups()
  ])
  rules.value = rulesRes.data
  servers.value = serversRes.data.items
  contacts.value = contactsRes.data
  groups.value = groupsRes.data
}

const fetchRules = async () => {
  loading.value = true
  try {
    await loadAllData()
  } catch (error) {
    ElMessage.error('获取告警规则失败')
  } finally {
    loading.value = false
  }
}

const handleRefresh = () => fetchRules()

const getServerName = (serverId) => {
  const server = servers.value.find(s => s.id === serverId)
  return server ? `${server.hostname} (${server.ip_address})` : '未知'
}

const handleMetricTypeChange = (metricType) => {
  form.metric_label = ''
  if (metricType === 'host_up') {
    form.operator = HOST_UP_OPERATOR
    form.threshold = HOST_UP_THRESHOLD
    form.duration = 2
  } else if (metricType === 'tcp_conn') {
    form.threshold = Math.min(Math.round(form.threshold || 100), 999999)
  } else if (form.threshold > 100) {
    form.threshold = 80
  }
}

const handleAdd = () => {
  isEdit.value = false
  editId.value = null
  dialogTitle.value = '添加告警规则'
  resetForm()
  dialogVisible.value = true
}

const handleEdit = async (row) => {
  isEdit.value = true
  editId.value = row.id
  dialogTitle.value = '编辑告警规则'
  Object.assign(form, {
    name: row.name,
    description: row.description || '',
    server_id: row.server_id,
    metric_type: row.metric_type,
    metric_label: row.metric_label || '',
    operator: row.operator,
    threshold: row.threshold,
    duration: row.duration,
    repeat_interval: row.repeat_interval || 30,
    severity: row.severity,
    contact_ids: row.contacts ? row.contacts.map(c => c.id) : [],
    group_ids: row.groups ? row.groups.map(g => g.id) : [],
    enabled: row.enabled
  })
  dialogVisible.value = true
  applyHostUpFixedCondition()
  await nextTick()
  formRef.value?.clearValidate()
}

const handleDialogClosed = () => {
  isEdit.value = false
  editId.value = null
  resetForm()
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return

    applyHostUpFixedCondition()

    submitting.value = true
    try {
      if (isEdit.value) {
        await updateAlertRule(editId.value, form)
        ElMessage.success('更新成功')
      } else {
        await createAlertRule(form)
        ElMessage.success('添加成功')
      }
      dialogVisible.value = false
      fetchRules()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    } finally {
      submitting.value = false
    }
  })
}

const handleToggle = async (row) => {
  try {
    await updateAlertRule(row.id, { enabled: row.enabled })
    ElMessage.success(row.enabled ? '已启用' : '已禁用')
  } catch (error) {
    row.enabled = !row.enabled
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除告警规则"${row.name}"吗？`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await deleteAlertRule(row.id)
    ElMessage.success('删除成功')
    fetchRules()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const resetForm = () => {
  Object.assign(form, {
    name: '',
    description: '',
    server_id: null,
    metric_type: '',
    metric_label: '',
    operator: '>',
    threshold: 80,
    duration: 5,
    repeat_interval: 30,
    severity: 'level3',
    contact_ids: [],
    group_ids: [],
    enabled: true
  })
}

onMounted(() => {
  fetchRules()
})
</script>

<style scoped>
.alert-rules {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.alert-rules :deep(.el-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.alert-rules :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.alert-rules :deep(.el-table) {
  flex: 1;
}

.alert-rules :deep(.el-table__wrapper) {
  flex: 1;
  overflow: auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.notification-cell {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  overflow: hidden;
  gap: 4px;
  max-width: 100%;
}

.notification-tag {
  flex-shrink: 0;
  max-width: 88px;
}

.notification-tag :deep(.el-tag__content) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notification-empty {
  color: #909399;
}

.host-up-hint {
  color: #909399;
  font-size: 13px;
}
</style>
