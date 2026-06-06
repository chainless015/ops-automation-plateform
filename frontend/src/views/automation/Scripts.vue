<template>
  <div class="scripts-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>脚本管理</span>
          <div style="display: flex; align-items: center; gap: 8px">
            <el-button type="primary" size="small" @click="fetchScripts" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button type="primary" size="small" @click="handleAdd">
              <el-icon><Plus /></el-icon>
              添加脚本
            </el-button>
          </div>
        </div>
      </template>

      <!-- 搜索栏 -->
      <el-form :inline="true" class="search-form">
        <el-form-item>
          <el-input
            v-model="searchQuery"
            placeholder="搜索脚本名称或描述"
            clearable
            @clear="handleSearch"
            @keyup.enter="handleSearch"
            style="width: 300px"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 脚本列表 -->
      <el-table
        :data="scripts"
        v-loading="loading"
        style="width: 100%"
      >
        <el-table-column prop="name" label="脚本名称" width="200" />
        <el-table-column prop="description" label="描述" min-width="300" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button type="success" size="small" @click="handleExecute(row)">
              <el-icon><VideoPlay /></el-icon>
              执行
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

    <!-- 执行脚本对话框 -->
    <el-dialog
      v-model="executeDialogVisible"
      title="执行脚本"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form label-width="100px">
        <el-form-item label="脚本名称">
          <el-input v-model="executeForm.scriptName" disabled />
        </el-form-item>
        <el-form-item label="选择服务器" required>
          <el-select
            v-model="executeForm.serverId"
            placeholder="请选择要执行的服务器"
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
      </el-form>
      <template #footer>
        <el-button @click="executeDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          @click="handleExecuteSubmit"
          :loading="executing"
          :disabled="!executeForm.serverId"
        >
          执行
        </el-button>
      </template>
    </el-dialog>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="800px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="脚本名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入脚本名称（必须以.sh结尾）" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            placeholder="请输入脚本描述"
          />
        </el-form-item>
        <el-form-item label="脚本内容" prop="content">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="15"
            placeholder="请输入Shell脚本内容"
            style="font-family: 'Courier New', monospace"
          />
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
import { useRouter } from 'vue-router'
import { getScripts, getScript, createScript, updateScript, deleteScript } from '@/api/scripts'
import { getServers } from '@/api/servers'
import { createExecution } from '@/api/executions'

// 数据
const router = useRouter()
const loading = ref(false)
const submitting = ref(false)
const executing = ref(false)
const scripts = ref([])
const servers = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const searchQuery = ref('')
const dialogVisible = ref(false)
const executeDialogVisible = ref(false)
const dialogTitle = ref('')
const formRef = ref(null)
const isEdit = ref(false)
const editId = ref(null)

const executeForm = reactive({
  scriptId: null,
  scriptName: '',
  serverId: null
})

const form = reactive({
  name: '',
  description: '',
  content: ''
})

const rules = {
  name: [
    { required: true, message: '请输入脚本名称', trigger: 'blur' },
    { pattern: /\.sh$/, message: '脚本名称必须以.sh结尾', trigger: 'blur' }
  ],
  description: [
    { required: true, message: '请输入脚本描述', trigger: 'blur' }
  ],
  content: [
    { required: true, message: '请输入脚本内容', trigger: 'blur' }
  ]
}

// 方法
const fetchScripts = async () => {
  loading.value = true
  try {
    const response = await getScripts({
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchQuery.value || undefined
    })
    scripts.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    ElMessage.error('获取脚本列表失败')
  } finally {
    loading.value = false
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

const handleSearch = () => {
  currentPage.value = 1
  fetchScripts()
}

const handleAdd = () => {
  isEdit.value = false
  dialogTitle.value = '添加脚本'
  resetForm()
  dialogVisible.value = true
}

const handleEdit = async (row) => {
  isEdit.value = true
  editId.value = row.id
  dialogTitle.value = '编辑脚本'
  
  // 获取完整的脚本内容
  try {
    const response = await getScript(row.id)
    Object.assign(form, {
      name: response.data.name,
      description: response.data.description,
      content: response.data.content
    })
    dialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取脚本详情失败')
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      if (isEdit.value) {
        await updateScript(editId.value, form)
        ElMessage.success('更新脚本成功')
      } else {
        await createScript(form)
        ElMessage.success('添加脚本成功')
      }
      dialogVisible.value = false
      fetchScripts()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    } finally {
      submitting.value = false
    }
  })
}

const handleExecute = (row) => {
  executeForm.scriptId = row.id
  executeForm.scriptName = row.name
  executeForm.serverId = null
  executeDialogVisible.value = true
}

const handleExecuteSubmit = async () => {
  executing.value = true
  try {
    await createExecution({
      script_id: executeForm.scriptId,
      server_id: executeForm.serverId
    })
    executeDialogVisible.value = false
    ElMessageBox.confirm(
      '脚本已提交执行，是否立即前往执行记录查看结果？',
      '执行成功',
      {
        confirmButtonText: '去查看',
        cancelButtonText: '留在此页',
        type: 'success'
      }
    ).then(() => {
      router.push('/automation/executions')
    }).catch(() => {})
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '执行失败')
  } finally {
    executing.value = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除脚本"${row.name}"吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await deleteScript(row.id)
    ElMessage.success('删除成功')
    fetchScripts()
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
    content: ''
  })
  formRef.value?.clearValidate()
}

const formatDate = (dateString) => {
  if (!dateString) return ''
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
})

// 监听分页变化
watch([currentPage, pageSize], () => {
  fetchScripts()
})
</script>

<style scoped>
.scripts-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.scripts-container :deep(.el-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.scripts-container :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.scripts-container :deep(.el-table) {
  flex: 1;
}

.scripts-container :deep(.el-table__wrapper) {
  flex: 1;
  overflow: auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-form {
  margin-bottom: 20px;
  flex-shrink: 0;
}
</style>
