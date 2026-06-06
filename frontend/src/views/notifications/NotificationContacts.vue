<template>
  <div class="alert-contacts">
    <el-card>
      <template #header>
        <div class="header">
          <span>通知对象</span>
          <div style="display: flex; align-items: center; gap: 8px">
            <el-button type="primary" size="small" @click="fetchContacts" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button type="primary" size="small" @click="handleAdd">
              <el-icon><Plus /></el-icon>
              添加通知对象
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="contacts" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="姓名" min-width="120" show-overflow-tooltip />
        <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
        <el-table-column prop="phone" label="电话" min-width="120" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.enabled" type="success">启用</el-tag>
            <el-tag v-else type="info">禁用</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
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
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="电话" prop="phone">
          <el-input v-model="form.phone" placeholder="请输入电话（可选）" />
        </el-form-item>
        <el-form-item label="状态">
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
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAlertContacts, createAlertContact, updateAlertContact, deleteAlertContact } from '@/api/alerts'

const loading = ref(false)
const submitting = ref(false)
const contacts = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('')
const formRef = ref(null)
const isEdit = ref(false)
const editId = ref(null)

const form = reactive({
  name: '',
  email: '',
  phone: '',
  enabled: true
})

const rules = {
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ]
}

const fetchContacts = async () => {
  loading.value = true
  try {
    const response = await getAlertContacts()
    contacts.value = response.data
  } catch (error) {
    ElMessage.error('获取告警人列表失败')
  } finally {
    loading.value = false
  }
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

const handleAdd = () => {
  isEdit.value = false
  dialogTitle.value = '添加通知对象'
  resetForm()
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  editId.value = row.id
  dialogTitle.value = '编辑通知对象'
  Object.assign(form, {
    name: row.name,
    email: row.email,
    phone: row.phone || '',
    enabled: row.enabled
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
        await updateAlertContact(editId.value, form)
        ElMessage.success('更新成功')
      } else {
        await createAlertContact(form)
        ElMessage.success('添加成功')
      }
      dialogVisible.value = false
      fetchContacts()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    } finally {
      submitting.value = false
    }
  })
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除告警人"${row.name}"吗？`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await deleteAlertContact(row.id)
    ElMessage.success('删除成功')
    fetchContacts()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const resetForm = () => {
  Object.assign(form, {
    name: '',
    email: '',
    phone: '',
    enabled: true
  })
  formRef.value?.clearValidate()
}

onMounted(() => {
  fetchContacts()
})
</script>

<style scoped>
.alert-contacts {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.alert-contacts :deep(.el-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.alert-contacts :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.alert-contacts :deep(.el-table) {
  flex: 1;
}

.alert-contacts :deep(.el-table__wrapper) {
  flex: 1;
  overflow: auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
