<template>
  <div class="scheduled-tasks-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>定时任务</span>
          <div style="display: flex; align-items: center; gap: 8px">
            <el-button type="primary" size="small" @click="fetchTasks" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button type="primary" size="small" @click="handleAdd">
              <el-icon><Plus /></el-icon>
              添加任务
            </el-button>
          </div>
        </div>
      </template>

      <!-- 筛选栏 -->
      <el-form :inline="true" class="filter-form">
        <el-form-item label="脚本">
          <el-select
            v-model="filterScriptId"
            placeholder="全部"
            clearable
            @change="fetchTasks"
            style="width: 200px"
          >
            <el-option
              v-for="script in scripts"
              :key="script.id"
              :label="script.name"
              :value="script.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="服务器">
          <el-select
            v-model="filterServerId"
            placeholder="全部"
            clearable
            @change="fetchTasks"
            style="width: 200px"
          >
            <el-option
              v-for="server in servers"
              :key="server.id"
              :label="`${server.hostname} (${server.ip_address})`"
              :value="server.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="filterEnabled"
            placeholder="全部"
            clearable
            @change="fetchTasks"
            style="width: 150px"
          >
            <el-option label="已启用" :value="true" />
            <el-option label="已禁用" :value="false" />
          </el-select>
        </el-form-item>
      </el-form>

      <!-- 任务列表 -->
      <el-table
        :data="tasks"
        v-loading="loading"
        style="width: 100%"
      >
        <el-table-column prop="name" label="任务名称" width="180" />
        <el-table-column prop="description" label="描述" min-width="120" show-overflow-tooltip />
        <el-table-column label="脚本" width="150">
          <template #default="{ row }">
            {{ getScriptName(row.script_id) }}
          </template>
        </el-table-column>
        <el-table-column label="服务器" width="180">
          <template #default="{ row }">
            {{ getServerName(row.server_id) }}
          </template>
        </el-table-column>
        <el-table-column prop="cron_expression" label="Cron表达式" width="130" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.enabled" type="success">已启用</el-tag>
            <el-tag v-else type="info">已禁用</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="上次执行结果" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.last_run_status === 'success'" type="success" size="small">成功</el-tag>
            <el-tag v-else-if="row.last_run_status === 'failed'" type="danger" size="small">失败</el-tag>
            <el-tag v-else-if="row.last_run_status === 'running'" type="warning" size="small">运行中</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="上次执行时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.last_run_at) }}
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
        <el-table-column label="通知时机" width="120">
          <template #default="{ row }">
            <template v-if="row.notify_on_success || row.notify_on_failure">
              <el-tag v-if="row.notify_on_success" type="success" size="small" class="notify-when-tag">成功</el-tag>
              <el-tag v-if="row.notify_on_failure" type="danger" size="small" class="notify-when-tag">失败</el-tag>
            </template>
            <span v-else class="notification-empty">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="next_run_at" label="下次执行时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.next_run_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button
              :type="row.enabled ? 'warning' : 'success'"
              size="small"
              @click="handleToggle(row)"
            >
              {{ row.enabled ? '禁用' : '启用' }}
            </el-button>
            <el-button type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 20px; justify-content: flex-end; display: flex"
      />
    </el-card>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="700px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
      >
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            placeholder="请输入任务描述"
          />
        </el-form-item>
        <el-form-item label="选择脚本" prop="script_id">
          <el-select
            v-model="form.script_id"
            placeholder="请选择脚本"
            style="width: 100%"
            filterable
          >
            <el-option
              v-for="script in scripts"
              :key="script.id"
              :label="script.name"
              :value="script.id"
            >
              <span>{{ script.name }}</span>
              <span style="color: #8492a6; font-size: 12px; margin-left: 10px">
                {{ script.description }}
              </span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="选择服务器" prop="server_id">
          <el-select
            v-model="form.server_id"
            placeholder="请选择服务器"
            style="width: 100%"
            filterable
          >
            <el-option
              v-for="server in servers"
              :key="server.id"
              :label="`${server.hostname} (${server.ip_address})`"
              :value="server.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Cron表达式" prop="cron_expression">
          <el-input v-model="form.cron_expression" placeholder="例如: 0 2 * * * (每天凌晨2点)" />
          <div style="margin-top: 5px; font-size: 12px; color: #909399">
            格式：分 时 日 月 周
          </div>
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
        <el-form-item label="通知时机">
          <el-checkbox v-model="form.notify_on_success">成功时发送</el-checkbox>
          <el-checkbox v-model="form.notify_on_failure">失败时发送</el-checkbox>
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getScheduledTasks, createScheduledTask, updateScheduledTask, deleteScheduledTask, toggleScheduledTask } from '@/api/scheduledTasks'
import { getAlertContacts, getAlertGroups } from '@/api/alerts'
import { getScripts } from '@/api/scripts'
import { getServers } from '@/api/servers'

const NOTIFICATION_DISPLAY_LIMIT = 2

const hasNotifications = (row) => {
  return (row.contacts?.length || 0) + (row.groups?.length || 0) > 0
}

const getNotificationItems = (row) => {
  const contactNames = (row.contacts || []).map(contact => contact.name)
  const groupNames = (row.groups || []).map(group => `${group.name}(组)`)
  return [...contactNames, ...groupNames]
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

// 数据
const loading = ref(false)
const submitting = ref(false)
const tasks = ref([])
const scripts = ref([])
const servers = ref([])
const contacts = ref([])
const groups = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const dialogVisible = ref(false)
const dialogTitle = ref('')
const formRef = ref(null)
const isEdit = ref(false)
const editId = ref(null)

const filterScriptId = ref(null)
const filterServerId = ref(null)
const filterEnabled = ref(null)

const form = reactive({
  name: '',
  description: '',
  script_id: null,
  server_id: null,
  cron_expression: '',
  enabled: true,
  contact_ids: [],
  group_ids: [],
  notify_on_success: false,
  notify_on_failure: false
})

const rules = {
  name: [
    { required: true, message: '请输入任务名称', trigger: 'blur' }
  ],
  script_id: [
    { required: true, message: '请选择脚本', trigger: 'change' }
  ],
  server_id: [
    { required: true, message: '请选择服务器', trigger: 'change' }
  ],
  cron_expression: [
    { required: true, message: '请输入Cron表达式', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        const parts = value.trim().split(/\s+/)
        if (parts.length !== 5) {
          callback(new Error('Cron表达式必须包含5个部分：分 时 日 月 周'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 方法
const fetchTasks = async () => {
  loading.value = true
  try {
    const response = await getScheduledTasks({
      page: currentPage.value,
      page_size: pageSize.value,
      script_id: filterScriptId.value || undefined,
      server_id: filterServerId.value || undefined,
      enabled: filterEnabled.value !== null ? filterEnabled.value : undefined
    })
    tasks.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    ElMessage.error('获取任务列表失败')
  } finally {
    loading.value = false
  }
}

const fetchScripts = async () => {
  try {
    const response = await getScripts({ page: 1, page_size: 100 })
    scripts.value = response.data.items
  } catch (error) {
    ElMessage.error('获取脚本列表失败')
  }
}

const fetchServers = async () => {
  try {
    const response = await getServers({ page: 1, page_size: 100 })
    servers.value = response.data.items
  } catch (error) {
    ElMessage.error('获取服务器列表失败')
  }
}

const fetchContacts = async () => {
  try {
    const response = await getAlertContacts()
    contacts.value = response.data
  } catch (error) {
    ElMessage.error('获取通知对象失败')
  }
}

const fetchGroups = async () => {
  try {
    const response = await getAlertGroups()
    groups.value = response.data
  } catch (error) {
    ElMessage.error('获取通知组失败')
  }
}

const handleAdd = () => {
  isEdit.value = false
  dialogTitle.value = '添加定时任务'
  resetForm()
  dialogVisible.value = true
}

const handleEdit = async (row) => {
  isEdit.value = true
  editId.value = row.id
  dialogTitle.value = '编辑定时任务'
  
  Object.assign(form, {
    name: row.name,
    description: row.description,
    script_id: row.script_id,
    server_id: row.server_id,
    cron_expression: row.cron_expression,
    enabled: row.enabled,
    contact_ids: row.contacts ? row.contacts.map(c => c.id) : [],
    group_ids: row.groups ? row.groups.map(g => g.id) : [],
    notify_on_success: row.notify_on_success || false,
    notify_on_failure: row.notify_on_failure || false
  })
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      if (isEdit.value) {
        await updateScheduledTask(editId.value, form)
        ElMessage.success('更新任务成功')
      } else {
        await createScheduledTask(form)
        ElMessage.success('添加任务成功')
      }
      dialogVisible.value = false
      fetchTasks()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    } finally {
      submitting.value = false
    }
  })
}

const handleToggle = async (row) => {
  try {
    await toggleScheduledTask(row.id)
    ElMessage.success(`任务已${row.enabled ? '禁用' : '启用'}`)
    fetchTasks()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除任务"${row.name}"吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await deleteScheduledTask(row.id)
    ElMessage.success('删除成功')
    fetchTasks()
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
    script_id: null,
    server_id: null,
    cron_expression: '',
    enabled: true,
    contact_ids: [],
    group_ids: [],
    notify_on_success: false,
    notify_on_failure: false
  })
  formRef.value?.clearValidate()
}

const getScriptName = (scriptId) => {
  const script = scripts.value.find(s => s.id === scriptId)
  return script ? script.name : '未知'
}

const getServerName = (serverId) => {
  const server = servers.value.find(s => s.id === serverId)
  return server ? `${server.hostname} (${server.ip_address})` : '未知'
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
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

// 生命周期
onMounted(() => {
  fetchTasks()
  fetchScripts()
  fetchServers()
  fetchContacts()
  fetchGroups()
})

// 监听分页变化
watch([currentPage, pageSize], () => {
  fetchTasks()
})
</script>

<style scoped>
.scheduled-tasks-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.scheduled-tasks-container :deep(.el-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.scheduled-tasks-container :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.scheduled-tasks-container :deep(.el-table) {
  flex: 1;
}

.scheduled-tasks-container :deep(.el-table__wrapper) {
  flex: 1;
  overflow: auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-form {
  margin-bottom: 20px;
  flex-shrink: 0;
}

.notification-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.notification-tag {
  max-width: 100%;
}

.notification-empty {
  color: #909399;
}

.notify-when-tag + .notify-when-tag {
  margin-left: 4px;
}
</style>
