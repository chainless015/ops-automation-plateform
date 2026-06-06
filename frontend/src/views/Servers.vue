<template>
  <div class="servers-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>服务器列表</span>
          <el-button type="primary" @click="showAddDialog">
            <el-icon><Plus /></el-icon>
            添加服务器
          </el-button>
        </div>
      </template>

      <!-- 筛选条件 -->
      <el-form :inline="true" :model="queryParams" class="filter-form">
        <el-form-item label="主机名/IP">
          <el-input
            v-model="queryParams.search"
            placeholder="请输入主机名或IP地址"
            clearable
            style="width: 250px"
            @keyup.enter="fetchServers"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="queryParams.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="全部" value="" />
            <el-option label="在线" value="online" />
            <el-option label="离线" value="offline" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchServers">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 服务器列表表格 -->
      <el-table :data="servers" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="hostname" label="主机名" min-width="150" />
        <el-table-column prop="ip_address" label="IP地址" min-width="150" />
        <el-table-column prop="ssh_port" label="SSH端口" width="100" />
        <el-table-column prop="ssh_username" label="SSH用户" width="120" />
        <el-table-column prop="purpose" label="用途" min-width="150" show-overflow-tooltip />
        <el-table-column prop="owner" label="负责人" width="100" />
        <el-table-column prop="online_status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.online_status === 'online' ? 'success' : 'info'">
              {{ row.online_status === 'online' ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button type="success" size="small" @click="goToMonitoring(row)">监控</el-button>
            <el-button type="primary" size="small" @click="showEditDialog(row)">编辑</el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="queryParams.page"
        v-model:page-size="queryParams.page_size"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="fetchServers"
        @current-change="fetchServers"
        class="pagination"
      />
    </el-card>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      @close="resetForm"
    >
      <el-form
        ref="serverFormRef"
        :model="serverForm"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="主机名" prop="hostname">
          <el-input v-model="serverForm.hostname" placeholder="请输入主机名" />
        </el-form-item>
        <el-form-item label="IP地址" prop="ip_address">
          <el-input v-model="serverForm.ip_address" placeholder="请输入IP地址" />
        </el-form-item>
        <el-form-item label="SSH端口" prop="ssh_port">
          <el-input-number v-model="serverForm.ssh_port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="SSH用户名" prop="ssh_username">
          <el-input v-model="serverForm.ssh_username" placeholder="请输入SSH用户名" />
        </el-form-item>
        <el-form-item label="SSH密码" prop="ssh_password">
          <el-input
            v-model="serverForm.ssh_password"
            type="password"
            :placeholder="isEdit ? '留空则保持原密码' : '请输入SSH密码'"
            show-password
          />
        </el-form-item>
        <el-form-item label="用途" prop="purpose">
          <el-input
            v-model="serverForm.purpose"
            type="textarea"
            :rows="3"
            placeholder="请输入服务器用途"
          />
        </el-form-item>
        <el-form-item label="负责人" prop="owner">
          <el-input v-model="serverForm.owner" placeholder="请输入负责人" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button
          type="primary"
          plain
          :loading="testingSSH"
          @click="handleTestSSH"
        >
          测试连接
        </el-button>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { getServers, pingServer, createServer, updateServer, deleteServer, testServerSSH } from '@/api/servers'

const router = useRouter()

// 数据
const loading = ref(false)
const servers = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const dialogTitle = ref('添加服务器')
const isEdit = ref(false)
const submitting = ref(false)
const testingSSH = ref(false)
const serverFormRef = ref(null)

const queryParams = reactive({
  search: '',
  status: '',
  page: 1,
  page_size: 20
})

const serverForm = reactive({
  id: null,
  hostname: '',
  ip_address: '',
  ssh_port: 22,
  ssh_username: '',
  ssh_password: '',
  purpose: '',
  owner: ''
})

// 表单验证规则
const rules = {
  hostname: [
    { required: true, message: '请输入主机名', trigger: 'blur' }
  ],
  ip_address: [
    { required: true, message: '请输入IP地址', trigger: 'blur' },
    {
      pattern: /^(\d{1,3}\.){3}\d{1,3}$/,
      message: 'IP地址格式不正确',
      trigger: 'blur'
    }
  ],
  ssh_port: [
    { required: true, message: '请输入SSH端口', trigger: 'blur' }
  ],
  ssh_username: [
    { required: true, message: '请输入SSH用户名', trigger: 'blur' }
  ],
  ssh_password: [
    {
      validator: (_rule, value, callback) => {
        if (!isEdit.value && !value) {
          callback(new Error('请输入SSH密码'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 方法
const fetchServers = async () => {
  loading.value = true
  try {
    const params = {
      page: queryParams.page,
      page_size: queryParams.page_size
    }
    if (queryParams.search) {
      params.search = queryParams.search
    }
    if (queryParams.status) {
      params.status = queryParams.status
    }

    const response = await getServers(params)
    servers.value = response.data.items
    total.value = response.data.total
    
    // 异步检测每个服务器的在线状态
    checkServersStatus()
  } catch (error) {
    ElMessage.error('获取服务器列表失败')
  } finally {
    loading.value = false
  }
}

const checkServersStatus = async () => {
  // 为每个服务器异步检测状态
  for (const server of servers.value) {
    try {
      const response = await pingServer(server.id)
      server.online_status = response.data.status
    } catch (error) {
      server.online_status = 'offline'
    }
  }
}

const resetQuery = () => {
  queryParams.search = ''
  queryParams.status = ''
  queryParams.page = 1
  fetchServers()
}

const showAddDialog = () => {
  dialogTitle.value = '添加服务器'
  isEdit.value = false
  dialogVisible.value = true
}

const showEditDialog = (row) => {
  dialogTitle.value = '编辑服务器'
  isEdit.value = true
  Object.assign(serverForm, row)
  dialogVisible.value = true
}

const resetForm = () => {
  serverForm.id = null
  serverForm.hostname = ''
  serverForm.ip_address = ''
  serverForm.ssh_port = 22
  serverForm.ssh_username = ''
  serverForm.ssh_password = ''
  serverForm.purpose = ''
  serverForm.owner = ''
  serverFormRef.value?.clearValidate()
}

const handleTestSSH = async () => {
  if (!serverFormRef.value) return

  const fields = ['ip_address', 'ssh_port', 'ssh_username']
  if (!isEdit.value || serverForm.ssh_password) {
    fields.push('ssh_password')
  }

  try {
    await serverFormRef.value.validateField(fields)
  } catch {
    return
  }

  testingSSH.value = true
  try {
    const payload = {
      ip_address: serverForm.ip_address,
      ssh_port: serverForm.ssh_port,
      ssh_username: serverForm.ssh_username,
    }
    if (serverForm.ssh_password) {
      payload.ssh_password = serverForm.ssh_password
    } else if (isEdit.value && serverForm.id) {
      payload.server_id = serverForm.id
    }

    const response = await testServerSSH(payload)
    if (response.data.success) {
      const duration = response.data.duration_seconds
      ElMessage.success(
        duration != null ? `SSH 连接成功（${duration}s）` : 'SSH 连接成功'
      )
    } else {
      ElMessage.error(response.data.message || 'SSH 连接失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || 'SSH 连接测试失败')
  } finally {
    testingSSH.value = false
  }
}

const handleSubmit = async () => {
  if (!serverFormRef.value) return

  await serverFormRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      if (isEdit.value) {
        await updateServer(serverForm.id, serverForm)
        ElMessage.success('更新成功')
      } else {
        await createServer(serverForm)
        ElMessage.success('添加成功')
      }
      dialogVisible.value = false
      fetchServers()
    } catch (error) {
      ElMessage.error(isEdit.value ? '更新失败' : '添加失败')
    } finally {
      submitting.value = false
    }
  })
}

const handleDelete = (row) => {
  ElMessageBox.confirm(
    `确定要删除服务器 "${row.hostname}" 吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deleteServer(row.id)
      ElMessage.success('删除成功')
      fetchServers()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

const goToMonitoring = (row) => {
  router.push(`/servers/${row.id}/monitoring`)
}

// 生命周期
onMounted(() => {
  fetchServers()
})
</script>

<style scoped>
.servers-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.servers-container :deep(.el-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.servers-container :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.servers-container :deep(.el-table) {
  flex: 1;
}

.servers-container :deep(.el-table__wrapper) {
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

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
  flex-shrink: 0;
}
</style>
