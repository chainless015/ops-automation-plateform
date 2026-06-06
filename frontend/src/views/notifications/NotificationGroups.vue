<template>
  <div class="alert-groups">
    <el-card>
      <template #header>
        <div class="header">
          <span>通知组</span>
          <div style="display: flex; align-items: center; gap: 8px">
            <el-button type="primary" size="small" @click="fetchGroups" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button type="primary" size="small" @click="handleAdd">
              <el-icon><Plus /></el-icon>
              添加通知组
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="groups" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="组名" min-width="120" show-overflow-tooltip />
        <el-table-column prop="description" label="描述" min-width="150" show-overflow-tooltip />
        <el-table-column label="成员" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <el-tag
              v-for="contact in row.contacts"
              :key="contact.id"
              size="small"
              style="margin-right: 5px"
            >
              {{ contact.name }}
            </el-tag>
            <span v-if="!row.contacts || row.contacts.length === 0">-</span>
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
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="组名" prop="name">
          <el-input v-model="form.name" placeholder="请输入组名" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入描述（可选）"
          />
        </el-form-item>
        <el-form-item label="成员" prop="contact_ids">
          <el-select
            v-model="form.contact_ids"
            multiple
            placeholder="请选择成员"
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
import { getAlertGroups, createAlertGroup, updateAlertGroup, deleteAlertGroup, getAlertContacts } from '@/api/alerts'

const loading = ref(false)
const submitting = ref(false)
const groups = ref([])
const contacts = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('')
const formRef = ref(null)
const isEdit = ref(false)
const editId = ref(null)

const form = reactive({
  name: '',
  description: '',
  contact_ids: []
})

const rules = {
  name: [
    { required: true, message: '请输入组名', trigger: 'blur' }
  ]
}

const fetchGroups = async () => {
  loading.value = true
  try {
    const response = await getAlertGroups()
    groups.value = response.data
  } catch (error) {
    ElMessage.error('获取告警组列表失败')
  } finally {
    loading.value = false
  }
}

const fetchContacts = async () => {
  try {
    const response = await getAlertContacts()
    contacts.value = response.data
  } catch (error) {
    console.error('获取告警人列表失败', error)
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
  dialogTitle.value = '添加通知组'
  resetForm()
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  editId.value = row.id
  dialogTitle.value = '编辑通知组'
  Object.assign(form, {
    name: row.name,
    description: row.description || '',
    contact_ids: row.contacts ? row.contacts.map(c => c.id) : []
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
        await updateAlertGroup(editId.value, form)
        ElMessage.success('更新成功')
      } else {
        await createAlertGroup(form)
        ElMessage.success('添加成功')
      }
      dialogVisible.value = false
      fetchGroups()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    } finally {
      submitting.value = false
    }
  })
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除告警组"${row.name}"吗？`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await deleteAlertGroup(row.id)
    ElMessage.success('删除成功')
    fetchGroups()
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
    contact_ids: []
  })
  formRef.value?.clearValidate()
}

onMounted(() => {
  fetchContacts()
  fetchGroups()
})
</script>

<style scoped>
.alert-groups {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.alert-groups :deep(.el-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.alert-groups :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.alert-groups :deep(.el-table) {
  flex: 1;
}

.alert-groups :deep(.el-table__wrapper) {
  flex: 1;
  overflow: auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
