<template>
  <div class="executions-container">
    <!-- 执行历史卡片 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>执行历史</span>
          <div style="display: flex; align-items: center; gap: 8px">
            <el-button type="primary" size="small" @click="fetchExecutions" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-dropdown @command="handleExportCommand">
              <el-button size="small" :loading="exporting">
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

      <!-- 筛选栏 -->
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
        <el-form-item label="脚本">
          <el-select
            v-model="filterScriptId"
            placeholder="全部"
            clearable
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
        <el-form-item label="执行类型">
          <el-select
            v-model="filterExecutionType"
            placeholder="全部"
            clearable
            style="width: 150px"
          >
            <el-option label="手动执行" value="manual" />
            <el-option label="定时任务" value="scheduled" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchExecutions">查询</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 执行历史列表 -->
      <el-table
        :data="executions"
        v-loading="loading"
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column label="脚本" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.script_name || '未知' }}
          </template>
        </el-table-column>
        <el-table-column label="服务器" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.server_hostname }} ({{ row.server_ip }})
          </template>
        </el-table-column>
        <el-table-column label="执行类型" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.execution_type === 'manual'" type="primary" size="small">手动执行</el-tag>
            <el-tag v-else-if="row.execution_type === 'scheduled'" type="success" size="small">定时任务</el-tag>
            <el-tag v-else type="info" size="small">{{ row.execution_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'success'" type="success">成功</el-tag>
            <el-tag v-else-if="row.status === 'failed'" type="danger">失败</el-tag>
            <el-tag v-else type="info">运行中</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="exit_code" label="退出码" width="80" />
        <el-table-column prop="started_at" label="开始时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.started_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="finished_at" label="结束时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.finished_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleViewDetail(row)">
              查看详情
            </el-button>
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

    <!-- 执行详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="执行详情"
      width="900px"
    >
      <el-descriptions :column="2" border v-if="currentExecution">
        <el-descriptions-item label="脚本">
          {{ currentExecution.script_name || '未知' }}
        </el-descriptions-item>
        <el-descriptions-item label="服务器">
          {{ currentExecution.server_hostname }} ({{ currentExecution.server_ip }})
        </el-descriptions-item>
        <el-descriptions-item label="执行类型">
          <el-tag v-if="currentExecution.execution_type === 'manual'" type="primary" size="small">手动执行</el-tag>
          <el-tag v-else-if="currentExecution.execution_type === 'scheduled'" type="success" size="small">定时任务</el-tag>
          <el-tag v-else type="info" size="small">{{ currentExecution.execution_type }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag v-if="currentExecution.status === 'success'" type="success">成功</el-tag>
          <el-tag v-else-if="currentExecution.status === 'failed'" type="danger">失败</el-tag>
          <el-tag v-else type="info">运行中</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="退出码">
          {{ currentExecution.exit_code }}
        </el-descriptions-item>
        <el-descriptions-item label="执行时长">
          {{ currentExecution.duration_seconds ? currentExecution.duration_seconds.toFixed(2) + '秒' : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="开始时间">
          {{ formatDate(currentExecution.started_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="结束时间">
          {{ formatDate(currentExecution.finished_at) }}
        </el-descriptions-item>
      </el-descriptions>

      <el-divider />

      <div style="margin-bottom: 10px">
        <strong>标准输出：</strong>
      </div>
      <el-input
        v-model="currentExecution.output"
        type="textarea"
        :rows="10"
        readonly
        style="font-family: 'Courier New', monospace"
      />

      <div style="margin: 20px 0 10px 0">
        <strong>错误输出：</strong>
      </div>
      <el-input
        v-model="currentExecution.error"
        type="textarea"
        :rows="5"
        readonly
        style="font-family: 'Courier New', monospace"
      />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getExecutions, getExecution, exportExecutions } from '@/api/executions'
import { getScripts } from '@/api/scripts'
import { getServers } from '@/api/servers'

// 数据
const loading = ref(false)
const exporting = ref(false)
const executions = ref([])
const scripts = ref([])
const servers = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

const dateRange = ref([])
const filterScriptId = ref(null)
const filterServerId = ref(null)
const filterExecutionType = ref(null)

const selectedRows = ref([])
const detailDialogVisible = ref(false)
const currentExecution = ref(null)

// 方法
const fetchExecutions = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    
    if (filterScriptId.value) {
      params.script_id = filterScriptId.value
    }

    if (filterServerId.value) {
      params.server_id = filterServerId.value
    }
    
    if (filterExecutionType.value) {
      params.execution_type = filterExecutionType.value
    }
    
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = new Date(dateRange.value[0]).toISOString().split('T')[0]
      params.end_date = new Date(dateRange.value[1]).toISOString().split('T')[0]
    }
    
    const response = await getExecutions(params)
    executions.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    ElMessage.error('获取执行历史失败')
  } finally {
    loading.value = false
  }
}

const fetchScripts = async () => {
  try {
    const response = await getScripts({ page: 1, page_size: 100 })
    scripts.value = response.data.items
  } catch (error) {
    // 静默失败，不影响主要功能
  }
}

const fetchServers = async () => {
  try {
    const response = await getServers({ page: 1, page_size: 100 })
    servers.value = response.data.items
  } catch (error) {
    // 静默失败，不影响主要功能
  }
}

const resetFilter = () => {
  dateRange.value = []
  filterScriptId.value = null
  filterServerId.value = null
  filterExecutionType.value = null
  currentPage.value = 1
  fetchExecutions()
}

const handleSelectionChange = (selection) => {
  selectedRows.value = selection
}

const handleViewDetail = async (row) => {
  try {
    const response = await getExecution(row.id)
    currentExecution.value = response.data
    detailDialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取执行详情失败')
  }
}

const handleExportCommand = async (command) => {
  if (command === 'selected') {
    if (selectedRows.value.length === 0) {
      ElMessage.warning('请先选择要导出的数据')
      return
    }
    await exportSelected()
  } else if (command === 'filtered') {
    await exportAllFiltered()
  }
}

const exportSelected = async () => {
  exporting.value = true
  try {
    const ids = selectedRows.value.map(row => row.id).join(',')
    const response = await exportExecutions({ ids })

    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `executions_${Date.now()}.xlsx`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

const exportAllFiltered = async () => {
  exporting.value = true
  try {
    const params = {}
    
    if (filterScriptId.value) {
      params.script_id = filterScriptId.value
    }

    if (filterServerId.value) {
      params.server_id = filterServerId.value
    }
    
    if (filterExecutionType.value) {
      params.execution_type = filterExecutionType.value
    }
    
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = new Date(dateRange.value[0]).toISOString().split('T')[0]
      params.end_date = new Date(dateRange.value[1]).toISOString().split('T')[0]
    }
    
    const response = await exportExecutions(params)

    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `executions_${Date.now()}.xlsx`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
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
  fetchScripts()
  fetchServers()
  fetchExecutions()
})

// 监听分页变化
watch([currentPage, pageSize], () => {
  fetchExecutions()
})
</script>

<style scoped>
.executions-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.executions-container :deep(.el-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.executions-container :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.executions-container :deep(.el-table) {
  flex: 1;
}

.executions-container :deep(.el-table__wrapper) {
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
</style>
