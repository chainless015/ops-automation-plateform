<template>
  <div class="alert-silences">
    <el-card>
      <template #header>
        <div class="header">
          <span>告警屏蔽</span>
          <el-button type="primary" size="small" @click="fetchSilences">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <el-table :data="silences" v-loading="loading" style="width: 100%">
        <el-table-column label="规则名称" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.rule_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="服务器" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.server_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="屏蔽原因" min-width="150" show-overflow-tooltip />
        <el-table-column label="屏蔽时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.silenced_at) }}
          </template>
        </el-table-column>
        <el-table-column label="到期时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.expires_at) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_active && !isExpired(row.expires_at)" type="success">生效中</el-tag>
            <el-tag v-else type="info">已失效</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.is_active && !isExpired(row.expires_at)"
              type="danger"
              size="small"
              @click="handleRemove(row)"
            >
              取消屏蔽
            </el-button>
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
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAlertSilences, deleteAlertSilence } from '@/api/alerts'

const loading = ref(false)
const silences = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const fetchSilences = async () => {
  loading.value = true
  try {
    const response = await getAlertSilences({
      page: currentPage.value,
      page_size: pageSize.value
    })
    silences.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    ElMessage.error('获取屏蔽列表失败')
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

const isExpired = (expiresAt) => {
  if (!expiresAt) return false
  return new Date(expiresAt) <= new Date()
}

const handleRemove = async (row) => {
  try {
    await ElMessageBox.confirm('确定要取消此屏蔽吗？', '确认取消', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await deleteAlertSilence(row.id)
    ElMessage.success('已取消屏蔽')
    fetchSilences()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('取消失败')
    }
  }
}

onMounted(() => {
  fetchSilences()
})

watch([currentPage, pageSize], () => {
  fetchSilences()
})
</script>

<style scoped>
.alert-silences {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.alert-silences :deep(.el-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.alert-silences :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.alert-silences :deep(.el-table) {
  flex: 1;
}

.alert-silences :deep(.el-table__wrapper) {
  flex: 1;
  overflow: auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
